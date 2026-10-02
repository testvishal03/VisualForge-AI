"""Isolated chapter inference and frame-aligned MP4 assembly."""
import json
import math
from pathlib import Path
import sys
import wave
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.llm.gguf_llm import create_local_llm
from backend.llm.prompts import factual_guidance
from backend.schemas.video_schema import Scene, VideoScript, VideoPlan, words
from backend.services.json_parser import parse_json_object
from backend.services.script_generator import write_json_atomic
from backend.services.run_state import fingerprint


def ask(engine, prompt, schema, validate, cache):
    key = fingerprint([prompt, schema, getattr(engine, 'cache_identity', 'legacy'), 'long-v1'])
    path = cache / f'{key}.json'
    if path.is_file():
        try:
            return validate(json.loads(path.read_text(encoding='utf-8')))
        except ValueError:
            pass
    original = prompt
    for attempt in range(3):
        print(f'Local model: attempt {attempt + 1}/3', flush=True)
        raw = engine.generate_json(prompt, max_new_tokens=1800, schema=schema) if hasattr(engine, 'generate_json') else engine.generate(prompt)
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f'{key}-attempt-{attempt + 1}.txt').write_text(raw, encoding='utf-8')
        try:
            data = parse_json_object(raw)
            result = validate(data)
            write_json_atomic(path, data)
            return result
        except ValueError as exc:
            if attempt == 2:
                raise
            prompt = original + '\nCorrect this validation error: ' + str(exc)[:700]


def outline(topic, minutes, output):
    count = math.ceil(minutes / 2)
    base, extra = divmod(minutes * 60, count)
    guidance = factual_guidance(topic)
    engine = create_local_llm(offline=True, threads=2, on_progress=lambda s: print(s, flush=True))
    chapters = []
    try:
        for index in range(count):
            schema = {'type': 'object', 'properties': {k: {'type': 'string', 'minLength': 5, 'maxLength': limit} for k, limit in [('title', 100), ('focus', 300), ('visual_goal', 160)]}, 'required': ['title', 'focus', 'visual_goal'], 'additionalProperties': False}
            prompt = f'''Plan chapter {index + 1} of {count} in a {minutes}-minute educational video about {topic}.
Earlier chapters: {json.dumps(chapters)}
Create a distinct next teaching objective in a logical progression. {'Begin with the essential context.' if index == 0 else 'Finish with a practical application and takeaway.' if index == count-1 else 'Develop a specific mechanism or application not already covered.'}
Domain guidance: {guidance}
Return title (under 10 words), focus (specific concepts to explain), visual_goal (one complete instruction of 8–15 words, under 130 characters). Available visuals are labeled process arrows, comparisons, connected relationships, cycles, system parts, neural network diagrams, code algorithm blocks, stat counter cards, icons, and example cards. Request these simple educational diagrams, not realistic footage or arbitrary animated characters. Do not invent dates or numerical statistics. Avoid generic chapter names and repetition.'''
            def validate(data):
                if set(data) != {'title', 'focus', 'visual_goal'} or any(not isinstance(data[k], str) or not 5 <= len(data[k]) <= limit or any(ord(c) < 32 for c in data[k]) for k, limit in [('title',100),('focus',300),('visual_goal',160)]):
                    raise ValueError('Use the three required plain single-line fields within their limits.')
                if any(data['title'].casefold() == c['title'].casefold() for c in chapters):
                    raise ValueError('This chapter repeats an earlier title.')
                return data
            chapter = ask(engine, prompt, schema, validate, output.parent / 'outline-cache')
            chapters.append({**chapter, 'seconds': base + (index < extra)})
            print(f'Chapter {index + 1}: {chapter["title"]}', flush=True)
        write_json_atomic(output, {'chapters': chapters})
    finally:
        if hasattr(engine, 'close'):
            engine.close()


