# Prompt for Claude: a script with a hand-designed visual for every scene

Copy everything below the line into Claude, replace `<TOPIC>` and the length, and paste Claude's whole
answer into **Paste a script** in VisualForge. The `visual` blocks are drawn and animated in sync with
the narration; they are never read aloud. See `tool-calling-visual.txt` in this folder for a full example.

Copying Claude's answer: the **Copy** button under the answer keeps the ```` ```visual ```` fences. Selecting
the text with the mouse drops them and leaves the word `visual` above each JSON block; VisualForge accepts
that form too, so either way works.

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

Data and machine-learning visuals (a "plot" gives other elements data coordinates):
- plot: {"id", "x","y" (centre), "w","h", "xRange": [low, high], "yRange": [low, high], "xLabel", "yLabel", "grid": true|false} — axes that draw themselves
- points: {"plot": plot id, "data": [[x, y], [x, y, classIndex], ...], "classes": ["cyan", "pink", ...], "r", "stagger": seconds between points} — a scatter plot; classIndex picks the colour
- curve: {"plot", "shape": {"type": "line", "slope", "intercept"} | {"type": "sigmoid", "k", "x0"} | {"type": "poly", "coefficients": [c0, c1, c2, ...]}, or "data": [[x, y], ...], "start": [[x, y], ...] (same number of points: the curve morphs from start to its final shape, e.g. a line rotating into the best fit), "dur", "color", "dashed"}
- dot: {"plot" (optional), "x","y" or "path": [[x, y], ...] (it travels along the path, e.g. gradient descent rolling down a loss curve), "label", "color", "dur"}
- segments: {"plot", "segments": [[x1, y1, x2, y2], ...], "color", "dashed"} — residual errors, distances to neighbours, guide lines
- region: {"plot", "polygon": [[x, y], ...], "color"} — a shaded area, e.g. one side of a decision boundary
- table: {"x","y" (top-left), "rows": [["", "Pred yes", "Pred no"], ["Actual yes", "40", "10"], ...], "header": true, "colWidth", "rowHeight", "highlight": [[row, column, "green"], ...]} — datasets, features and labels, confusion matrices; rows appear one by one
- network: {"x","y","w","h", "layers": [3, 4, 2], "labels": ["Input", "Hidden", "Output"]} — a neural network drawn layer by layer
- counter: {"x","y", "value": 92, "begin": 0, "prefix", "suffix": "%", "decimals", "size", "color"} — a number that counts up, for accuracy, loss or scores

Animation actions (any element; build scenes that MOVE, not only appear):
- "moveTo": {"at": sentence, "delay", "x", "y", "dur"} — slide an element to a new place later in the scene.
- "dim": {"at": sentence, "delay"} — fade an element into the background when focus moves on.
- "typing": true — a bubble or text types itself out (good for prompts, code and chat messages).
- Continuity: give an element the SAME "id" and type in the next scene and it stays on screen across the cut and
  glides to its new position (keep the main character of the story, e.g. "model", on screen between scenes).
- Camera (on the block, next to "elements"): "camera": [{"at": sentence, "delay", "x", "y", "zoom": 1.2-2, "dur"}]
  zooms into a detail (for example one row of a table) and {"zoom": 1} zooms back out. Use it at most once or twice
  per scene.

Use real, consistent numbers: if the narration says the model predicts 79, the plot and counter show 79.
Prefer these data visuals whenever the idea is about data, fitting, distance, probability or measuring a model.

PUBLISHING (YouTube title, description and tags)
After the last visual block, add ONE block that the app uses for publishing (it is never narrated):

```publish
{"titles": ["...", "...", "...", "...", "..."],
 "description": "...",
 "tags": ["...", "..."],
 "hashtags": ["...", "...", "..."]}
```

- titles: 5 high-click-through options, best first. 45–60 characters each. Put the main search keyword in the
  first 40 characters. Each uses one proven hook: a clear benefit ("…in 5 Minutes"), curiosity ("How … Really
  Works"), "Explained Visually", "for Beginners", a number, or a before/after. Title Case, at most one emoji-free
  bracket like (Visual Guide). Never misleading clickbait, never ALL CAPS, every title must match the video.
- description: 150–300 words. The first 2 lines (about 150 characters) are the hook and contain the main keyword,
  because only they show in search. Then "In this video you'll learn:" with 4–6 short bullet lines starting "- ",
  then one line about the playlist. Use 3–5 related keywords naturally (no keyword stuffing). No timestamps, links,
  or < > characters: the app adds chapter times measured from the finished video.
- tags: 15–25 tags, from specific to broad: the exact topic, long-tail search phrases ("what is machine learning
  for beginners"), related concepts, then broad ones ("machine learning", "artificial intelligence"). Under 500
  characters in total.
- hashtags: 3 hashtags without "#", most important first (YouTube shows the first three above the title).
- thumbnail: {"text": "2-4 punchy words", "highlight": "one of those words", "scene": number, "badge": "EPISODE 1"}.
  The words must COMPLEMENT the best title, not repeat it (title "What Is Machine Learning? Explained Visually",
  thumbnail "HOW MACHINES LEARN"); at most 28 characters. "scene" is the scene whose finished visual is the
  most striking and readable when small (a plot, a before/after, a big stamp), shown beside the words.
  "badge" is optional, e.g. the episode number.

Output only the script: paragraphs, each followed by its visual block, then the publish block. Valid JSON, double quotes,
escape quotes inside text as \".
