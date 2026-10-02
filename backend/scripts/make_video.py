"""Make a finished video from a script without the browser studio, for servers and notebooks.

    python backend/scripts/make_video.py --script lesson.txt --out output/

It runs the studio's own server code in this process (the same project, workspace and job
pipeline as clicking Prepare in the browser) and copies the results into --out: the video,
its thumbnail, the YouTube description and a JSON report. Every stage runs locally, so on a
GPU server set VISUALFORGE_GPU_LAYERS=99 to put the language model on the GPU and
VISUALFORGE_PLANNING_LIMIT=999 to let the AI plan every scene.
"""
import argparse
import json
import shutil
import sys
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--script', type=Path, required=True, help='Narration as .txt, or notes / a production script as .md')
    parser.add_argument('--out', type=Path, required=True, help='Folder for video.mp4, thumbnail.png, description.txt, report.json')
    parser.add_argument('--title', help='Video title; by default named from the script')
    parser.add_argument('--voice', default='af_heart', help='Kokoro voice id (default af_heart)')
    parser.add_argument('--music', action='store_true', help='Add the quiet background music bed')
    parser.add_argument('--no-intro', action='store_true')
    parser.add_argument('--no-outro', action='store_true')
    parser.add_argument('--quality', choices=['draft', 'final'], default='draft', help='draft is 720p; final is 1080p')
    parser.add_argument('--store', type=Path, default=ROOT / 'data/headless', help='Project store kept between runs, so reruns reuse caches')
    args = parser.parse_args(argv)
    text = args.script.read_text(encoding='utf-8')

    from backend.scripts.review_app import make_server
    server = make_server(0, ROOT, args.store)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'

    def call(path, body=None):
        headers = {'Content-Type': 'application/json', 'X-Editor-Token': token} if body is not None else {}
        request = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers,
                          method='POST' if body is not None else 'GET')
        with urlopen(request, timeout=600) as response:
            raw = response.read()
            return json.loads(raw) if response.headers.get('Content-Type', '').startswith('application/json') else raw

    try:
        token = call('/api/config')['token']
        workspace = call('/api/workspaces', {'name': (args.title or args.script.stem)[:100], 'kind': 'single', 'voice': args.voice,
                                             'music': args.music, 'show_intro': not args.no_intro, 'show_outro': not args.no_outro})
        body = {'mode': 'script', 'text': text, 'profile': args.quality, 'automatic': True, 'approval_required': False,
                'workspace_id': workspace['id'], **({'title': args.title} if args.title else {})}
        project = call('/api/projects', body)
        started, last = time.monotonic(), None
        print(f'Project {project["id"]}: generating "{project.get("topic", "")}"', flush=True)
        while True:
            job = call('/api/job')
            state = (job.get('phase'), job.get('message'))
            if state != last:
                print(f"[{round(time.monotonic() - started):>5}s] {job.get('phase') or ''} {job.get('message') or ''}".rstrip(), flush=True)
                last = state
            if job.get('project') == project['id'] and job.get('status') in {'complete', 'failed', 'cancelled'}:
                break
            time.sleep(5)
        if job['status'] != 'complete':
            raise SystemExit(f"Generation {job['status']}: {job.get('error') or job.get('message')}")
        result = call(f"/api/projects/{project['id']}")
        args.out.mkdir(parents=True, exist_ok=True)
        folder = args.store / project['id']
        video = folder / ('draft.mp4' if args.quality == 'draft' else 'video.mp4')
        shutil.copy2(video, args.out / 'video.mp4')
        kit = folder / 'publish'
        for name in ('thumbnail.png', 'description.txt'):
            if (kit / name).is_file():
                shutil.copy2(kit / name, args.out / name)
        report = {'project': project['id'], 'title': result.get('topic'), 'seconds': round(time.monotonic() - started),
                  'scenes': len(result['document']['scenes']), 'quality': args.quality, 'voice': args.voice, 'music': args.music,
                  'validation': json.loads((folder / f"{video.stem}-validation.json").read_text(encoding='utf-8'))}
        (args.out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f"Done in {report['seconds']} s: {args.out / 'video.mp4'} ({report['scenes']} scenes)", flush=True)
        return 0
    finally:
        server.editor_jobs.close()
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    raise SystemExit(main())
