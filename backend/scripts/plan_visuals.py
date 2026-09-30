"""Isolated, cached local visual planning without rewriting narration."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.schemas.video_schema import VideoScript
from backend.llm.gguf_llm import create_local_llm
from backend.services.semantic_director import plan_video
from backend.services.script_generator import write_json_atomic

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--scene-id', type=int)
    parser.add_argument('--instructions', default='')
    args = parser.parse_args()
    video = VideoScript.model_validate_json(args.source.read_text(encoding='utf-8'))
    if args.scene_id is not None:
        if not 1 <= args.scene_id <= len(video.scenes):
            raise ValueError('Unknown scene')
        video = video.model_copy(update={'scenes': [video.scenes[args.scene_id-1]]})
    engine = create_local_llm(offline=True, threads=2, on_progress=lambda s: print(s, flush=True))
    try:
        write_json_atomic(args.output, plan_video(video, engine=engine, cache=args.output.parent/'visual-plan-cache', instructions=args.instructions))
    finally:
        if hasattr(engine, 'close'):
            engine.close()
