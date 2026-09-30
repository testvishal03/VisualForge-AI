"""Sequential, observable subprocesses; stop only the current stage's process tree."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


def console_progress(message):
    # Keep Unicode in UTF-8 log files, but tolerate legacy Windows consoles.
    encoding=getattr(sys.stdout,'encoding',None) or 'utf-8'
    print(message.encode(encoding,errors='replace').decode(encoding),flush=True)


def stop_process(process):
    if process.poll() is not None:
        return
    if sys.platform == 'win32':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
    else:
        os.killpg(process.pid, signal.SIGTERM)
    process.wait(timeout=15)


def execute(command: list, *, cwd: Path, log: Path, timeout: int = 3600, cancel_event=None) -> dict:
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log.open('a', encoding='utf-8') as output, log.open('r', encoding='utf-8', errors='replace') as reader:
        reader.seek(0, 2)
        process = subprocess.Popen([str(x) for x in command], cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                   env={**os.environ,'PYTHONIOENCODING':'utf-8'},
                                   start_new_session=sys.platform != 'win32',
                                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        try:
            last_progress = 0
            last_heartbeat = 0
            while process.poll() is None:
                if cancel_event is not None and cancel_event.is_set():
                    raise InterruptedError('Cancelled; completed outputs remain available.')
                elapsed = time.monotonic()-started
                if elapsed > timeout:
                    raise TimeoutError(f"Stage exceeded {timeout}s. See {log}")
                if elapsed-last_progress >= 5:
                    lines = reader.read().strip().splitlines()
                    if lines:
                        console_progress('  '+lines[-1][:250])
                        last_heartbeat = elapsed
                    elif elapsed-last_heartbeat >= 30:
                        console_progress(f'  {log.stem}: still running ({elapsed:.0f}s elapsed).')
                        last_heartbeat = elapsed
                    last_progress = elapsed
                time.sleep(.25)
            if process.returncode:
                raise RuntimeError(f"Stage exited with code {process.returncode}. See {log}")
        finally:
            stop_process(process)
    return {"seconds": round(time.monotonic()-started, 3), "log": str(log),
            "memory_scope": "See worker metrics for Python stages; renderer child-tree memory is not measured."}


def python_stage(script: Path, args: list, *, root: Path, folder: Path, name: str, timeout: int, cancel_event=None):
    metrics = folder / 'logs' / f'{name}.metrics.json'
    result = execute([sys.executable, '-u', root/'backend/scripts/stage_worker.py', metrics, script, *args],
                     cwd=root, log=folder/'logs'/f'{name}.log', timeout=timeout, cancel_event=cancel_event)
    result.update(json.loads(metrics.read_text(encoding='utf-8')))
    return result


def node_executable():
    node = shutil.which('node')
    if not node:
        raise ValueError('Node.js is required. Install project dependencies in renderer first.')
    return node
