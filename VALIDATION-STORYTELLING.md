# Script grouping and topic visuals

Implemented September 28, 2026.

## Behavior

- Pasted scripts are grouped at sentence boundaries using a bounded optimization. It favors approximately 42 words, respects substantial authored paragraph breaks, and avoids separating question/setup lines from their explanation when possible. Existing 15-60 word and 600-character scene limits remain enforced.
- Narration wording and order are preserved. The saved Tokens and context windows source produces 33 scenes instead of 76, with no blocking quality issues.
- Both directors recognize source-supported text -> tokens -> token ID explanations and context inventories. Diagrams never add unmentioned categories or numeric capacities.
- Context inventories use a persistent container, progressively revealed at measured sentence boundaries. Up to four selected categories appear, explicitly labeled illustrative; band sizes do not claim measured token usage.
- Existing measured-tokenizer demonstrations remain available and can be selected automatically when the grouped scene contains an explicit input.
- Previous full exports remain accessible with a distinct Previous Export label after renderer updates or document changes. Their hash and path are checked, and they do not count as current exports for rendering/cache decisions.

## Verification

- 144 backend tests passed, including source preservation, substantial paragraph boundaries, topic grounding, long-script planning persistence, and previous-export corruption rejection.
- 16 renderer tests passed, including equal sentence cue handling; TypeScript and creator JavaScript syntax checks passed.
- Rendered `renderer/generated/storytelling-preview.mp4`: 35.83 seconds, 1280x720, 30fps, 1,075 frames.
- Full decode passed. Audio correlations exceeded 0.99996; measured codec offsets were 0 and -0.000333 seconds.
- Visually inspected extracted token and context frames. Labels fit and captions remain separate.
- Verified the preserved existing full-video endpoint responds with HTTP 206 to a byte-range request.

## Scope

Grouping applies to newly imported scripts. Existing saved storyboards are not regrouped automatically, protecting edits and scene references. Other topics retain the existing semantic and extractive visual planners; the new specialized diagrams currently cover token processing and context contents. No complete new 10-minute export was generated in this milestone. The preview is a separate two-scene review artifact, not a replacement for the user's existing video.
