"""Explicit one-time download, separate from offline TTS generation."""
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.tts.kokoro_tts import ASSETS, MODEL_DIR, verify_asset


def main() -> int:
    try:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        for name, digest in ASSETS.items():
            target = MODEL_DIR / name
            if target.exists():
                verify_asset(target, digest)
                print(f"Verified {name}")
                continue
            partial = target.with_suffix(target.suffix + ".part")
            try:
                print(f"Downloading {name}...", flush=True)
                urllib.request.urlretrieve(
                    f"https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/{name}", partial
                )
                verify_asset(partial, digest)
                partial.replace(target)
            finally:
                partial.unlink(missing_ok=True)
        return 0
    except Exception as exc:
        print(f"Model setup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
