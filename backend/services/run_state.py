"""Durable stage checkpoints with content hashes and exclusive run ownership."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import time

from backend.services.script_generator import write_json_atomic


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@contextmanager
def run_lock(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".lock").open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if __import__('sys').platform == "win32":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError("This video run is already active. Wait for it or use a different run directory.") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if __import__('sys').platform == "win32":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


class RunState:
    def __init__(self, folder: Path, *, force=False, progress=print):
        self.path = folder / "run.json"
        self.force, self.progress = force, progress
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if self.data.get("version") != 1 or not isinstance(self.data.get("stages"), dict):
                raise ValueError("Invalid run manifest")
        except (OSError, ValueError):
            self.data = {"version": 1, "stages": {}}
        self.executed, self.reused = [], []

    def save(self):
        write_json_atomic(self.path, self.data)

    def stage(self, name, key, action, artifacts, *, attempts=1):
        previous = self.data['stages'].get(name, {})
        outputs = previous.get('artifacts', {})
        intact = bool(outputs) and all(Path(p).is_file() and file_hash(Path(p)) == digest for p, digest in outputs.items())
        if not self.force and previous.get('status') == 'complete' and previous.get('fingerprint') == key and intact:
            self.progress(f"[{name}] Reusing verified outputs.")
            self.reused.append(name)
            previous['last_action'] = 'reused'
            self.save()
            return
        self.executed.append(name)
        for attempt in range(1, attempts+1):
            started = time.monotonic()
            entry = {"status": "running", "fingerprint": key, "attempt": attempt, "last_action": "executed"}
            self.data['stages'][name] = entry
            self.data['status'] = 'running'
            self.save()
            self.progress(f"[{name}] Running ({attempt}/{attempts})...")
            try:
                metrics = action() or {}
                paths = artifacts() if callable(artifacts) else artifacts
                if not paths or any(not Path(p).is_file() for p in paths):
                    raise ValueError(f"{name} did not produce all required outputs")
                entry.update(status='complete', artifacts={str(Path(p).resolve()): file_hash(Path(p)) for p in paths}, metrics=metrics)
            except BaseException as exc:
                entry.update(status='interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed', error=str(exc))
                self.data['status'] = entry['status']
                self.data['failed_stage'] = name
                if isinstance(exc, (KeyboardInterrupt, SystemExit)) or attempt == attempts:
                    raise
                self.progress(f"[{name}] Failed: {exc}. Retrying only this stage.")
            else:
                self.progress(f"[{name}] Complete.")
                return
            finally:
                entry['seconds'] = round(time.monotonic()-started, 3)
                self.save()
