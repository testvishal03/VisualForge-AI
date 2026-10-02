"""Verify streams, full decoding, and source-to-render narration alignment."""
import json
import io
from pathlib import Path
import subprocess
import sys
import argparse

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.services.media_tools import compositor_dir, ffmpeg, ffprobe
RENDERER = ROOT / "renderer"
BIN = compositor_dir()


def run(*args):
    result = subprocess.run([str(arg) for arg in args], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout


def validate(video: Path, metadata: Path | None = None, profile='final') -> dict:
    timeline = json.loads(run("node", "--experimental-strip-types", RENDERER / "scripts/timeline.ts", *([metadata] if metadata else [])))
    probe = json.loads(run(ffprobe(), "-v", "error", "-show_streams", "-show_format", "-of", "json", video))
    picture = next(s for s in probe["streams"] if s["codec_type"] == "video")
    speech = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    assert profile in {'draft','final'}, 'Unknown render profile'
    assert (picture["width"], picture["height"]) == ((1280,720) if profile=='draft' else (1920, 1080)), "Wrong video dimensions"
    assert picture["codec_name"] == "h264" and speech["codec_name"] == "mp3", "Unexpected codecs"
    assert picture["r_frame_rate"] == f"{timeline['fps']}/1", "Wrong FPS"
    assert int(picture["nb_frames"]) == timeline["durationInFrames"], "Wrong frame count"
    assert abs(float(picture["duration"]) - timeline["durationInFrames"] / timeline["fps"]) < 0.00001
    run(ffmpeg(), "-v", "error", "-xerror", "-i", video, "-c:v", "rawvideo", "-c:a", "pcm_s16le", "-f", "null", "-")
    # Match the source WAV sample rate so comparisons cover every narrated sample.
    first = sf.info(RENDERER / "public" / timeline["scenes"][0]["scene"]["audio"])
    rate = first.samplerate
    decoded, decoded_rate = sf.read(io.BytesIO(run(ffmpeg(), "-v", "error", "-i", video, "-vn", "-ar", rate, "-ac", "1", "-c:a", "pcm_s16le", "-f", "wav", "-")), dtype="float32")
    assert decoded_rate == rate
    # With a music bed the padding holds quiet music, never narration: the bed stays below 0.03 RMS,
    # while narration running into the padding measures about 0.1.
    style = json.loads(Path(metadata).read_text(encoding='utf-8'))['videoData'].get('style', {}) if metadata else {}
    padding_limit = 0.035 if style.get('music') else 0.001
    results = []
    for entry in timeline["scenes"]:
        scene = entry["scene"]
        source, source_rate = sf.read(RENDERER / "public" / scene["audio"], dtype="float32")
        assert source_rate == rate and source.ndim == 1, "Expected matching mono WAVs"
        assert np.isfinite(source).all() and np.max(np.abs(source)) > 0, "Silent/invalid source WAV"
        start = round(entry["from"] / timeline["fps"] * rate)
        low = max(0, start - round(0.15 * rate))
        high = min(len(decoded) - len(source), start + round(0.15 * rate))
        # Correlate only the expected scene window. A full-video FFT for every
        # scene used multiple gigabytes for long exports without improving checks.
        window = decoded[low:high + len(source)]
        fft_size = 1 << (len(window) + len(source) - 1).bit_length()
        cross = np.fft.irfft(np.fft.rfft(window, fft_size) * np.fft.rfft(source[::-1], fft_size), fft_size)
        aligned = low + int(np.argmax(cross[len(source) - 1:high - low + len(source)]))
        print(f"Scene {scene['id']}: decoded audio offset {(aligned - start) / rate:.6f}s", file=sys.stderr)
        actual = decoded[aligned:aligned + len(source)]
        assert len(actual) == len(source), f"Scene {scene['id']} is truncated"
        correlation = float(np.corrcoef(source, actual)[0, 1])
        assert correlation > 0.98, f"Scene {scene['id']} does not match its source: correlation={correlation}"
        assert abs(aligned - start) / rate < 1 / timeline['fps'], f"Scene {scene['id']} starts more than one frame late"
        end = round((entry["from"] + entry["durationInFrames"]) / timeline["fps"] * rate)
        # Exclude 100 ms of normal codec filter ringing around the speech boundary.
        gap = decoded[start + len(source) + round(0.1 * rate):end]
        gap_rms = float(np.sqrt(np.mean(gap ** 2)))
        assert len(gap) > 0 and gap_rms < padding_limit, f"Scene {scene['id']} narration overlaps its end padding"
        results.append({"id": scene["id"], "wav": scene["audio"], "duration": len(source) / rate,
                        "startFrame": entry["from"], "frames": entry["durationInFrames"],
                        "sourceCorrelation": correlation, "paddingRms": gap_rms,
                        "codecOffsetSeconds": (aligned - start) / rate,
                        "sourcePeak": float(np.max(np.abs(source)))})
    return {"profile":profile, "width":picture['width'], "height":picture['height'], "fps": timeline["fps"], "frames": timeline["durationInFrames"],
            "videoDuration": float(picture["duration"]), "containerDuration": float(probe["format"]["duration"]),
            "videoCodec": picture["codec_name"], "audioCodec": speech["codec_name"],
            "audioSampleRate": speech["sample_rate"], "scenes": results, "fullDecode": "passed"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", nargs="?", type=Path, default=RENDERER / "generated/demo-with-voice.mp4")
    parser.add_argument("--metadata", type=Path, help="Run-specific metadata or Remotion props")
    parser.add_argument('--profile',choices=['draft','final'],default='final')
    parser.add_argument("--report", type=Path, default=RENDERER / "generated/media-validation.json")
    args = parser.parse_args()
    try:
        result = validate(args.video, args.metadata, args.profile)
        report = args.report
        report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"Media validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
