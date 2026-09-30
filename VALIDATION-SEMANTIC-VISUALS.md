# Topic-aware visual planning

The local model now selects diagram forms and source-grounded labels for each scene. The implementation is shared across topics, prompt input, pasted scripts, and chapter scripts; no LLM-topic-specific renderer was added.

Supported forms are processes, relationships, system components, comparisons, cycles, timelines, and simpler explanations or examples. Existing numeric-chart extraction preserves literal percentages. The model chooses from short source phrases through constrained JSON generation. Backend validation checks label grounding, sentence references, element counts, known icons, and distinct labels. Measured speech boundaries control reveals; continuous diagram motion does not alter audio scheduling.

Invalid decisions retry at most three times, then record an explicit fallback in the plan and log. Valid plans are cached. Runtime/model failures stop the stage rather than publishing a partially updated plan. Source labels do not prove that the chosen relationship or the narration is factually correct; editorial review remains necessary.

New short videos plan visuals automatically before audio/rendering. New chapter scripts plan visuals before they are published to the chapter editor. Existing chapter scripts have a **Plan visuals from script** action; it preserves narration and scene IDs, and clears export approval. Individual short-video scenes can use the visual replan action.

## Live test

Project `474d674d5a29` was created through the studio API using a prompt about how large language models work, with a 30-second draft target. The local Qwen3 model generated tokenization, attention, and a recipe-input example. The test exposed and corrected an overly narrow example check, invalid one-node diagram decisions, paraphrased labels failing grounding checks, and “training” incorrectly matching the rain icon.

The final visual-plan evidence is stored in `data/editor/474d674d5a29/visual-plan.json`; raw attempts and validated cache entries are in its `visual-plan-cache` directory. All three final decisions validated without fallback: process, relationship, process. Script text was not manually replaced during this test. The refined plan was saved through the studio API and the draft-render job resumed.

The completed draft is **29.43 seconds**, 1280×720 at 30 fps. Full decode, frame counts, and all three narration alignment checks passed. The resumed audio/render/validation job took 86.308 seconds. Evidence: `data/editor/474d674d5a29/draft-validation.json`. Rendered frames from every scene were inspected for readable labels and layout; the video was opened in Chrome. This is a short demonstration of the shared planner, not a complete long-form lesson on language models.

## Regression checks

- 99 backend tests passed (18.257 seconds), including source-label grounding, cache reuse, script/scene-ID preservation, chapter review invalidation, explicit fallback, and false-positive quality/icon fixes.
- TypeScript check and eight renderer tests passed.
- Generic plans explicitly suppress the earlier topic-keyword environment override, so the chosen diagram remains authoritative.

This is local AI selection and composition of supported educational graphics, not unrestricted text-to-video footage generation. Content outside the available visual vocabulary can still need manual refinement.
