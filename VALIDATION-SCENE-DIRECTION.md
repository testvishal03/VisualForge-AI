# Scene direction and style previews

Implemented 2026-09-27.

## Behavior

- Local AI selects a compatible composition along with its source-grounded concept labels. Bounded decoding, validation, retries, and fallback remain in place. No new paid service or model is required.
- Six reusable compositions: pipeline demonstration, branching relationships, system layers, comparison, timeline, and detail view. Existing motion choices control entrance and emphasis where supported; detail view has its own focus animation.
- Shared labels preserve the preceding icon in a transition marker. Continuity requires matching labels and only spans scenes within the same rendered chapter/video.
- Review warnings flag repetitive compositions, dense text, and estimated static stretches. They do not establish factual correctness or measure audience engagement.
- Style previews select complete consecutive scenes, prefer varied compositions, and enforce a 60-second cap using measured audio plus frame-rounded padding. They do not grant approval or overwrite a full draft/final video. Longer individual scenes must be split first.

## Checks

- Renderer TypeScript check and 11 tests passed, including composition compatibility, shared-object identity, and unchanged audio scheduling.
- All 109 backend tests passed. Checks cover preview selection and duration limits, artifact isolation/invalidation, chapter routing without full-export approval, and semantic composition compatibility.
- Inspected rendered frames for branching, close-up, layers, comparison, and timeline layouts. Synthetic layout QA props and frames are in `renderer/generated/scene-direction-qa`; these are visual fixtures, not fact-checked lessons.
- The existing LLM demonstration project `6d0eb387ed2a` is used for a real narrated style preview. Narration is reused from its cache. New AI generation throughput and a new 7–30 minute export were not benchmarked for this milestone.
- Final preview was launched using the Chrome studio button and completed in 45.243 seconds. Output `data/editor/6d0eb387ed2a/style.mp4`: 1280x720, 30 fps, 883 frames, 29.433 seconds (the complete short script). Full decode passed; source-audio correlation exceeded 0.99996 and measured offsets were at most 0.334 milliseconds. The media URL returned HTTP 200, approval remained false, and full exports were untouched. See `style-validation.json` beside the MP4.
