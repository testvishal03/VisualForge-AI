import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.services.editor_store import EditorStore

SCENE_END_PADDING_SECONDS = 0.5
SPEECH_RATE = 0.42

def format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def get_scene_duration(scene) -> float:
    if 'duration' in scene:
        return float(scene['duration']) + SCENE_END_PADDING_SECONDS
    
    narration = scene.get('narration', '')
    words = len(narration.split()) if narration else 0
    return (words * SPEECH_RATE) + SCENE_END_PADDING_SECONDS

def main():
    parser = argparse.ArgumentParser(description="Export a YouTube-ready text file for a project.")
    parser.add_argument("project_id", nargs="?", help="The ID of the project to export")
    parser.add_argument("--list", action="store_true", help="List all available projects")
    args = parser.parse_args()

    store_dir = ROOT / 'data' / 'editor'
    store = EditorStore(store_dir)

    if args.list:
        projects = store.list()
        if not projects:
            print("No projects found.")
            return
        
        print("Available projects:")
        for proj in projects:
            print(f"  {proj['id']} - {proj.get('title', 'Untitled')}")
        return

    if not args.project_id:
        parser.print_help()
        sys.exit(1)

    try:
        project = store.load(args.project_id)
    except Exception as e:
        print(f"Error loading project '{args.project_id}': {e}", file=sys.stderr)
        sys.exit(1)

    document = project.get('document')
    if not document:
        print(f"Error: Project '{args.project_id}' does not have a generated document yet.", file=sys.stderr)
        sys.exit(1)

    title = project.get('title') or project.get('topic', 'Untitled Video')
    topic = project.get('topic', 'unknown topic')

    scenes = document.get('scenes', [])
    if not scenes:
        print(f"Error: Project '{args.project_id}' document has no scenes.", file=sys.stderr)
        sys.exit(1)

    chapters = []
    current_time = 0.0

    for scene in scenes:
        chapters.append({
            'timestamp': format_timestamp(current_time),
            'headline': scene.get('headline', 'Untitled Chapter')
        })
        current_time += get_scene_duration(scene)

    chapters_text = "\n".join([f"{c['timestamp']} {c['headline']}" for c in chapters])

    tags = [t.strip() for t in topic.split() if t.strip()] + ['explained', 'visual explainer', f"how does {topic} work", f"learn {topic}"]
    tags_text = ", ".join(tags)

    export_content = f"""=== YouTube Export: {title} ===

CHAPTER TIMESTAMPS (paste into description):
{chapters_text}

SUGGESTED TITLE:
{title} | Explained Visually

SUGGESTED DESCRIPTION:
In this video, we explore {topic}.

Chapters:
{chapters_text}

CREATED WITH: VisualForge AI (local, no cloud)

SUGGESTED TAGS:
{tags_text}
"""

    out_file = store.folder(args.project_id) / 'youtube-export.txt'
    
    try:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(export_content, encoding='utf-8')
        print(export_content)
        print(f"\nSuccessfully wrote export to: {out_file}")
    except Exception as e:
        print(f"Error writing export file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
