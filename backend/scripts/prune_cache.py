import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def find_audio_hashes(json_data, hashes):
    if isinstance(json_data, dict):
        for k, v in json_data.items():
            if isinstance(v, str):
                match = re.search(r'audio/([a-f0-9]+)/', v)
                if match:
                    hashes.add(match.group(1))
            else:
                find_audio_hashes(v, hashes)
    elif isinstance(json_data, list):
        for item in json_data:
            find_audio_hashes(item, hashes)

def main():
    parser = argparse.ArgumentParser(description="Prune unreferenced audio cache folders.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be deleted without deleting")
    parser.add_argument("--days", type=int, default=7, help="Delete unreferenced folders older than this many days")
    args = parser.parse_args()

    audio_dir = ROOT / 'renderer' / 'public' / 'audio'
    editor_data_dir = ROOT / 'data' / 'editor'
    runs_dir = ROOT / 'data' / 'runs'

    referenced_hashes = set()

    # Scan data/editor/*/project.json
    if editor_data_dir.exists():
        for proj_file in editor_data_dir.glob('*/project.json'):
            try:
                data = json.loads(proj_file.read_text(encoding='utf-8'))
                find_audio_hashes(data, referenced_hashes)
            except Exception:
                pass

    # Scan data/runs/*/video.generated.json
    if runs_dir.exists():
        for gen_file in runs_dir.glob('*/video.generated.json'):
            try:
                data = json.loads(gen_file.read_text(encoding='utf-8'))
                find_audio_hashes(data, referenced_hashes)
            except Exception:
                pass

    # Scan data/video.generated.json
    root_gen_file = ROOT / 'data' / 'video.generated.json'
    if root_gen_file.exists():
        try:
            data = json.loads(root_gen_file.read_text(encoding='utf-8'))
            find_audio_hashes(data, referenced_hashes)
        except Exception:
            pass

    if not audio_dir.exists():
        print(f"Audio cache directory not found: {audio_dir}")
        return

    all_folders = [d for d in audio_dir.iterdir() if d.is_dir()]
    
    now = time.time()
    threshold_seconds = args.days * 24 * 3600

    to_delete = []
    total_size_mb = 0.0
    reclaimed_size_mb = 0.0

    for folder in all_folders:
        folder_size = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
        total_size_mb += folder_size / (1024 * 1024)

        if folder.name not in referenced_hashes:
            mtime = folder.stat().st_mtime
            age_seconds = now - mtime
            if age_seconds > threshold_seconds:
                to_delete.append({
                    'path': folder,
                    'size_mb': folder_size / (1024 * 1024),
                    'age_days': age_seconds / (24 * 3600)
                })
                reclaimed_size_mb += folder_size / (1024 * 1024)

    print(f"Audio cache: {len(all_folders)} folders, {total_size_mb:.1f} MB total")
    print(f"Referenced: {len(referenced_hashes)} folders")
    print(f"Unreferenced and old (>{args.days} days): {len(to_delete)} folders, {reclaimed_size_mb:.1f} MB")

    if not to_delete:
        return

    if args.dry_run:
        print("\nWould delete (--dry-run):")
        for item in to_delete:
            p = item['path'].relative_to(ROOT)
            print(f"  {p}/  ({item['size_mb']:.1f} MB, {item['age_days']:.1f} days old)")
        print("\nRun without --dry-run to delete.")
    else:
        print("\nDeleting...")
        for item in to_delete:
            try:
                shutil.rmtree(item['path'])
                p = item['path'].relative_to(ROOT)
                print(f"Deleted: {p}/")
            except Exception as e:
                print(f"Error deleting {item['path']}: {e}")
        
        print(f"\nReclaimed {reclaimed_size_mb:.1f} MB.")

if __name__ == "__main__":
    main()
