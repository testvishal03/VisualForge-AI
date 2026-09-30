# Playlist-guided script review

New videos created from the main creator use this sequence:

1. Choose a playlist or a single-video workspace. Playlist settings support an ordered topic list and an optional current topic. The Generative AI Visualized preset suggests Embeddings after Tokens and Context Windows. Existing episodes also advance the suggestion; this is not a YouTube publication status.
2. Prepare a script. Prompt-based lessons target at least ten minutes (up to the existing thirty-minute target), using the chapter generator. Pasted narration is preserved.
3. Review and edit the narration and visual plan. Explicitly select **Approve script & generate video**. Changes invalidate the existing document/chapter approval fingerprints.
4. Before rendering, measure the generated narration. Narration must exceed 420 seconds, excluding scene pauses and bookends. Short narration stops with an actionable explanation; it is never padded with silence.
5. Request an expanded draft if needed, review it, and approve again. Original pasted narration is retained in an archive before conversion to chapters. Chapter expansion uses the existing measured-duration adjustment worker.

Legacy projects retain their previous workflow. Advanced editor/manual projects can still be shorter. Single-document review editing preserves scene paragraph boundaries; structural edits belong in the scene editor. Generated drafts still need factual and editorial review, and estimates are not duration guarantees.

## Validation

- New regression suite: 10 tests passed, covering HTTP review settings, unchanged pasted narration, approval gates, short narration rejection before rendering, chapter preflight, minimum prompt target, playlist suggestions, input validation, and temporary Windows file locks.
- Existing automatic/chapter/workspace/storyboard suites: 38 tests passed.
- Full backend discovery: 164 tests at that point; two environment-sensitive failures (existing media access and child-process timeout) passed when rerun with the necessary access. Two further review tests were subsequently added and passed.
- Script-generation and review suites passed after the bounded Windows save-retry change.
- JavaScript syntax checks passed for app.js and creator.js.
- Chrome: created Generative AI Visualized with Tokens and Context Windows as current topic, verified Embeddings suggestion, and prepared the existing 1,436-word Embeddings script in project f8e998318a12. Preparation completed and stopped for explicit approval. No new video was rendered or published during this check.
- The first live preparation exposed a temporary Windows destination-file lock. Atomic JSON replacement now retries Windows errors 5/32/33 for up to one second, retaining the original until replacement succeeds. Live retry completed successfully.

The local server was restarted with these changes. A new full-length render and a fresh local-model prompt-to-script run were not performed during this milestone.
