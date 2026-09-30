"""Regenerate one scene's caption/narration; never change its siblings."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.llm.gguf_llm import create_local_llm
from backend.llm.prompts import build_scene_prompt, build_retry_prompt
from backend.schemas.video_schema import VideoScript, BodyDraft, NarrationDraft, Scene
from backend.services.json_parser import parse_json_object
from backend.services.quality import scene_issues
from backend.services.script_generator import write_json_atomic


def regenerate(video, scene_id, instructions, engine=None):
    owns_engine = engine is None
    engine = engine or create_local_llm(offline=True, threads=2, on_progress=lambda s: print(s, flush=True))
    try:
        old = next(s for s in video.scenes if s.id == scene_id)
        result = old.model_dump()
        for field, validator in [('body', BodyDraft), ('narration', NarrationDraft)]:
            point = old.headline + '. ' + old.body + '\nFocus this revision on: ' + instructions
            original = build_scene_prompt(video.topic, {'point': point}, field, result['body'])
            original += '\nUse neutral language. Avoid the words always, ensure, ensures, ensuring, guarantee, guarantees, and guaranteeing. Describe checking as reducing errors, not proving accuracy.'
            prompt = original
            for attempt in range(1, 4):
                print(f'Scene {scene_id} {field}: attempt {attempt}/3', flush=True)
                raw = engine.generate(prompt, max_new_tokens=180 if field == 'body' else 300, temperature=.2)
                try:
                    value = getattr(validator.model_validate(parse_json_object(raw)), field)
                    candidate = {**result, field: value}
                    if field == 'narration':
                        scene = Scene.model_validate(candidate)
                        errors = [i['message'] for i in scene_issues(scene, [s for s in video.scenes if s.id != scene_id]) if i['severity'] == 'error']
                        if errors:
                            raise ValueError(' '.join(errors))
                    result = candidate
                    break
                except ValueError as exc:
                    print(f'Validation rejected {field}: {exc}', flush=True)
                    if attempt == 3:
                        raise ValueError(f'Could not regenerate {field}; original scene preserved. {exc}') from exc
                    prompt = build_retry_prompt(original, raw, str(exc), attempt+1)
        return Scene.model_validate(result)

    finally:
        if owns_engine and hasattr(engine, 'close'):
            engine.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--scene-id', type=int, required=True)
    parser.add_argument('--instructions', default='Make the explanation concrete, clear, and concise. Avoid hype.')
    args = parser.parse_args()
    video = VideoScript.model_validate_json(args.source.read_text(encoding='utf-8'))
    write_json_atomic(args.output, regenerate(video, args.scene_id, args.instructions).model_dump())
