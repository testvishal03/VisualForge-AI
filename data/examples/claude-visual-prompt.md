# Prompt for Claude: a script with a hand-designed visual for every scene

Copy everything below the line into Claude, replace `<TOPIC>` and the length, and paste Claude's whole
answer into **Paste a script** in VisualForge. The `visual` blocks are drawn and animated in sync with
the narration; they are never read aloud. See `tool-calling-visual.txt` in this folder for a full example.

---

Write a narration script for a YouTube explainer video about: <TOPIC>
Audience: beginners. Length: about <N> words (140 words is about 1 minute).

NARRATION RULES
- Plain text paragraphs, one teaching point each, 2–4 sentences, under 25 words per sentence.
- Separate paragraphs with a blank line. First paragraph introduces the topic; last is a short recap.
- Write words, not symbols: "for example" not "e.g.", "versus" not "vs.", "10 million" not "10M", no URLs.
- Do not say "in this video" or "we'll explore".

VISUAL RULES
After EVERY paragraph, add a fenced block that designs that scene's 2D animation:

```visual
{"elements": [ ... ]}
```

Design a different picture for every scene, the way a motion designer would: a fan-out of risks, a
pipeline, a cycle, a before/after, a chat exchange, a "BLOCKED" stamp, a packet travelling between
boxes. Never reuse the same arrangement twice in a row. Use short on-screen labels of 1–5 words that
summarise the idea (they do not have to quote the narration). Every element appears when its sentence
is spoken, so build the picture up step by step.

Canvas: 1920 x 1080 pixels, origin top-left. Keep everything between x 80–1840 and y 140–930
(the caption bar sits below y 950; the top 120 px hold the title tag).

Every element has:
- "type" (below), "at": the sentence number in this paragraph that reveals it (0 = first sentence),
- optional "delay": extra seconds after that sentence starts (use 0.2–1.5 to build in sequence),
- optional "word": reveal exactly when this word of that sentence is spoken,
- optional "id": a name other elements can point to,
- optional "out": {"at": sentence, "delay": seconds} to remove it later,
- optional "pulse": a sentence number at which it glows briefly.

Colours (by meaning): "yellow" = the AI model / main idea, "cyan" = input / user / data, "pink" =
output, "green" = good / safe / correct, "red" = risk / error / blocked, "muted" = neutral, plus
"purple", "orange", "white", "line" (dim grey).

Element types:
- box: {"x","y" (centre), "w","h" optional, "text", "sub" (small second line), "color", "fill": "panel"|"tint"|"solid"|"none", "icon": a concept word like "database", "calendar", "search"}
- arrow: {"from","to": an element id (connects edge to edge) or [x, y], "color", "curve": -300..300 for a bent arrow, "label", "dashed": true}
- mover: {"from","to": id or [x, y], "text" (a small packet label), "color", "dur": seconds to travel} — a message or data moving between things
- bubble: {"x","y" (top-left), "w", "text" (a quote or message), "color", "mono": true for code/JSON}
- pill: {"x","y", "text", "color"} — a solid rounded tag
- stamp: {"x","y", "text" like "BLOCKED" or "FLAGGED", "color"} — slams in
- check / cross: {"x","y", "r"} — a green tick or red cross
- text: {"x","y", "text", "size": "title"|"h2"|"body"|"small", "color", "align"}
- headline: {"text", "color"} — a heading centred at the top of the stage
- bracket: {"x1","x2","y", "label", "color"} — groups things above it
- ring: {"x","y","r", "text", "color"} — a circle outline
- bar: {"x","y" (top-left), "w","h", "color", "text"} — a filled block, for levels or ratings
- icon: {"x","y", "name": a concept word, "size", "color"}
- line: {"points": [[x,y], ...], "color", "dashed"}

Output only the script: paragraphs, each followed by its visual block. Valid JSON, double quotes,
escape quotes inside text as \".
