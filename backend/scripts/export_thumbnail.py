import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.services.editor_store import EditorStore

def main():
    parser = argparse.ArgumentParser(description="Export a thumbnail JPEG for a project.")
    parser.add_argument("project_id", help="The ID of the project to generate a thumbnail for")
    args = parser.parse_args()

    store_dir = ROOT / 'data' / 'editor'
    store = EditorStore(store_dir)

    try:
        store.load(args.project_id)
    except Exception as e:
        print(f"Error loading project '{args.project_id}': {e}", file=sys.stderr)
        sys.exit(1)

    project_folder = store.folder(args.project_id)
    video_path = project_folder / 'video.mp4'

    if not video_path.exists():
        print(f"Error: video.mp4 not found in project folder ({video_path}).\nRender the video first to generate the thumbnail.", file=sys.stderr)
        sys.exit(1)

    thumbnail_path = project_folder / 'thumbnail.jpg'

    ffmpeg_paths_to_try = [
        __import__('backend.services.media_tools', fromlist=['ffmpeg']).ffmpeg(),
        'ffmpeg'
    ]

    success = False
    last_error = None
    
    for ffmpeg_path in ffmpeg_paths_to_try:
        try:
            cmd = [
                str(ffmpeg_path),
                "-y", 
                "-i", str(video_path),
                "-ss", "00:00:03",
                "-vframes", "1",
                str(thumbnail_path)
            ]
            result = subprocess.run(cmd, capture_output=True, check=True)
            success = True
            break
        except FileNotFoundError:
            last_error = f"ffmpeg not found at {ffmpeg_path}"
        except subprocess.CalledProcessError as e:
            last_error = f"ffmpeg error: {e.stderr.decode(errors='replace')}"

    if success:
        print(f"Successfully exported thumbnail to: {thumbnail_path}")
    else:
        print(f"Failed to extract thumbnail. Error: {last_error}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
