# Lesson quality improvements

Implemented September 28, 2026.

- Short-video narration receives the entire validated teaching outline and the preceding accepted explanation. The generation report retains the teaching plan.
- Chapter narration receives the chapter teaching sequence and preceding explanation, including during duration adjustment.
- Both semantic and fallback directors repair obvious cut-off labels using phrases from the assigned narration sentence. Semantic decoding excludes dangling endings and allows longer complete phrases.
- Repeated compatible diagram compositions switch to a detail view without changing the conceptual relationship or narration.
- Explicitly quoted tokenizer inputs can automatically use the existing measured local-model example renderer. Numeric token-count claims and ambiguous inputs are excluded. Automatic continuation demonstrations are intentionally excluded because a script's claimed output may differ from the model.
- Explanation and takeaway cards reveal bounded supporting sentences at measured narration boundaries. Main captions remain visible.
- Quality review detects incomplete labels, narration-label mismatches, repeated layouts, and unsupported chart/statistic values. Export no longer bypasses blocking errors after storyboard approval.

## Verification

- 138 backend unit/integration tests passed outside the Windows sandbox, which restricts existing WAV files and process termination.
- 21 focused chapter/lesson tests passed after the chapter-context change.
- Renderer TypeScript check passed; all 15 renderer tests passed.
- Rendered and visually inspected `renderer/generated/lesson-quality-review.png`, using repaired evaporation labels with existing measured audio.
- Rendered and visually inspected `renderer/generated/lesson-card-review.png`, a takeaway-card fixture using existing measured audio. Text fits within the card and captions remain clear.

## Limits

No new complete 7-30 minute export or real-model script-generation benchmark was run for this change. Existing project documents and exported videos are not migrated automatically; new generation/replanning uses the improved directors. Label and factual-support checks are bounded heuristics, not general grammatical or factual verification. Automatic measured examples currently cover tokenizer inputs only. Sentence support cards display only short sentences (at most 180 characters), keeping longer narration in the existing synchronized captions.
