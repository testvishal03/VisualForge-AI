# Illustrated story preview

Validated September 30, 2026.

The renderer now draws original SVG characters, topic-related objects, and narrated connections on a light explainer stage. Sequence, workspace, relationship, and comparison layouts vary their geometry. Existing sentence-cited choreography supplies the labels and animation times; the renderer does not add unsaid numeric facts. The local visual planner can compile exact, cited labels for other topics as well. Its dedicated code, chart, and authored example renderers remain available.

The isolated preview copies scenes 2, 3, 7, and 8 from the existing Tokens and Context Windows project. It does not edit or approve the source project. The excerpt covers text entering the model, token pieces, the context window, and the assembled request. It uses Kokoro narration and the normal Remotion draft pipeline.

The final assembled export runs for 81.133333 seconds (2,434 frames at 30 fps, 1280 × 720). Full decoding passed, and each of the four narration tracks has a measured codec offset of zero seconds. Visual inspection of the assembled sequence and context-window frames found no label, character, heading, or footer overlap. Final evidence is in `data/illustrated-story-preview/result.json`, and the MP4 path is recorded there.

Validation commands:

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests
cd renderer
npm.cmd test
npm.cmd run typecheck
```

Results: 189 backend tests, 21 renderer tests, and TypeScript typecheck passed. A real renderer pass also exercised clip decoding, cached scene assembly, final media validation, and measured speech alignment. Visual inspection caught icon-label, character-object, and context-heading overlaps; these were corrected before the final preview.

This preview demonstrates a controlled explainer grammar. The drawings are local editable vectors, so it does not create arbitrary photographic or cinematic scenes. Factual and aesthetic review remains necessary for each finished episode.
