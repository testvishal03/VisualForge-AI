# VisualForge AI — Milestone 2 validation

Validated on Windows, 2026-09-26. Milestone 3 was not started.

## Environment

| Item | Value |
| --- | --- |
| Python used | 3.12.14, isolated in `backend/.venv` |
| System Python | 3.14.6, unchanged |
| Node.js | 24.18.0 |
| npm | 12.0.2 |
| Remotion | 4.0.529 |
| TTS | Kokoro v1.0 through `kokoro-onnx` 0.6.1, local CPU inference |
| Voice | `af_sarah`, `en-us`, speed 1.0, seed 0 |
| Other directly used Python packages | SoundFile 0.14.0, NumPy 2.5.3, ONNX Runtime 1.30.0 |

All 16 installed Python dependencies are pinned in `backend/requirements.lock.txt`. Kokoro model and voice SHA-256 checksums match the official release assets. No fallback TTS engine, remote inference, paid API, or external subscription was used. Python 3.12 was installed locally because the current Kokoro package excludes the system Python 3.14.

## Generated narration and timing

Active WAV directory: `renderer/public/audio/9489d771301e0b99/`.

| WAV | Measured narration duration | Start frame | Scene frames | Scene length with padding |
| --- | ---: | ---: | ---: | ---: |
| `scene-1.wav` | 5.353958333 s | 0 | 176 | 5.866666667 s |
| `scene-2.wav` | 7.443291667 s | 176 | 239 | 7.966666667 s |
| `scene-3.wav` | 7.584000000 s | 415 | 243 | 8.100000000 s |

Source WAVs are mono PCM signed 16-bit, 24 kHz. Actual duration comes from WAV sample counts, not word estimates. Each scene gets 0.5 seconds of end padding, then rounds upward to a whole frame. There are no manual scene starts or lengths in the authored JSON.

Total timeline: **658 frames / 30 FPS = 21.933333333 seconds**. The MP4 container reports **21.936 seconds**, including approximately 2.7 ms of audio packet rounding after the final padded scene.

## Validation performed

- Environment creation, pinned dependency installation, and model download/checksum verification completed successfully.
- Actual local TTS generated all three WAVs. Two subsequent seeded runs produced identical SHA-256 hashes for every WAV.
- Five Python tests passed: source schema, generation/rerun, failed-batch metadata preservation, malformed JSON/missing WAV/invalid folder handling, and real generated audio metadata.
- Four TypeScript/Node tests passed: source-to-metadata/WAV agreement, contiguous padded timing, arbitrary scene counts and FPS values, and invalid inputs.
- TypeScript compilation passed with no errors, including renderer source, tests, configuration, and timeline export script.
- `pip check`: no broken requirements. npm install/audit: zero vulnerabilities.
- Remotion Studio loaded `VisualForgeVideo`. All scenes and their audio tracks appeared. Preview played with audio unmuted, loaded audio state (`readyState=4`), advancing playback time, and no media error.
- Deliberately referencing a missing WAV in CLI props produced a clear `missing WAV` error and nonzero exit status before rendering.
- The narrated MP4 rendered successfully with all 658 frames encoded.
- The media validator fully decoded video and audio and compared every narration with its complete source WAV at the expected scene start. It also checked end padding for unintended audio overlap.
- Chrome played the narrated MP4 through to its final scene with audio unmuted and no media error.

Detailed sample-level measurements are saved in `renderer/generated/media-validation.json`. The final source correlations are 0.9999669, 0.9999741, and 0.9999655. Measured offsets are 0 ms, +0.333 ms, and -0.333 ms; padding RMS is zero or below 0.000001. The file is 1,009,244 bytes.

## Output and synchronization

- Resolution: **1920 x 1080**, 16:9 landscape.
- Frame rate: **30 FPS**.
- Video codec: **H.264**.
- Audio codec: **MP3**, 192 kbps, 48 kHz, stereo, inside the MP4 container.
- WAV narration is neither trimmed nor looped. Every narration finishes before its scene ends.
- The default raw AAC intermediate introduced approximately 43 ms of encoder delay. The final configuration uses MP3, which preserves delay metadata through this Remotion version's audio pipeline. This retains the standard direct MP4 render command without manual post-processing or a guessed scene offset.

Final file: **`D:\Personal Project\VisualForge AI\renderer\generated\demo-with-voice.mp4`**.

The original silent `renderer/generated/demo.mp4` remains unchanged; its historical report is `renderer/VALIDATION.md`.

## Commands executed

Key successful commands (run from the project root unless noted):

```powershell
python -m pip install --target backend/.bootstrap uv
backend/.bootstrap/bin/uv.exe python install 3.12 --install-dir backend/.python --no-registry --no-bin
backend/.bootstrap/bin/uv.exe venv backend/.venv --python backend/.python/cpython-3.12.14-windows-x86_64-none/python.exe --clear --seed
backend/.venv/Scripts/python.exe -m pip install kokoro-onnx==0.6.1 soundfile==0.14.0
backend/.venv/Scripts/python.exe backend/scripts/download_models.py
backend/.venv/Scripts/python.exe backend/scripts/generate_audio.py
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v
backend/.venv/Scripts/python.exe -m pip check
cd renderer
npm.cmd run generate:audio
npm.cmd run typecheck
npm.cmd test
npm.cmd run dev -- --no-open
npx.cmd remotion render VisualForgeVideo generated/demo-with-voice.mp4
cd ..
backend/.venv/Scripts/python.exe backend/scripts/validate_render.py
```

The model assets were downloaded from the official GitHub release with `curl.exe` and verified using `download_models.py`. Direct `ffprobe`/`ffmpeg` checks and a temporary loopback-only file server were also used for playback validation. The `--clear` bootstrap flag above was used only on the empty environment created during this task; it is not needed for normal setup.

## Files created

- `.gitignore`, `VALIDATION.md`
- `data/video.json`, `data/video.generated.json`
- `backend/requirements.txt`, `backend/requirements.lock.txt`, package `__init__.py` files
- `backend/tts/kokoro_tts.py`
- `backend/utils/scene_data.py`, `backend/utils/audio_duration.py`
- `backend/scripts/download_models.py`, `generate_audio.py`, `validate_render.py`
- `backend/tests/test_pipeline.py`, `backend/models/.gitkeep`
- `renderer/src/components/SceneAudio.tsx`, `renderer/scripts/timeline.ts`
- Three active WAVs listed above, generated metadata, MP4, and machine-readable media validation report. Earlier generated audio batches are retained in separate content folders.
- Ignored local tooling: Python runtime, venv, bootstrap helper, Kokoro model, and voices.

## Files modified

- Root and renderer `README.md`
- `renderer/package.json`, synchronized npm lockfile, `tsconfig.json`, `remotion.config.ts`
- `renderer/src/types.ts`, `timeline.ts`, `data/demo.ts`, `Root.tsx`, `Video.tsx`, `components/TextScene.tsx`
- `renderer/tests/timeline.test.ts`

## Acceptance

All Milestone 2 acceptance criteria passed: local TTS, valid per-scene audio, measured durations, audio-aware sequencing, synchronized complete narration without overlap, working Studio, passing tests/typecheck, playable narrated MP4, and updated documentation. No remaining blocking issues. No Milestone 3 features were added.
