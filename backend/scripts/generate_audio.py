"""Generate a complete narration batch, then publish renderer metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from backend.tts.kokoro_tts import DEFAULT_VOICE, SEED, generate_speech
from backend.utils.audio_duration import audio_duration
from backend.utils.scene_data import load_source


def generate(source: Path, output: Path, public_dir: Path, voice: str = DEFAULT_VOICE, synthesizer=generate_speech) -> dict:
    data = load_source(source)
    # Content-addressed folders keep previous metadata valid while a new batch runs.
    fingerprint = hashlib.sha256(json.dumps(
        {"data": data, "voice": voice, "engine": "kokoro-onnx-0.6.1-v1.0", "speed": 1.0, "seed": SEED},
        sort_keys=True, ensure_ascii=False,
    ).encode()).hexdigest()[:16]
    audio_root = public_dir / "audio"
    audio_root.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not output.is_file():
        raise ValueError(f"Metadata output must be a file: {output}")
    enriched = []
    with tempfile.TemporaryDirectory(prefix=".staging-", dir=audio_root) as staging:
        staging_path = Path(staging)
        for scene in data["scenes"]:
            name = f"scene-{scene['id']}.wav"
            target = staging_path / name
            synthesizer(scene["narration"], target, voice)
            duration = audio_duration(target)
            enriched.append({
                "id": scene["id"], "headline": scene["headline"], "body": scene["body"],
                "narration": scene["narration"], "audio": f"audio/{fingerprint}/{name}", "duration": duration,
            })
            print(f"Scene {scene['id']}: {duration:.6f}s -> {name}", flush=True)
        destination = audio_root / fingerprint
        destination.mkdir(exist_ok=True)
        for audio in staging_path.iterdir():
            audio.replace(destination / audio.name)
    result = {"title": data["title"], "scenes": enriched, "tts": {"engine": "kokoro-onnx", "version": "0.6.1", "voice": voice, "seed": SEED}}
    if "topic" in data:
        result["topic"] = data["topic"]
    # Never publish half-generated JSON; old metadata survives a synthesis failure.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, suffix=".json", delete=False) as handle:
        temp_path = Path(handle.name)
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    try:
        temp_path.replace(output)
    finally:
        temp_path.unlink(missing_ok=True)
    print(f"Published {len(enriched)} scenes to {output}", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data/video.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/video.generated.json")
    parser.add_argument("--public-dir", type=Path, default=PROJECT_ROOT / "renderer/public")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--incremental", action="store_true", help="Regenerate only changed or missing narration")
    parser.add_argument("--directed", action="store_true", help="Synthesize measured sentence beats for visual synchronization")
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and generated output must be different files.")
    try:
        if args.incremental or args.directed:
            from backend.services.incremental_audio import generate_incremental
            generate_incremental(args.input, args.output, args.public_dir, args.voice, directed=args.directed)
        else:
            generate(args.input, args.output, args.public_dir, args.voice)
        return 0
    except Exception as exc:
        print(f"Audio generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