def script(request_path, output, adjust=False):
    started = time.monotonic()
    request = json.loads(request_path.read_text(encoding='utf-8'))
    chapter = request['chapter']
    guidance = factual_guidance(request['topic'])
    engine = create_local_llm(offline=True, threads=2, on_progress=lambda s: print(s, flush=True))
    cache = output.parent / 'generation-cache'
    count = len(request['previous']['scenes']) if adjust else min(12, max(3, math.ceil(chapter['seconds'] / 15)))
    target_words = round((chapter['seconds'] - count * .5) * 170 / 60)
    scenes = []
    try:
        if not adjust:
            schema = VideoPlan.model_json_schema()
            schema['properties']['topic']['const'] = chapter['title']
            schema['properties']['scenes'].update(minItems=count, maxItems=count)
            plan_prompt = f'''Outline exactly {count} distinct scenes for ONE chapter called {chapter['title']}.
Overall video: {request['topic']}. Chapter scope: {chapter['focus']}.
Other chapter titles (do not teach those chapters here): {json.dumps(request['titles'])}.
Domain guidance: {guidance}
Previous playlist topic (use a short connection, avoid reteaching): {request.get('playlist_context', '')}
User's original script for expansion (preserve its intent and explain useful additional details): {request.get('reference_script', '')}
Break the chapter into specific subtopics, mechanisms, observations, contrasts, and one practical example. Each scene must teach a DIFFERENT detail. Do not summarize the entire chapter in scene one, and do not repeat the same process with different wording. Use concrete short headlines and one precise teaching point per scene.
Return title, topic (exactly {json.dumps(chapter['title'])}), scenes with sequential id, headline, point. Exactly {count} scenes.'''
            def validate_plan(data):
                plan = VideoPlan.model_validate(data)
                if len(plan.scenes) != count or plan.topic != chapter['title']:
                    raise ValueError(f'Use exactly {count} scenes and preserve the chapter topic.')
                return plan
            plan = ask(engine, plan_prompt, schema, validate_plan, cache)
        for index in range(count):
            old = request['previous']['scenes'][index] if adjust else None
            desired = round(len(words(old['narration'])) * chapter['seconds'] / request['measured_seconds']) if old else round(target_words / count)
            low, high = max(15, min(50, round(desired * .9))), max(20, min(60, round(desired * 1.1)))
            schema = Scene.model_json_schema()
            schema['properties']['id']['const'] = index + 1
            prompt = f'''Write scene {index + 1} of {count} for this ONE chapter of a longer educational video.
Overall topic: {request['topic']}. Audience: {request['audience']}.
Chapter: {chapter['title']}. Scope: {chapter['focus']}. Desired visuals: {chapter['visual_goal']}.
Domain guidance: {guidance}
Previous playlist topic (use a short connection, avoid reteaching): {request.get('playlist_context', '')}
User's original script for expansion (preserve its intent and explain useful additional details): {request.get('reference_script', '')}
Other chapter titles: {json.dumps(request['titles'])}.
Previously explained headings: {json.dumps([s.headline for s in scenes])}.
Previous explanation: {json.dumps(scenes[-1].narration if scenes else '')}.
Teaching sequence: {json.dumps([s.model_dump() for s in plan.scenes]) if not adjust else 'Preserve the existing teaching sequence.'}.
Answer a specific viewer question, explain the mechanism, and carry a concrete example forward where relevant.
{('This scene teaches ONLY: ' + plan.scenes[index].point + '. Heading: ' + plan.scenes[index].headline) if not adjust else ''}
{'Revise this narration for measured duration, preserving its meaning: '+old['narration'] if old else 'Add a distinct useful detail within this chapter, avoiding repeated definitions and repeated introductions.'}
Write {low}–{high} spoken words in narration, two to four complete sentences. Name the input or situation, explain what changes and why, and give the observable result. Define unfamiliar terms. Continue the preceding example when useful; do not repeat its setup. Keep analogies separate from the actual mechanism. No filler or invented claims. When appropriate, explain actual ordered steps with First, Next, Finally; comparisons with Whereas or In contrast; causal relationships explicitly. Do not force diagrams onto unrelated facts.
Return id={index + 1}, headline (under 8 words), body (8–12 word on-screen caption, not identical to narration), narration. Use single-paragraph plain text. No scene/video introductions.'''
            def validate(data):
                scene = Scene.model_validate(data)
                # Word targets guide drafting; measured speech determines duration.
                # Scene already enforces the safe 15–60 word range. Rejecting an
                # otherwise valid paragraph for a few words causes futile retries.
                if scene.id != index + 1:
                    raise ValueError(f'Use scene id {index + 1}.')
                if any(scene.narration == prior.narration or scene.headline.casefold() == prior.headline.casefold() for prior in scenes):
                    raise ValueError('Add a distinct scene, not a repeated explanation.')
                from backend.services.quality import scene_issues
                errors = [i['message'] for i in scene_issues(scene, scenes, topic=request['topic']) if i['severity'] == 'error']
                if errors:
                    raise ValueError(' '.join(errors))
                return scene
            scenes.append(ask(engine, prompt, schema, validate, cache))
            print(f'Scene {index + 1}/{count}: {len(words(scenes[-1].narration))} words', flush=True)
        video = VideoScript(title=chapter['title'], topic=chapter['title'], scenes=scenes)
        write_json_atomic(output, video.model_dump())
        from backend.services.semantic_director import plan_video
        write_json_atomic(output.with_suffix('.visuals.json'), plan_video(video, engine=engine, cache=output.parent/'visual-plan-cache'))
        write_json_atomic(output.with_suffix('.generation-report.json'), {
            **getattr(engine, 'metadata', {}), 'seconds': round(time.monotonic() - started, 3),
            'scenes': len(scenes), 'words': sum(len(words(s.narration)) for s in scenes),
            'mode': 'adjust' if adjust else 'script', 'target_seconds': chapter['seconds']})
    finally:
        if hasattr(engine, 'close'):
            engine.close()


