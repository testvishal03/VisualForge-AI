# Verified Python and SQL examples

Implemented September 28, 2026.

## Supported examples

- Python variable assignment and update, an `if`/`else` condition, and a loop that accumulates a total.
- SQL `WHERE amount >= threshold` and `INNER JOIN` between customers and orders.
- Optional scene controls select a template, two to five integer values, a threshold, and the starting narration sentence. Inputs can be copied from the preceding scene. SQL templates share the same customer/order dataset.
- Relevant generic narration selects examples automatically. Numeric examples, explicit code/operators, unsupported comparison wording, and other join types are left to the existing visual path. Examples can be explicitly disabled.

Python runs only internally defined fixed templates with bounded integer substitutions and restricted built-ins. Checkpoints capture actual variable states and printed output. No arbitrary user/model code is accepted. SQL runs fixed SELECT statements against a private in-memory SQLite database.

The renderer independently checks expected variable states, outputs, SQL rows, displayed code, and timing. Execution animations begin at the chosen measured sentence boundary; intermediate operation timing is explicitly illustrative, not measured execution time. Existing teaching plans identify computed Python/SQL examples, and existing scene preview/export paths render them.

Inputs survive narration edits and visual replanning. Explicit numeric output and SQL row-count contradictions block export; these are bounded checks, not complete semantic verification of arbitrary narration.

## Verification

- Full backend suite: 155 tests passed before adding the workflow regression.
- Focused example suite: 7 tests passed, including scene preview injection, narration preservation, and authored input persistence.
- Focused example/automatic/storyboard tests: 20 passed before adding that workflow regression.
- Renderer: 18 tests passed, including corrupt code, trace, and result rejection. TypeScript and storyboard JavaScript syntax checks passed.
- Five-scene narrated review: `renderer/generated/code-demo.mp4`; source, measured narration, props, extracted frames, and final validation report are retained alongside it.
- Final sample is 35.8 seconds, 720p, 1,074 frames. Full decoding passed; narration correlations exceed 0.99996 with codec offsets of at most 0.000333 seconds.
- Inspected the accumulated Python total (45), filtered SQL row (order 2, amount 25), and joined rows with customer names. Content fits without covering captions.
- Live API exposes demonstration settings for saved scenes, and the existing full video remains playable through its previous-export URL.

## Limits

This is a controlled example system, not a general Python execution environment or SQL query editor. Functions, recursion, arbitrary tables, GROUP BY, and other joins remain future work. No new complete long-video export was generated for this milestone. The optional editor controls were syntax checked; a live browser interaction walkthrough was not performed.
