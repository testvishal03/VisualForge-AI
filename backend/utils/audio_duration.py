"""Read actual PCM WAV sample counts; never estimate from narration text."""
from pathlib import Path
import wave


def audio_duration(path: str | Path) -> float:
    try:
        with wave.open(str(path), "rb") as audio:
            frames, rate = audio.getnframes(), audio.getframerate()
            if frames <= 0 or rate <= 0:
                raise ValueError("audio contains no samples")
            raw = audio.readframes(frames)
            if len(raw) != frames * audio.getnchannels() * audio.getsampwidth():
                raise ValueError("audio is truncated")
            return frames / rate
    except (OSError, EOFError, wave.Error, ValueError) as exc:
        raise ValueError(f"Cannot read WAV duration for {path}: {exc}") from exc
