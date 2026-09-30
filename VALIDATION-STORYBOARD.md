# Storyboard review validation

Validated on 2026-09-27 on the local Windows development machine.

- Backend: 104 unittest tests passed. Coverage includes stop-before-render, approval invalidation, stale revisions, selected-scene preview isolation, and atomic chapter storyboard validation. The initial sandbox run encountered audio access and subprocess termination restrictions; the unrestricted verification passed.
- Renderer: 9 tests and TypeScript typecheck passed, including unchanged audio frame scheduling across animation treatments and measured-cue preference.
- Chrome: inspected the three-scene storyboard, generated a scene preview through Play scene, and approved the test storyboard through the UI.
- Real media: project `6d0eb387ed2a` (LLM storyboard review) uses previously generated local-AI scene plans with assembly, focus, and progressive reveal. All three scene MP4s passed full decode and source-audio correlation validation with zero measured codec offset. Cached narration was reused. Extracted frames were inspected for readable text and layout.
- After UI approval, the complete 720p draft rendered in 72.887 seconds: 883 frames at 30 fps, 29.433 seconds. Full decode passed; all source correlations exceeded 0.99996 and measured audio offsets were at most 0.334 milliseconds. All three narration files were reused. Output: `data/editor/6d0eb387ed2a/draft.mp4`; report: `draft-validation.json` in the same directory.

This check reused the existing AI-generated narration and plans; it did not benchmark new LLM generation. Chapter edits are covered by tests, but a new 7–30 minute export was not rendered for this change. This milestone adds review and reusable concept animation; it does not guarantee factual accuracy or create arbitrary cinematic footage. Scenes whose concepts share a sentence cue use illustrative pacing, not word timestamps.
