# D3 visual director: Tokens and Context Windows

Implemented September 29, 2026.

## Pipeline

The local visual planner now accepts scene-specific revision instructions and selects a bounded build, focus, or comparison treatment. A compiler converts source phrases and sentence references into validated objects and reveal, focus, connection, and removal actions. Model output is data, never executable code.

D3 point scales and link paths compute SVG geometry. Remotion remains the animation clock and video renderer. Every action carries the measured start/end of its narration sentence; objects cannot appear before their introduction. These are sentence-level cues, not claimed word-level forced alignment. Relationships and removals require corresponding narration language. Context diagrams are illustrative; the separate worked example displays actual local tokenizer pieces and IDs.

The renderer includes sequence, workspace, comparison, connection, intro, outro, and numerical-budget layouts with subject-specific glyphs. Numerical budgets require a source-grounded total equal to the sum of two positive parts. Existing authored code, chart, and measured tokenizer demonstrations retain priority. Existing semantic-motion continuity remains available; this does not synthesize arbitrary new animations for every subject.

## Creator controls

- Each scene in Script & visual plan has a Change this visual request field. It uses the local model and preserves narration; unsaved script edits must be saved first.
- Visual plans show object labels and their sentence-timed actions. Quality checks account for active demonstrations instead of incorrectly treating them as static cards.
- New workspaces enable the existing branded intro and outro by default. Existing workspace preferences are retained. Narrated intro/outro scenes replace duplicate silent brand screens at those boundaries.
- Preview selection includes narrated bookends and representative complete scenes, up to two minutes. The UI explicitly identifies this as excerpts that may skip between sections.
- Duration estimates use consistent rounding. Dependency-lockfile changes invalidate renderer cache entries; fixtures without a lockfile remain supported.

## Review lesson

Created a separate workspace, **Tokens and Context Windows - Visual director**, project `8ac669012aac`. Existing episodes were not replaced or deleted.

The script has 25 scenes and 1,206 whitespace-counted words, approximately eight to nine minutes before measuring the complete narration. It includes a spoken welcome and hook, tokenizer-specific pieces and IDs, context allocation, a toy 1,000-token budget, truncation policy, context versus model weights, summaries, retrieval, generation, recap, and a spoken outro.

The review preview contains complete scenes 1, 4, 11, and 25: intro, real tokenizer example, illustrative budget, and outro. The first validated preview is 78.766667 seconds, 2,363 frames, 1280 x 720 at 30 fps. Full decode and narration/audio validation passed. Extracted intro and budget frames were visually inspected for clipping, labels, and matching captions. Final cache-consistent preview is validated through the same pipeline.

The complete episode remains at script review. No approval was recorded on the user's behalf and no full episode or YouTube upload was performed. Use **Approve & render video** after reviewing the script and preview.

## Checks

- 181 backend tests passed: `data/choreography-all-tests.log`.
- 21 renderer tests passed, including cue timing, label grounding, and existing real-WAV validation.
- TypeScript typecheck and frontend JavaScript syntax checks passed.
- Added tests for unsupported connections, early actions, altered source labels, numerical budgets, narrated bookends, and complete-scene preview selection.
- Browser inspection showed the new lesson and review workflow during preview generation. The browser connection became unavailable for the last reload; final data and media were checked through the local API and render reports.

## References

- D3 point scales: https://d3js.org/d3-scale/point
- D3 link geometry: https://d3js.org/d3-shape/link
- Model text generation background: https://huggingface.co/docs/transformers/main/en/llm_tutorial
