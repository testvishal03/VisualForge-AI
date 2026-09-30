"""Generate a real 30-second-target studio draft with the configured GGUF model."""
import json
from pathlib import Path
import sys
import time
import argparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.llm.gguf_llm import model_status


def main():
    profile = model_status()
    if profile['backend'] != 'gguf' or not profile['ready']:
        raise RuntimeError('Install the GGUF profile before running this validation.')
    base = 'http://127.0.0.1:8765'
    token = json.load(urlopen(base + '/api/config'))['token']
    def api(path, body=None):
        request = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                          headers={'Content-Type': 'application/json', 'X-Editor-Token': token})
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    if api('/api/job').get('status') == 'running':
        raise RuntimeError('A studio job is running; let it finish first.')
    space = api('/api/workspaces', {'name': 'Qwen3 local model test', 'kind': 'single', 'audience': 'beginners'})
    started = time.monotonic()
    project = api('/api/projects', {'workspace_id': space['id'], 'mode': 'prompt',
                                  'text': 'How does a library work?', 'minutes': .5, 'profile': 'draft'})
    print('Created test video ' + project['id'], flush=True)
    previous = ''
    while True:
        job = api('/api/job')
        status = json.dumps({key: job.get(key) for key in ('status', 'phase', 'progress')})
        if status != previous:
            print(status, flush=True)
            previous = status
        if job['status'] != 'running':
            break
        time.sleep(3)
    result = api('/api/projects/' + project['id'])
    evidence = {'profile': profile, 'project': project['id'], 'workspace': space['id'],
                'seconds': round(time.monotonic() - started, 3), 'job': job,
                'draft_url': result.get('draft_url'), 'duration': result.get('duration'),
                'quality': result.get('quality')}
    (ROOT / 'data/gguf-validation.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    if job['status'] != 'complete' or not result.get('draft_url'):
        raise RuntimeError('Real-model validation failed; see data/gguf-validation.json and the project logs.')
    print('Draft ready: ' + base + result['draft_url'], flush=True)


def wait_for_installer(pid):
    """Keep validation queued while an already-owned Windows installer finishes."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)
    if not handle:
        raise RuntimeError(f'Cannot observe installer process {pid}; run validation directly after setup completes.')
    try:
        deadline = time.monotonic() + 4 * 3600
        while time.monotonic() < deadline:
            result = kernel.WaitForSingleObject(handle, 30000)
            if result == 0:
                code = wintypes.DWORD()
                if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 0:
                    raise RuntimeError('Installer did not finish successfully; see data/gguf-setup-xet.log.')
                return
            if result != 258:
                raise RuntimeError('Could not wait for the installer.')
        raise TimeoutError('Download exceeded four hours; validation did not run.')
    finally:
        kernel.CloseHandle(handle)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--after-process', type=int, help='Wait for this owned Windows installer process before validating')
    args = parser.parse_args()
    status_file = ROOT / 'data/gguf-validation-status.json'
    def status(state, **details):
        status_file.write_text(json.dumps({'status': state, **details}, indent=2), encoding='utf-8')
    try:
        if args.after_process:
            status('waiting_for_download', installer_pid=args.after_process)
            print('Validation queued behind model installation.', flush=True)
            wait_for_installer(args.after_process)
        status('validating')
        main()
        status('complete', evidence='data/gguf-validation.json')
    except Exception as exc:
        status('failed', error=str(exc))
        raise
