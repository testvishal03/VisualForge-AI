# Structured teaching plans and technical demonstrations

Implemented September 28, 2026.

## Scope

First release of the reusable teaching system: embeddings, vector similarity, and RAG. Other playlist topics continue using existing visual planners. No model downloads or paid services were added.

Each rendered scene with measured speech beats receives a validated teaching plan: question, objective, source-linked actions, final source sentence as takeaway, evidence type, and measured reveal times. A fingerprinted `teaching-plan.json` is saved beside project artifacts. The editor exposes a read-only plan for saved scenes. Editing narration recomputes the plan on the next render; source narration is never rewritten by this service.

The initial planner is conservative and rule-based, derived from narration rather than titles. It falls back to ordinary visuals when evidence is insufficient. It does not claim to perform general semantic or factual verification.

## Visuals

- Embeddings: illustrative two-dimensional vectors, with a clear distinction from actual model embeddings.
- Vector search: a fixed toy query and three vectors. Cosine scores are computed from the displayed coordinates and independently validated by the renderer. This release does not query a vector database or run an embedding model.
- RAG: source retrieval, context, and answer-generation stages, revealed using measured sentence cues. Labels are extracted from narration. No fabricated documents, quotations, or generated answer text is shown.
- Authored charts, code, statistics, and measured tokenizer examples retain their own renderers.

Backend planning logic participates in the render cache version. Existing exports remain available through the previous-export feature.

## Verification

- 149 backend tests passed; the five teaching-plan tests passed again after improving RAG labels.
- 17 renderer tests passed, including rejection of incorrect cosine scores, invented labels, and mismatched timing.
- TypeScript and storyboard JavaScript syntax checks passed.
- Prepared and rendered a three-scene narrated review using local Kokoro speech: `renderer/generated/teaching-demo.mp4`.
- Inspected frames of embeddings, ranked cosine scores, and the RAG flow. Final media validation is recorded in `renderer/generated/teaching-demo-validation.json`.
- Final sample: 41.73 seconds, 720p, 1,252 frames. Full decode passed; all narration correlations exceed 0.99996 and codec offsets are at most 0.000333 seconds. Updated RAG labels were visually inspected.
- Live API exposes the saved project's teaching plans; the previous full export still streams successfully with HTTP 206.

## Remaining milestones

Code execution and SQL/table demonstrations, playlist knowledge continuity, and specialized components for the remaining playlists are future work. This release does not automatically rebuild previously saved projects or claim a complete long-video quality review.
