# Narration-driven visual demonstrations

The renderer now selects an explanatory mechanism from each scene's narration before falling back to generic cards. This selection also applies to existing saved scripts on their next render.

Supported mechanisms in this change:

- Meaning space: points gather into schematic clusters. Source-mentioned example groups share labels; coordinates are explicitly illustrative.
- Encoding: text moves through an embedding model into vector coordinates, without inventing model outputs.
- Dimensions: a two-dimensional projection is contrasted with multiple coordinates.
- Retrieval: a query expands its search and retrieves ranked schematic matches.
- RAG: source passages move into context, then through an LLM into an answer.

Animation progression spans relevant measured narration sentences. Consecutive scenes of the same mechanism omit the scene-wide transition; dimensions use a small zoom, encoding/RAG a directional reveal, and other changes a fade. This is not an object-tracking or generative-animation engine. The same mechanism can recur when the narration explains it again.

Authored measured examples, executable examples, code, charts, statistics, weather diagrams and neural-network diagrams take priority. Unsupported concepts retain existing visual fallbacks. This milestone does not provide a unique animation for every conceivable subject.

The existing 32-scene Embeddings export selects five new mechanisms for 23 scenes: meaning space 5, encoding 9, dimensions 2, retrieval 5, and RAG 2. The other 9 use existing visuals.

Validation:

- TypeScript typecheck passed.
- All 19 renderer tests passed, including narration-based selection, measured timing, protected visual types, source example grouping, and transitions.
- Review artifact: `renderer/generated/semantic-motion-review.mp4`; five complete existing narration scenes, 89 seconds, 720p. Original narration and scene durations are preserved.
- Full decode passed; all five narration segments correlate above 0.99996 with source audio, with offsets no larger than 0.000334 seconds. Five extracted frames were inspected: diagrams, labels, and subtitles fit without overlapping.
- Local server restarted to refresh the renderer fingerprint. Previously exported full videos remain available as previous exports; generating an updated video applies these visuals.
