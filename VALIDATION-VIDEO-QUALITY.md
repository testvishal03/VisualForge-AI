# Video quality review

Reviewed the updated studio and rendering pipeline on 2026-09-27. The existing UI design is retained.

## Findings and changes

1. **Explanations need causal detail.** Short and chapter script prompts now ask for the concrete input/situation, what changes and why, and an observable result. Worked examples should show an operation and result. Unfamiliar terms need plain-language definitions; analogies need boundaries. Existing word budgets remain in force. These are generation instructions, not a guarantee of factual accuracy.
2. **Decorative variety was sometimes unsupported by the script.** Removed hard-coded cost/latency statistics and automatic code-without-code selection. Keyword templates with unsupported labels fall back to an explanation. The semantic planner can choose an explicit analogy or takeaway; neural diagrams require an explicitly described network. Icon relevance takes precedence over avoiding repetition.
3. **Too much repeated text and constant movement.** Title and takeaway cards now have distinct large compositions. Other concept/example/analogy cards show the explanation once alongside the scene title. Background decoration settles; default transitions favor a real fade, while slide/zoom treatments use small movements. Authored wipes remain available.
4. **Long caption sentences competed with the diagram.** Captions are split into phrases of at most 12 words while preserving every word and measured sentence boundaries. Phrase timing within a sentence is estimated, not word-level forced alignment.
5. **New technical visuals needed stronger boundaries.** Statistic cards show exact supplied values, including decimals, without animating through invented intermediate numbers. Values absent from narration block export. Missing-code scenes remain editable and show a repair error. Code rendering preserves repeated text, uses a bounded scrolling viewport, and avoids browser-time CSS animation. Neural diagram labels wrap; animation is labeled schematic rather than measured activations.
6. **Bookend settings were disconnected from scheduling.** Workspace settings now map to renderer flags. The timeline, composition duration, validator, and combined narration include a 3-second intro and 5-second outro when enabled. All themes apply consistently. Long videos get bookends only at the first/last chapter; scene/style previews omit them. Runtime reporting includes them.

## Verification

- 114 backend tests passed, including editable legacy-scene repair, unsupported statistics, missing code, first/last chapter flags, and joined narration with bookend silence.
- Renderer typecheck and 14 tests passed, including frame offsets at multiple frame rates, caption text preservation, exact source-value requirements, and transition endpoints.
- A separate review project, `23324adb3012` (**Video quality review - Tokens**), reuses four narrated scenes from the existing tokens lesson. It changes presentation without modifying the source project. Forest theme and both bookends are enabled.
- Its complete 720p draft rendered in 107.913 seconds: 1,089 frames at 30 fps, 36.3 seconds including bookends. Full decode passed, narration correlations exceeded 0.99996, and maximum measured audio offset was 0.334 milliseconds. Output and report: `data/editor/23324adb3012/draft.mp4` and `draft-validation.json`.
- Inspected title, example, and outro frames from the actual video, plus synthetic neural/code/statistic readability fixtures under `renderer/generated/video-quality-qa`. The fixtures test layout, not factual lesson content.
- Corrected the studio's progress labels from “Fact Check” to “Editorial Checks” and from “1080p Render” to “Video Render”; completion messages now retain the task-specific status instead of always claiming a video is ready.

No new 7–30 minute export or local-LLM explanation-quality benchmark was performed for this change. Inspect the storyboard before publishing; the improvements support clarity but do not measure viewer retention or verify every factual claim.
