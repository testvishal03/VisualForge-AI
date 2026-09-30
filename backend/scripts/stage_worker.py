"""Run a stage in its own process and record that process's peak memory."""
import ctypes
import json
from pathlib import Path
import runpy
import sys
import time


def peak_memory_bytes():
    if sys.platform == "win32":
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [(key, ctypes.c_size_t) for key in (
                "peak", "working", "peakPaged", "paged", "peakNonPaged", "nonPaged", "pagefile", "peakPagefile")]
        stats = Counters()
        stats.cb = ctypes.sizeof(stats)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        api = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
        api.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if api(kernel.GetCurrentProcess(), ctypes.byref(stats), stats.cb):
            return stats.peak
        return None
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value if sys.platform == "darwin" else value * 1024
    except ImportError:
        return None


if __name__ == "__main__":
    metrics = Path(sys.argv[1])
    target = Path(sys.argv[2]).resolve()
    sys.argv = [str(target), *sys.argv[3:]]
    started = time.monotonic()
    try:
        runpy.run_path(str(target), run_name="__main__")
    finally:
        metrics.parent.mkdir(parents=True, exist_ok=True)
        metrics.write_text(json.dumps({"seconds": round(time.monotonic()-started, 3),
                                      "peak_working_set_bytes": peak_memory_bytes(),
                                      "memory_scope": "stage Python process; excludes subprocesses"}, indent=2), encoding="utf-8")
