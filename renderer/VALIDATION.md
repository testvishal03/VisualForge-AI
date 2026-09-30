# Milestone 1 validation

Validated locally on Windows on 2026-09-26 with Node.js 24.18.0, npm 12.0.2, and Remotion 4.0.529.

## Results

- `npm.cmd install --no-fund`: clean completion, zero vulnerabilities, no install warnings after configuring the pinned esbuild install script.
- `npm.cmd run typecheck`: passed with no TypeScript errors.
- `npm.cmd test`: all three tests passed (demo timing, additional/fractional scenes, invalid inputs).
- `npm.cmd run dev -- --no-open`: Studio started at http://localhost:3000; `VisualForgeVideo` loaded successfully.
- Studio visual checks: headline and delayed body inspected at frame 15, settled first scene at frame 45, second scene at frame 195, third scene at frame 375. All text fits and the scene timeline is contiguous.
- `npx.cmd remotion render VisualForgeVideo generated/demo.mp4`: completed successfully, all 510 frames rendered and encoded.
- Bundled `ffprobe.exe` verified H.264, 1920 x 1080, 30/1 FPS, 510 decoded frames, exactly 17.000000 seconds, and 502890 bytes.
- Bundled `ffmpeg.exe -v error -i generated/demo.mp4 -c:v rawvideo -f null -`: all frames decoded, exit code 0, no errors.
- Actual MP4 playback in Chrome: observed playing, then `currentTime = 17`, `duration = 17`, `ended = true`, and no media error. Final scene displayed correctly.
- No AI APIs, LLM integration, paid APIs, TTS, LangChain, LangGraph, Hugging Face, or application backend were added.

All Milestone 1 acceptance criteria passed. No remaining issues for the supplied demo. Milestone 2 was not started.

## Files

The workspace was empty; no pre-existing project files were modified.

Created root `README.md` and, under `renderer`:

- `package.json`, `package-lock.json`, `tsconfig.json`, `remotion.config.ts`, `.gitignore`
- `src/types.ts`, `src/timeline.ts`, `src/data/demo.ts`
- `src/components/TextScene.tsx`, `src/Video.tsx`, `src/Root.tsx`, `src/index.ts`
- `tests/timeline.test.ts`
- `public/.gitkeep`, `generated/.gitkeep`, `generated/demo.mp4`
- `README.md`, `VALIDATION.md`

Installed dependencies and the rendering browser are local generated tooling, excluded through `node_modules/`.

## Output

`D:\Personal Project\VisualForge AI\renderer\generated\demo.mp4`
