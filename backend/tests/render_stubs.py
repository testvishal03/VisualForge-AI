"""Keep workflow tests independent of Chromium; real cache rendering has its own smoke test."""
from pathlib import Path


def stub_output(command):
    """Where a stubbed Remotion command writes: a bundle's index.html, or the render/still output."""
    args = [str(a) for a in command]
    if 'bundle' in args:
        out = Path(next(a.split('=', 1)[1] for a in args if a.startswith('--out-dir=')))
        out.mkdir(parents=True, exist_ok=True)
        return out/'index.html'
    return Path(next(a for a in args if a.endswith(('.mp4', '.png'))))


def stub_props(command):
    return Path(next(str(a).split('=', 1)[1] for a in command if str(a).startswith('--props=')))

def cached(jobs,project,data,props,pending,profile,render):
    render(['render','VisualForgeVideo',pending,f'--props={props}','--concurrency=2',*(['--scale=0.6666666666666666'] if profile=='draft' else [])],'render')
