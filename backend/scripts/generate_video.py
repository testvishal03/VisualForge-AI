"""One command: topic -> resumable local script, audio, visuals, render and checks."""
import argparse
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.llm.gguf_llm import model_status
from backend.llm.prompts import normalize_topic, scene_count
from backend.schemas.video_schema import VideoScript
from backend.services.process_runner import execute, node_executable, python_stage
from backend.services.quality import review_video
from backend.services.run_state import RunState, file_hash, fingerprint, run_lock
from backend.services.script_generator import write_json_atomic

STAGES = ['script', 'quality', 'audio', 'visuals', 'props', 'render', 'validate']


def code_hash(*names):
    paths = []
    for name in names:
        path = ROOT/name
        paths.extend(p for p in path.rglob('*') if p.is_file() and p.suffix in {'.py', '.ts', '.tsx', '.json'} and '__pycache__' not in p.parts) if path.is_dir() else paths.append(path)
    return fingerprint({str(p.relative_to(ROOT)): file_hash(p) for p in sorted(paths)})


def run(args):
    topic = normalize_topic(args.topic)
    scene_count(args.minutes)
    node = node_executable()
    if not (ROOT/'renderer/node_modules/@remotion/cli/remotion-cli.js').is_file():
        raise ValueError('Renderer dependencies are missing. Run npm.cmd install in renderer.')
    if not all((ROOT/'backend/models'/name).is_file() for name in ['kokoro-v1.0.onnx', 'voices-v1.0.bin']):
        raise ValueError('Kokoro weights are missing. Run backend/scripts/download_models.py before generating a video.')
    supplied = args.script.resolve() if args.script else None
    settings = {'topic': topic, 'minutes': args.minutes, 'threads': args.threads, 'model': model_status(),
                'script': str(supplied) if supplied else None}
    slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')[:50] or 'video'
    run_id = f'{slug}-{fingerprint(settings)[:10]}'
    folder = args.run_dir.resolve() if args.run_dir else ROOT/'data/runs'/run_id
    source, metadata = folder/'video.json', folder/'video.generated.json'
    quality, visuals, props = folder/'quality.json', folder/'visuals.json', folder/'props.json'
    report, output = folder/'media-validation.json', folder/'video.mp4'
    if supplied:
        imported = VideoScript.model_validate_json(supplied.read_text(encoding='utf-8'))
        if imported.topic != topic:
            raise ValueError('--script topic must match the supplied topic exactly')
    print(f'Video: {topic}\nRun folder: {folder}\nStages run sequentially; rerun the same command to resume.', flush=True)
    started = time.monotonic()
    with run_lock(folder):
        state = RunState(folder, force=args.force, progress=lambda s: print(s, flush=True))
        state.data.update(settings=settings, output=str(output))
        def stage(name, key, action, artifacts, attempts=1):
            state.stage(name, key, action, artifacts, attempts=attempts)
            if args.stop_after == name:
                state.data.update(status='paused', stopped_after=name)
                state.save()
                print(f'Stopped after {name}. Rerun without --stop-after to continue.', flush=True)
                raise StopIteration
        def py(name, script, argv):
            return python_stage(ROOT/'backend/scripts'/script, argv, root=ROOT, folder=folder, name=name, timeout=args.stage_timeout)
        flags = ['--offline'] if args.offline else []
        try:
            script_key = fingerprint([settings, file_hash(supplied) if supplied else None,
                                      code_hash('backend/llm', 'backend/schemas', 'backend/services/script_generator.py', 'backend/services/quality.py', 'backend/scripts/generate_script.py')])
            def script_action():
                if supplied:
                    write_json_atomic(source, imported.model_dump())
                    return {'origin': str(supplied), 'generation': 'imported; no inference'}
                argv = [topic, '--minutes', str(args.minutes), '--output', source, '--threads', str(args.threads), *flags]
                if not args.force:
                    argv += ['--checkpoint-dir', folder/'drafts']
                return py('script', 'generate_script.py', argv)
            stage('script', script_key, script_action, [source] if supplied else [source, source.with_suffix('.generation-report.json')])

            def quality_action():
                video = VideoScript.model_validate_json(source.read_text(encoding='utf-8'))
                result = review_video(video)
                write_json_atomic(quality, result)
                if any(i['severity'] == 'error' for i in result['issues']):
                    raise ValueError(f'Content needs correction before rendering. See {quality}')
                return {'review_status': result['status']}
            stage('quality', fingerprint([file_hash(source), code_hash('backend/services/quality.py', 'backend/schemas')]), quality_action, [quality])

            def audio_artifacts():
                data = json.loads(metadata.read_text(encoding='utf-8'))
                return [metadata, *[ROOT/'renderer/public'/s['audio'] for s in data['scenes']]]
            stage('audio', fingerprint([file_hash(source), code_hash('backend/scripts/generate_audio.py', 'backend/tts', 'backend/utils', 'backend/requirements.lock.txt')]),
                  lambda: py('audio', 'generate_audio.py', ['--input', source, '--output', metadata]), audio_artifacts)
            stage('visuals', fingerprint([file_hash(source), settings['model'], code_hash('backend/services/visuals.py', 'backend/llm', 'backend/scripts/generate_visuals.py')]),
                  lambda: py('visuals', 'generate_visuals.py', [source, visuals, '--threads', str(args.threads), *flags]), [visuals])

            def props_action():
                data = json.loads(metadata.read_text(encoding='utf-8'))
                plan = json.loads(visuals.read_text(encoding='utf-8'))
                by_id = {s['id']: {k:v for k,v in s.items() if k != 'id'} for s in plan['scenes']}
                if set(by_id) != {s['id'] for s in data['scenes']}:
                    raise ValueError('Visual scene IDs do not match narration metadata')
                for scene in data['scenes']:
                    scene['visual'] = by_id[scene['id']]
                write_json_atomic(props, {'videoData': data})
            stage('props', fingerprint([file_hash(metadata), file_hash(visuals), code_hash('backend/scripts/generate_video.py')]), props_action, [props])
            renderer_hash = code_hash('renderer/src', 'renderer/remotion.config.ts', 'renderer/package-lock.json')
            audio_hashes = [file_hash(p) for p in audio_artifacts()]
            def render_action():
                pending = folder/'video.pending.mp4'
                metrics = execute([node, ROOT/'renderer/node_modules/@remotion/cli/remotion-cli.js', 'render', 'VisualForgeVideo', pending,
                                   f'--props={props}', f'--concurrency={args.concurrency}'], cwd=ROOT/'renderer',
                                  log=folder/'logs/render.log', timeout=args.stage_timeout)
                pending.replace(output)
                return metrics
            stage('render', fingerprint([file_hash(props), audio_hashes, renderer_hash, args.concurrency]),
                  render_action, [output], attempts=2)
            stage('validate', fingerprint([file_hash(output), file_hash(props), audio_hashes, code_hash('backend/scripts/validate_render.py', 'renderer/scripts/timeline.ts', 'renderer/src/timeline.ts')]),
                  lambda: py('validate', 'validate_render.py', [output, '--metadata', props, '--report', report]), [report])
        except StopIteration:
            return 0
        checks = json.loads(quality.read_text(encoding='utf-8'))
        plan = json.loads(visuals.read_text(encoding='utf-8'))
        media = json.loads(report.read_text(encoding='utf-8'))
        review = checks['status'] == 'needs_review' or bool(plan['warnings'])
        state.data.update(status='complete_with_review' if review else 'complete', failed_stage=None,
                          last_run_seconds=round(time.monotonic()-started, 3), executed=state.executed, reused=state.reused)
        state.save()
        print(f"\nVideo complete: {output}\n{media['frames']} frames; {media['videoDuration']:.3f}s; 1080p / {media['fps']} FPS.\nExecuted: {', '.join(state.executed) or 'none'}\nReused: {', '.join(state.reused) or 'none'}", flush=True)
        print(f"Editorial review: {'NEEDS REVIEW' if review else 'automated checks passed; facts not verified'}. See {quality}", flush=True)
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('topic')
    parser.add_argument('--minutes', type=float, default=2)
    parser.add_argument('--threads', type=int, choices=range(1, 9), default=2)
    parser.add_argument('--concurrency', type=int, choices=[1, 2], default=2)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--script', type=Path, help='Use an existing validated script instead of local text generation')
    parser.add_argument('--run-dir', type=Path, help='Run folder; use the same folder to resume')
    parser.add_argument('--force', action='store_true', help='Regenerate all stages without reusing field drafts')
    parser.add_argument('--stop-after', choices=STAGES, help='Save and stop after a stage; rerun without this option to resume')
    parser.add_argument('--stage-timeout', type=int, default=3600)
    args = parser.parse_args(argv)
    try:
        if args.stage_timeout < 1:
            raise ValueError('--stage-timeout must be positive')
        return run(args)
    except KeyboardInterrupt:
        print('\nInterrupted. Completed stages are saved; rerun the same command to resume.', file=sys.stderr)
        return 130
    except Exception as exc:
        print(f'Video generation failed: {exc}\nCompleted stages are saved. Correct the issue and rerun to resume.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
