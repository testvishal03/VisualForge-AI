# Automatic creator validation

## Implemented flow

- Prompt or script input, automatic length, one Generate video action.
- Prompt length chosen by the installed local model, validated against supported short and chapter targets. Script narration is preserved and determines runtime.
- Backend-owned automatic orchestration, independent of frontend polling; short and chapter pipelines continue through export.
- Estimated stage progress with actual rendered-frame counts, elapsed time, cancellation, retry, connection feedback, and reload recovery.
- One completed-video player and download link. Detailed editing remains available under Edit video.
- Optional output/workspace settings; default 720p, optional 1080p.

## Real local verification

- Prompt planner: `Explain evaporation for beginners using one everyday example.` The installed Qwen3 model chose 0.5 minutes and returned a reason. Result: `renderer/generated/automatic-length-result.json`.
- Chrome: pasted a 68-word, two-paragraph script, clicked Generate video once, observed stage progress, refreshed during generation, and confirmed the active job restored without duplication.
- First attempt exposed a Windows console encoding error in visual-planning logs. Fixed subprocess output to UTF-8 and made legacy-console progress printing tolerant without changing log-file content. Verified the failure/retry UI and retried the same project.
- Project `9c56b720524c`, **Automatic creation review - Evaporation**, completed in 136.32 seconds on retry. Two scenes, 779 frames, approximately 25.97 seconds at 720p. Full video decoding and source-audio alignment checks passed.
- Output: `data/editor/9c56b720524c/draft.mp4`; validation: `draft-validation.json` in that directory.
- Chrome displayed completion, measured runtime, a single player, and the download link automatically. Playback visibly advanced through the generated visuals and captions.

## Automated checks

- Full backend suite: 131 tests passed after the Unicode logging fix.
- Focused automatic-generation suite: 9 tests passed, including an additional long-prompt conversion test added after the full run.
- Frontend progress suite: 3 tests passed (actual frame ratios, monotonic estimates, multi-chapter weighting, completion boundary).
- Final HTTP and automatic-workflow checks: 18 tests passed after removing unnecessary per-scene media checks from workspace listing.
- New video was verified to reset the composer to an empty prompt; reload shows a loading state before restoring the studio.
- Syntax checks passed for app.js, creator.js, storyboard.js, and progress.js.

## Scope and limits

- Real end-to-end verification used a short pasted script; real-model duration selection was verified separately. Long automatic orchestration is unit-tested; no new 7-30 minute full export was generated in this UI milestone.
- Percentages before completion are estimates of pipeline work, not an elapsed-time prediction. Runtime is measured from narration; prompt targets are guidance, not guaranteed exact duration.
- A browser refresh can recover a running server job. Restarting the server does not resume an interrupted worker automatically; Retry uses saved checkpoints and caches.
- Existing visual-planning and rendering capabilities remain the video engine. This change simplifies their orchestration and frontend, rather than generating arbitrary cinematic footage.
