"""Checks that must pass before anything is merged into main (the stable line).

    backend/.venv/Scripts/python.exe backend/scripts/release_check.py

Runs the backend tests, the renderer type check and tests, the UI script tests, and the
script check on every example script (hand-designed visuals must have no errors or layout
warnings). Exits non-zero on the first failing group and says which one.
"""
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
NPM = 'npm.cmd' if sys.platform == 'win32' else 'npm'
NODE = 'node'


def run(name, command, cwd=ROOT):
    started = time.monotonic()
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    ok = result.returncode == 0
    print(f"{'PASS' if ok else 'FAIL'}  {name} ({time.monotonic() - started:.0f} s)", flush=True)
    if not ok:
        print((result.stdout + result.stderr)[-3000:])
    return ok


def examples():
    from backend.services.script_check import check
    ok = True
    for path in sorted((ROOT / 'data/examples').glob('*.txt')):
        report = check(path.read_text(encoding='utf-8'))
        problems = [i for i in report['issues'] if i['level'] == 'error' or i['message'].startswith('Layout:')]
        print(f"{'PASS' if not problems else 'FAIL'}  example {path.name}: {report['scenes']} scenes", flush=True)
        for issue in problems:
            print(f"      scene {issue.get('scene')}: {issue['message']}")
        ok = ok and not problems
    return ok


if __name__ == '__main__':
    steps = [
        lambda: run('backend tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'backend/tests', '-p', 'test_*.py']),
        lambda: run('renderer type check', [NPM, 'run', 'typecheck'], ROOT / 'renderer'),
        lambda: run('renderer tests', [NPM, 'test'], ROOT / 'renderer'),
        lambda: run('studio UI tests', [NODE, '--test', 'review/progress.test.cjs', 'review/script-fixes.test.cjs']),
        examples,
    ]
    for step in steps:
        if not step():
            print('\nRelease check FAILED: do not merge into main.')
            raise SystemExit(1)
    print('\nRelease check passed: safe to merge into main.')
