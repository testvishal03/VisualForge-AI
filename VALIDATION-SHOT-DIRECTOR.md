# Narration-timed shot director

The illustrated-story renderer now plans one camera view per narrated sentence and binds each view to measured speech timings. Focus can follow a source-grounded object, while the stage camera stays within bounds so edge objects and labels remain visible. The studio exposes a per-sentence view selector and a continuous preview of consecutive scenes (up to two minutes). Changing a view invalidates the preview without changing narration or storyboard approval.

Validation: 192 backend tests, 23 renderer tests, and TypeScript typecheck passed. The local Tokens and Context Windows project was used for a real five-scene, consecutive preview with generated/reused Kokoro narration, Remotion scene rendering, and full-media validation. Its original script remains revision 3 and unapproved.

The shot director currently applies to illustrated choreography scenes. Existing worked examples and other renderer layouts retain their specialized animation. This is a preview and editorial control, not an automatic guarantee that every topic receives a unique illustration; factual and visual review remains necessary before publishing.
