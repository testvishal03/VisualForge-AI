# Creator flow and topic visuals

Validated September 29, 2026. This update supersedes the seven-minute minimum described in VALIDATION-SCRIPT-REVIEW.md.

## Behavior

- Narration drives the duration. Short complete scripts are supported; long pasted scripts are split into chapters without trimming their narration. No minimum-duration padding or seven-minute render gate remains.
- Script review includes a scene-by-scene visual plan, source-linked sentence cues, continuity information, and repetition/fallback notes. Preview visuals renders a representative excerpt before a full export.
- Specialized demonstrations cover tokenization, context capacity, attention, autoregressive generation, embeddings, meaning-space geometry, dimensions, semantic retrieval, vector storage, and RAG. Existing authored/code/chart demonstrations retain priority. Unsupported passages retain existing visuals and receive review notes; this is not arbitrary animation synthesis for every subject.
- Measured narration beats drive demonstrations. Consecutive related scenes preserve assembled geometry and change focus instead of restarting the same build.
- Playlist suggestions stay on hold until the current verified export is explicitly marked finished. Revise this video reopens review. Content, theme, or export changes clear finished status. Marking finished does not publish to YouTube.
- Permanent deletion requires typing DELETE and a current revision. Project deletion removes that project's files and playlist reference; workspace deletion removes its project files and catalog entry. Shared model/audio caches are retained. Paths and junctions are checked before deletion.
- The main player comes before expandable script review. Advanced editing and deletion are under More options. Submit controls no longer overlap content.

## Verification

- Backend: 174 unittest tests passed (data/creator-flow-tests.log).
- Renderer: 20 tests passed; TypeScript typecheck passed.
- Frontend: node syntax checks passed for app.js and creator.js.
- Live Embeddings visual preview: 1280 x 720, 30 fps, 1,266 frames, 42.2 seconds. Full decode and narration/audio validation passed (data/editor/f8e998318a12/style-validation.json).
- Chrome inspection: preview player, script controls, duration explanation, and More options displayed; no browser console errors observed. Initial loading resolved after the active render completed.
- Deletion, acceptance, revision checks, chapter preservation, and reopening were tested with disposable fixtures. No existing user project was permanently deleted or marked finished.

## Practical limits

This validation covers an excerpt, not a newly rendered full-length episode. The existing full export remains available and is labeled as previous until regenerated. API request size is 2 MB and the script file picker accepts up to 1.5 MB. Scene sentence-format limits and hardware/rendering constraints remain; removal of the duration gate does not imply unlimited resources. Single-document script edits preserve existing paragraph/scene boundaries; structural edits use the advanced scene editor. AI draft scope choices remain separate from final measured duration.
