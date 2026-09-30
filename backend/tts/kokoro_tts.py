"""One cached, CPU-only Kokoro session; inference never downloads anything."""
from functools import lru_cache
import hashlib
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
DEFAULT_VOICE = "af_sarah"
SEED = 0
ASSETS = {
    "kokoro-v1.0.onnx": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}


def verify_asset(path: Path, expected: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"Missing Kokoro asset: {path}. Run backend/scripts/download_models.py first.")
    with path.open("rb") as stream:
        checksum = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
        actual = checksum.hexdigest()
    if actual != expected:
        raise RuntimeError(f"Kokoro asset checksum mismatch: {path}. Download it again.")


@lru_cache(maxsize=1)
def _model():
    for name, digest in ASSETS.items():
        verify_asset(MODEL_DIR / name, digest)
    try:
        import onnxruntime as ort
        from kokoro_onnx import Kokoro
        ort.set_seed(SEED)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.use_deterministic_compute = True
        session = ort.InferenceSession(
            str(MODEL_DIR / "kokoro-v1.0.onnx"),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        return Kokoro.from_session(session, str(MODEL_DIR / "voices-v1.0.bin"))
    except Exception as exc:
        raise RuntimeError(f"Could not initialize local Kokoro. Install backend/requirements.txt with Python 3.12: {exc}") from exc


def generate_speech(text: str, output_path: str | Path, voice: str | None = None) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Narration must be a non-empty string.")
    output = Path(output_path)
    selected_voice = voice or DEFAULT_VOICE
    try:
        model = _model()
        if selected_voice not in model.get_voices():
            raise ValueError(f"Unknown Kokoro voice: {selected_voice}")
        samples, sample_rate = model.create(text.strip(), voice=selected_voice, speed=1.0, lang="en-us")
        import numpy as np
        import soundfile as sf
        if len(samples) == 0 or not np.isfinite(samples).all() or np.max(np.abs(samples)) == 0:
            raise ValueError("TTS produced empty, invalid, or silent audio.")
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output), samples, sample_rate, subtype="PCM_16", format="WAV")
        if not output.is_file():
            raise RuntimeError("TTS did not create an audio file.")
        return str(output)
    except Exception as exc:
        raise RuntimeError(f"Speech generation failed for {output.name}: {exc}") from exc
