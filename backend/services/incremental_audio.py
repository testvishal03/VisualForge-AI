"""Speech cache keyed by narration and synthesis settings, never scene position."""
import json
from pathlib import Path
import tempfile
import wave

from backend.services.director import sentences

from backend.services.run_state import file_hash, fingerprint
from backend.services.script_generator import write_json_atomic
from backend.tts.kokoro_tts import DEFAULT_VOICE, SEED, generate_speech
from backend.utils.audio_duration import audio_duration
from backend.utils.scene_data import load_source


def speech_key(narration, voice=DEFAULT_VOICE, directed=False):
    settings = {'narration': narration, 'voice': voice, 'engine': 'kokoro-onnx-0.6.1-v1.0', 'speed': 1, 'seed': SEED}
    if directed:
        settings['timing'] = 'sentences-v1-pause120ms'
    return fingerprint(settings)


def cached_speech(public_dir: Path, narration: str, voice=DEFAULT_VOICE, directed=False):
    key = speech_key(narration, voice, directed)
    wav = public_dir/'audio'/key/'scene-1.wav'
    try:
        record = json.loads(wav.with_suffix('.json').read_text(encoding='utf-8'))
        if record['key'] == key and record['sha256'] == file_hash(wav) and record['duration'] == audio_duration(wav):
            if directed:
                validate_beats(record['beats'], narration, record['duration'])
            return wav, record['duration']
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def validate_beats(beats, narration, duration):
    if not isinstance(beats, list) or [b['text'] for b in beats] != sentences(narration):
        raise ValueError('Invalid sentence timing text')
    previous = 0
    for beat in beats:
        if not 0 <= previous <= beat['start'] < beat['end'] <= duration:
            raise ValueError('Invalid sentence timing range')
        previous = beat['end']
    if not beats or beats[0]['start'] != 0 or abs(beats[-1]['end']-duration) > 1/24000:
        raise ValueError('Incomplete sentence timing')


def sentence_speech(narration, pending, voice, synthesizer):
    parts = sentences(narration)
    beats, samples, params, cursor = [], [], None, 0
    for index, text in enumerate(parts):
        part = pending.parent/f'part-{index}.wav'
        synthesizer(text, part, voice)
        with wave.open(str(part), 'rb') as reader:
            fmt = (reader.getnchannels(), reader.getsampwidth(), reader.getframerate())
            if fmt != (1, 2, 24000):
                raise ValueError('Sentence narration requires 24 kHz mono PCM16 WAV')
            params = fmt
            frames = reader.getnframes()
            if frames <= 0:
                raise ValueError('Empty sentence audio')
            samples.append(reader.readframes(frames))
        beats.append({'text': text, 'start': cursor/24000, 'end': (cursor+frames)/24000})
        cursor += frames
        if index < len(parts)-1:
            samples.append(b'\0\0'*2880)
            cursor += 2880
    with wave.open(str(pending), 'wb') as writer:
        writer.setparams((*params, 0, 'NONE', 'not compressed'))
        writer.writeframes(b''.join(samples))
    return beats


def generate_incremental(source: Path, output: Path, public_dir: Path, voice=DEFAULT_VOICE, synthesizer=generate_speech, directed=False):
    data = load_source(source)
    enriched, generated, reused = [], [], []
    for scene in data['scenes']:
        cached = cached_speech(public_dir, scene['narration'], voice, directed)
        if cached:
            wav, duration = cached
            reused.append(scene['id'])
        else:
            key = speech_key(scene['narration'], voice, directed)
            directory = public_dir/'audio'/key
            directory.mkdir(parents=True, exist_ok=True)
            wav = directory/'scene-1.wav'
            with tempfile.TemporaryDirectory(dir=directory, prefix='.pending-') as temporary:
                pending = Path(temporary)/'speech.wav'
                beats = sentence_speech(scene['narration'], pending, voice, synthesizer) if directed else None
                if not directed:
                    synthesizer(scene['narration'], pending, voice)
                duration = audio_duration(pending)
                pending.replace(wav)
            write_json_atomic(wav.with_suffix('.json'), {'key': key, 'sha256': file_hash(wav), 'duration': duration, **({'beats': beats} if directed else {})})
            generated.append(scene['id'])
        timing = {'beats': json.loads(wav.with_suffix('.json').read_text(encoding='utf-8'))['beats']} if directed else {}
        enriched.append({**scene, 'audio': wav.relative_to(public_dir).as_posix(), 'duration': duration, **timing})
        print(f"Scene {scene['id']}: {'reused' if cached else 'generated'} {duration:.3f}s", flush=True)
    result = {**data, 'scenes': enriched, 'tts': {'engine': 'kokoro-onnx', 'version': '0.6.1', 'voice': voice, 'seed': SEED},
              'cache': {'generated_scene_ids': generated, 'reused_scene_ids': reused}}
    write_json_atomic(output, result)
    return result
