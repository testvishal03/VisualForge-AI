"""Topic -> local model -> validated content JSON, ready for generate_audio.py."""
import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.llm.prompts import normalize_topic, scene_count
from backend.services.script_generator import generate_video_script


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic")
    parser.add_argument("--minutes", type=float, default=2.0, help="Target duration guidance, 0.5–4 minutes")
    parser.add_argument('--audience',default='beginners')
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/video.json")
    parser.add_argument("--offline", action="store_true", help="Require the cached model; make no model download")
    parser.add_argument("--checkpoint-dir", type=Path, help="Reuse validated field drafts when resuming")
    parser.add_argument("--threads", type=int, default=2, choices=range(1, 9))
    parser.add_argument("--max-new-tokens", type=int, default=1800)
    parser.add_argument("--temperature", type=float, default=0.0, help="Zero means greedy decoding")
    parser.add_argument("--attempts", type=int, default=3, choices=[1, 2, 3])
    args = parser.parse_args(argv)
    try:
        topic = normalize_topic(args.topic)
        count = scene_count(args.minutes)
        if not 128 <= args.max_new_tokens <= 3000 or not 0 <= args.temperature <= 1:
            raise ValueError("Use 128–3000 new tokens and temperature between 0 and 1.")
        print(f"Planning around {count} scenes with the configured local CPU model.", flush=True)
        result = generate_video_script(
            topic, args.output, args.minutes, offline=args.offline, threads=args.threads,
            max_new_tokens=args.max_new_tokens, temperature=args.temperature, attempts=args.attempts,
            report_path=args.output.with_suffix(".generation-report.json"),
            diagnostics_dir=PROJECT_ROOT / "backend/.cache/last-generation",
            checkpoint_dir=args.checkpoint_dir,
            audience=args.audience,
            on_progress=lambda message: print(message, flush=True),
        )
        print(f"Video script generated successfully.\nTopic: {result.topic}\nTitle: {result.title}\nScenes: {len(result.scenes)}\nOutput: {args.output}")
        return 0
    except Exception as exc:
        print(f"Script generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
