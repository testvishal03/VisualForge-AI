"""A quick preview of one hand-designed scene, straight from the script box.

No narration is generated: sentence and word times are estimated from the words (about 140 per
minute, as the voice speaks), the scene gets a silent track, and Remotion renders a small, muted
clip of just that scene. Previews are cached by their content, so an unchanged scene is instant.
"""
import json
from pathlib import Path
import wave

from backend.services.run_state import fingerprint
from backend.services.script_generator import write_json_atomic

WORDS_PER_SECOND = 140 / 60
PAUSE = .28
RATE = 24000
SCALE = .4   # 768x432: enough to judge layout and motion, several times faster than a draft


def estimated_beats(narration):
    from backend.services.director import sentences
    from backend.utils.word_timing import estimate_words, offset_words
    beats, cursor = [], 0.0
    for part in sentences(narration):
        length = round(max(.8, len(part.split()) / WORDS_PER_SECOND), 3)
        start, end = round(cursor, 3), round(cursor + length, 3)
        # Same clamping as measured narration, so every word stays inside its sentence.
        words = offset_words(estimate_words(part, 0, length), start, end)
        beats.append({'text': part, 'start': start, 'end': end, 'words': words, 'wordTiming': 'estimated'})
        cursor = end + PAUSE
    return beats


def scene_from_script(text, number):
    """(narration, canvas spec) of scene `number` (1-based) in a pasted script, or ValueError."""
    from backend.services import seo
    from backend.services.canvas import extract
    text, _, _ = seo.extract(text)
    narration, specs, problems = extract(text)
    paragraphs = narration.split('\n\n')
    if problems:
        bad = [message for scene, message in problems if scene == number]
        if bad:
            raise ValueError(f'Scene {number} visual: {bad[0]}')
    if not 1 <= number <= len(paragraphs) or not specs or specs[number - 1] is None:
        raise ValueError(f'Scene {number} has no visual block to preview.')
    return paragraphs[number - 1], specs[number - 1]


def preview(jobs, text, number, title='Preview'):
    """Path of an MP4 preview of scene `number`; renders only when this exact scene is new."""
    from backend.services.canvas import timed, validate
    from backend.services.director import sentences
    from backend.services.render_assets import RENDER_CONCURRENCY
    narration, spec = scene_from_script(text, number)
    clean = validate(spec, sentences(narration))
    key = fingerprint(['scene-preview-v1', jobs.version, narration, clean, title, number])[:16]
    folder = jobs.root / 'backend/.cache/scene-preview'
    output = folder / f'{key}.mp4'
    if output.is_file():
        return output
    beats = estimated_beats(narration)
    duration = beats[-1]['end']
    audio = f'audio/preview/{key}/scene-1.wav'
    wav = jobs.root / 'renderer/public' / audio
    wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav), 'wb') as writer:
        writer.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        writer.writeframes(b'\0\0' * round(duration * RATE))
    scene = {'id': 1, 'headline': title[:60] or 'Preview', 'body': narration[:120], 'narration': narration, 'audio': audio,
             'duration': duration, 'beats': beats, 'visual': {'kind': 'explanation', 'items': []}, 'canvas': timed(clean, beats)}
    props = folder / f'{key}-props.json'
    write_json_atomic(props, {'videoData': {'title': title, 'topic': title, 'scenes': [scene],
                                            'style': {'theme': 'ocean', 'brand': 'PREVIEW', 'showIntro': False, 'showOutro': False, 'topicMap': False}}})
    pending = folder / f'{key}.pending.mp4'
    jobs.remotion(folder, ['render', 'VisualForgeVideo', pending, f'--props={props}', f'--scale={SCALE}', '--muted',
                           f'--concurrency={RENDER_CONCURRENCY}'], 'scene-preview')
    pending.replace(output)
    return output
