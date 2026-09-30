import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.schemas.video_schema import VideoScript
from backend.services.script_generator import write_json_atomic
from backend.services.visuals import build_visuals

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a restrained visual plan using local content and a local model.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--threads", type=int, default=2, choices=range(1, 9))
    args = parser.parse_args()
    video = VideoScript.model_validate(json.loads(args.source.read_text(encoding="utf-8")))
    write_json_atomic(args.output, build_visuals(video, offline=args.offline, threads=args.threads))
