# VisualForge AI renderer

## Milestone 4

The root `backend/scripts/generate_video.py` command orchestrates generation and supplies a run-specific `props.json` to this renderer. It does not replace the legacy default data file. See the [one-command workflow](../README.md#milestone-4-one-command-generation).

`scene.visual` is optional. Its `kind` is `title`, `explanation`, `process`, `comparison`, `example`, or `takeaway`; `items` is empty except for exactly three process labels (maximum 70 characters each) or two comparison captions (maximum 180 characters each). `timeline.ts` rejects malformed visual data before rendering. Scenes without `visual` retain `TextScene`.

`VisualScene.tsx` provides the reusable layouts, local SVG icons, staggered entrances, and audio-duration-based progress indicator. It adds no external assets or dependencies. All layouts use the same narration WAV, sequence start, and end padding as the earlier renderer.

Render an existing run from this directory, replacing RUN_FOLDER with its actual path:

```powershell
npx.cmd remotion render VisualForgeVideo "../data/runs/RUN_FOLDER/video.mp4" --props="../data/runs/RUN_FOLDER/props.json" --concurrency=2
```

Prefer the root pipeline command: it manages verified reuse, retries, logs, and final media validation automatically. Milestone 3's historical report is [preserved here](../VALIDATION-MILESTONE3.md).

## Milestone 3

The existing React/TypeScript/Remotion renderer consumes `../data/video.generated.json` and local narration WAVs. Milestone 3 adds topic-to-storyboard generation before this audio/rendering flow. See the [project README](../README.md) for local model setup and the complete workflow.

From this directory:

```powershell
npm install
npm run generate:audio
npm run dev
npx remotion render VisualForgeVideo generated/generative-ai.mp4
npm run typecheck
npm test
```

Use `npm.cmd` and `npx.cmd` if PowerShell blocks script shims. The `generate:audio` shortcut expects the Windows virtual environment at `../backend/.venv`.

`VisualForgeVideo` remains 1920 x 1080, 16:9, 30 FPS, with a dynamic total duration. Generated scene `duration` is the actual audio length; `src/timeline.ts` adds the single configured end padding and uses `Math.ceil` to avoid cutting speech short. `SceneAudio` starts at its enclosing sequence's first frame and uses public-relative audio paths.

To provide different ready-to-render JSON through the CLI, wrap it as `{ "videoData": { "title": "...", "scenes": [...] } }` and pass `--props=./my-props.json`. Each scene must include `id`, `headline`, `body`, `narration`, `audio`, and a positive measured `duration`. WAV paths must refer to `public/audio/.../scene-ID.wav`. Prefer the Python generator so paths and durations remain accurate.

The original `generated/demo.mp4` and `generated/demo-with-voice.mp4` preserve Milestones 1 and 2. The Milestone 3 deliverable is `generated/generative-ai.mp4`. [Current validation](../VALIDATION.md), [Milestone 2 validation](VALIDATION-MILESTONE2.md), and [Milestone 1 validation](VALIDATION.md) are separate.
