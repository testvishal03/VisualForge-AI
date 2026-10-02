"""The ffmpeg and ffprobe that ship with Remotion's compositor for this platform.

npm installs only the compositor package that matches the machine (for example
compositor-win32-x64-msvc on Windows, compositor-linux-x64-gnu on Linux), so the
same project runs on a laptop and on a Linux server without a separate ffmpeg.
"""
from functools import lru_cache
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=None)
def compositor_dir(root: Path = ROOT) -> Path:
    base = root / 'renderer/node_modules/@remotion'
    machine = {'amd64': 'x64', 'x86_64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}.get(platform.machine().lower(), 'x64')
    names = {'win32': [f'compositor-win32-{machine}-msvc'], 'darwin': [f'compositor-darwin-{machine}'],
             'linux': [f'compositor-linux-{machine}-gnu', f'compositor-linux-{machine}-musl']}.get(sys.platform, [])
    for name in names:
        if (base / name).is_dir():
            return base / name
    found = sorted(base.glob('compositor-*'))
    if not found:
        raise RuntimeError('Remotion compositor missing. Run npm install in renderer.')
    return found[0]


def tool(name: str, root: Path = ROOT) -> Path:
    """Path to `ffmpeg` or `ffprobe` from the compositor, with .exe on Windows."""
    return compositor_dir(root) / (f'{name}.exe' if sys.platform == 'win32' else name)


def ffmpeg(root: Path = ROOT) -> Path:
    return tool('ffmpeg', root)


def ffprobe(root: Path = ROOT) -> Path:
    return tool('ffprobe', root)