def join(manifest_path):
    from backend.scripts.validate_render import validate
    from backend.services.media_tools import ffmpeg
    request = json.loads(manifest_path.read_text(encoding='utf-8'))
    output = Path(request['output'])
    folder = output.parent
    profile = request['profile']
    stem, props_name = ('draft', 'draft-props.json') if profile == 'draft' else ('video', 'render-props.json')
    chapters = [Path(p) for p in request['chapters']]
    scenes, entries = [], []
    opening=closing=False
    for index,chapter in enumerate(chapters):
        props = json.loads((chapter / props_name).read_text(encoding='utf-8'))['videoData']
        flags=props.get('style',{})
        intro=bool(flags.get('showIntro'));outro=bool(flags.get('showOutro'))
        if intro and index!=0 or outro and index!=len(chapters)-1:
            raise ValueError('Bookends belong only at the start and end of a complete video')
        opening=opening or intro;closing=closing or outro
        duration = sum(math.ceil((s['duration'] + .5) * 30) for s in props['scenes']) / 30+(3 if intro else 0)+(5 if outro else 0)
        # Paths are internal UUID directories. Quote apostrophes for concat syntax.
        path = (chapter / f'{stem}.mp4').resolve().as_posix().replace("'", "'\\''")
        entries.extend([f"file '{path}'", f'duration {duration:.9f}'])
        for scene in props['scenes']:
            scenes.append({**scene, 'id': len(scenes) + 1})
    combined = folder / f'{stem}-combined-props.json'
    write_json_atomic(combined, {'videoData': {'title': 'Full video', 'style':{'theme':'ocean','brand':'','showIntro':opening,'showOutro':closing}, 'scenes': scenes}})
    listing = folder / 'chapters.concat.txt'
    listing.write_text('\n'.join(entries) + '\n', encoding='utf-8')
    # Build narration once on a frame-aligned sample timeline to avoid accumulating
    # encoder delay or container padding at every chapter boundary.
    wav = folder / 'combined-narration.wav'
    with wave.open(str(wav), 'wb') as writer:
        writer.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        if opening:writer.writeframes(b'\0\0'*(3*24000))
        for scene in scenes:
            with wave.open(str(ROOT / 'renderer/public' / scene['audio']), 'rb') as source:
                if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 24000):
                    raise ValueError('Expected 24 kHz mono narration.')
                samples = source.getnframes()
                writer.writeframes(source.readframes(samples))
            scheduled = math.ceil((scene['duration'] + .5) * 30) * 800
            writer.writeframes(b'\0\0' * (scheduled - samples))
        if closing:writer.writeframes(b'\0\0'*(5*24000))
    subprocess.run([str(ffmpeg()), '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(listing),
                    '-i', str(wav), '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'libmp3lame',
                    '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', str(output)], check=True)
    report = validate(output, combined, profile)
    write_json_atomic(folder / f'{stem}-validation.json', report)
    print(f'Validated full video: {report["videoDuration"]:.2f}s', flush=True)


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'outline':
        outline(sys.argv[2], int(sys.argv[3]), Path(sys.argv[4]))
    elif mode in {'script', 'adjust'}:
        script(Path(sys.argv[2]), Path(sys.argv[3]), mode == 'adjust')
    elif mode == 'join':
        join(Path(sys.argv[2]))
    else:
        raise ValueError('Unknown chapter worker action.')
