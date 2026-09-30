# Chapter video workflow

Implemented September 27, 2026.

The studio now supports a 7–30 minute target through separately saved chapter projects. The outline and narration scripts have explicit review gates. Editing a chapter invalidates its derived output; completed, unchanged chapters can be reused after failure or cancellation. Chapters inherit their parent workspace style and lifecycle.

Narration is measured from generated audio. The duration rewrite uses that measurement to request a longer or shorter explanation. Target duration is guidance, not a guarantee; review and measure again after rewriting. Scene validation still enforces complete paragraphs and 15–60 words, while the narrower drafting word target is advisory.

Assembly copies chapter video streams and rebuilds narration on a frame-aligned timeline from source WAVs. The assembled MP4 must pass full decode, frame count, source-audio correlation, and silent-padding checks before it becomes downloadable. The audio validator searches around each expected scene start to avoid repeatedly correlating against the entire long video.

## Checks

- Backend regression suite: 93 tests passed (15.669 seconds), including approval atomicity, duration edits, independent workspace copies, resume behavior, and validated generation-cache reuse. Final rerun recorded in `data/long-video-tests.log`.
- Studio JavaScript syntax checked with `node --check review/app.js`.
- Renderer TypeScript check passed; all seven renderer tests passed with access to the existing narration WAVs.
- Real assembly smoke test: two existing rendered chapters joined into a 46.10-second MP4. All five narration offsets were zero; full decode and timing validation passed. Evidence: `data/chapter-join-smoke/draft-validation.json`.
- A real Qwen3 seven-minute-target water-cycle project (`5a43de42bb85`) completed all four chapter scripts and a 452.93-second 1080p export. Full decode and all 28 narration alignment checks passed; report: `data/editor/5a43de42bb85/video-validation.json`. The original style used in that export has since been revised; see `VALIDATION-MOTION.md` for the separately validated new-style preview.
- A complete 30-minute export has not been stress-tested on this laptop.

Local CPU generation can be slow. These checks do not establish factual accuracy; review the script and preview before publishing.
