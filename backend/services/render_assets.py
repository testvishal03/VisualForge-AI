"""Give each render only the narration it uses, instead of the whole shared audio cache.

Remotion copies its public directory on every CLI call. The shared cache under
renderer/public/audio grows with every video, so each render got slower over time.
A per-project public directory of hard links keeps that copy small and constant.
"""
import json
import os
from pathlib import Path
import shutil


def referenced_audio(props: Path):
    data = json.loads(props.read_text(encoding='utf-8'))['videoData']
    return sorted({scene['audio'] for scene in data.get('scenes', []) if isinstance(scene.get('audio'), str)})


def prepare_public(root: Path, folder: Path, props: Path) -> Path:
    """Mirror exactly the props' audio into folder/render-public and return that directory."""
    source, target = root/'renderer/public', folder/'render-public'
    wanted = set(referenced_audio(props))
    for relative in wanted:
        original, link = source/relative, target/relative
        if not original.is_file():
            continue  # A missing narration fails in the renderer with its own clear message.
        if link.is_file() and link.stat().st_size == original.stat().st_size and link.stat().st_mtime >= original.stat().st_mtime:
            continue
        link.parent.mkdir(parents=True, exist_ok=True)
        link.unlink(missing_ok=True)
        try:
            os.link(original, link)
        except OSError:
            shutil.copy2(original, link)
    # Drop narration no longer referenced so the directory never accumulates.
    if (target/'audio').is_dir():
        for file in (target/'audio').rglob('*'):
            if file.is_file() and file.relative_to(target).as_posix() not in wanted:
                file.unlink()
        for directory in sorted((d for d in (target/'audio').rglob('*') if d.is_dir()), reverse=True):
            if not any(directory.iterdir()):
                directory.rmdir()
    target.mkdir(parents=True, exist_ok=True)
    return target


def with_public_dir(root: Path, folder: Path, command: list):
    """Append --public-dir for render and still commands that carry --props."""
    if not command or command[0] not in {'render', 'still'}:
        return command
    props = next((str(arg).split('=', 1)[1] for arg in command if str(arg).startswith('--props=')), None)
    if not props or not Path(props).is_file():
        return command
    return [*command, f'--public-dir={prepare_public(root, folder, Path(props))}']
