# Worked-example validation

Implemented September 27, 2026.

## Measured local integration

- Installed Qwen3-4B-Instruct-2507-Q4_K_M.gguf, llama.cpp b11206, CPU-only worker.
- Exact input `The cat sat on the` produced five token IDs: 785, 8251, 7578, 389, 279. Pieces reconstruct the original UTF-8 input byte for byte.
- A bounded raw completion returned 12 generated IDs. Each displayed prefix was decoded from those actual IDs; final prefix equals the returned completion. This is a text completion, not a chat response or a factuality claim.
- Results: `renderer/generated/worked-results.json`; owned inference cache: `data/worked-example-cache/`.
- API contract reference: https://github.com/ggml-org/llama.cpp/tree/master/tools/server (tokenize, completion, detokenize).

## Render and UI

- New review project `f5dff12d7ae3`: **Worked example review - Real model tokens**.
- `data/editor/f5dff12d7ae3/draft.mp4`: 669 frames at 30 fps, 22.3 seconds, 720p, two narrated scenes, all four action types.
- Kokoro narration sentence timing drives action starts. Same input and token identities carry across both scenes.
- Media validation passed: full decode, audio alignment, complete source narration, scene padding. Report: `data/editor/f5dff12d7ae3/draft-validation.json`.
- Inspected token-ID, schematic-processing, and continuation frames under `renderer/generated/worked-review/`: no overlaps in the review example; captions and model attribution readable.
- Chrome studio verified editable input/label/action/cue controls, measured result summary, rendered draft link, and successful **Prepare example** execution from the UI.

## Automated coverage

- Backend unit coverage includes strict authored specs, cue ordering, UTF-8 pieces, trace matching, cache/model invalidation, no measured fields in editable documents, numeric token-count contradictions, scene-local preparation, preservation on narration edit, measured renderer props, and chapter task routing without approval changes.
- Renderer coverage rejects missing/mismatched measurements and invalid cues, and verifies action selection against measured beat starts. Existing audio/timeline checks remain intact.
- TypeScript and browser-script syntax checks pass. See final task report for test totals.

## Limits

- Opt-in LLM example engine, not an automatic demonstration generator for every subject.
- Maximum 80 input characters and 24 tokenizer tokens; up to four ordered sentence actions. Generation requests 12 tokens, so continuations can end mid-sentence.
- Diagram is a schematic; it does not show actual weights or activations. Intra-action speed is illustrative, not measured inference latency.
- Numeric contradiction and unsupported-probability checks are bounded heuristics, not comprehensive fact verification.
- Real integration exercised a short two-scene draft. Chapter dispatch is unit-tested; no new 7-30 minute export was run for this milestone.
