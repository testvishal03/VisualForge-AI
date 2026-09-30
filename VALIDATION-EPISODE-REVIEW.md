# Episode review and incremental rendering

Validated September 30, 2026.

## Delivered

- Episode timeline with scene narration, visual forms, timing, thumbnails after rendering, and scene playback or preview generation. Unrecorded timings are explicitly estimates.
- Local-model visual revisions for worked examples, simpler diagrams, and comparisons. Revisions render in an isolated candidate project; the user can accept or discard them without rewriting narration.
- Shared, already-visible objects carry between compatible directed scenes, moving into their next positions.
- Editorial review notes flag repeated compositions, dense text, static passages, and limited visual operations alongside existing quality checks.
- Frame-range scene caching, verified clip hashes, streamed audio assembly, and final export validation. Transition neighbors are dependencies; timing changes can invalidate later ranges. Renderer and output-profile changes invalidate the cache.
- Thumbnail failures leave the previously published video intact. Stale or modified candidates cannot be accepted.

## Verification

- 188 backend tests passed; 21 renderer tests passed.
- TypeScript typecheck and JavaScript syntax checks passed.
- Chrome review screen inspected after server restart; no browser errors reported.
- Actual local Qwen visual revision completed for scene 7, "The context window", in Tokens and Context Windows (project `8ac669012aac`). The rendered candidate is available in Review your episode. The original project remains at revision 2, with script approval pending; the candidate has not been accepted.

## Laptop benchmark

The isolated benchmark used four existing Tokens preview scenes: 1, 4, 11, and 25. Output was 2,363 frames at 30 fps, 1280 x 720, lasting 78.766667 seconds.

| Run | Rendered segments | Reused segments | Render/assembly time |
| --- | --- | --- | --- |
| First | 4 | 0 | 164.73 seconds |
| Fully cached | 0 | 4 | 2.12 seconds |

These times exclude the separate final validation pass. Both outputs passed full decoding and narration alignment checks; measured audio offsets were zero for all four scenes. This is a short preview benchmark, not a full-episode performance estimate. Additional per-clip decoding validation was added afterward; the final regression suite covers the updated code.

Raw evidence: `data/scene-cache-benchmark.json`. Reproduction script: `backend/scripts/benchmark_scene_cache.py`.

## Remaining user review

Review the proposed replacement and accept it or keep the current visual. The full Tokens episode still requires script approval before rendering. Editorial notes help review pacing and source alignment; they do not guarantee factual correctness or visual appeal. Existing thumbnails are generated on the next current render rather than fabricated for unrendered scenes.
