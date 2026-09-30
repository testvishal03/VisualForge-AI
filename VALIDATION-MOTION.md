# Motion treatment — September 27, 2026

The renderer now uses a less boxed visual treatment, larger illustrations, animated diagram icons, scene-dependent composition, narration captions, and overlapping visual wipes. Audio starts and timeline duration remain unchanged; only the preceding visual stays visible during the incoming wipe.

Water-related teaching scenes can select five deterministic SVG environments: evaporation, condensation/clouds, rainfall, ground water movement, and plant water transport. These are a bounded illustration library, not arbitrary generated footage. Other subjects retain diagrams, comparisons, charts, and icon treatments. Charts are never replaced by environmental illustrations, and cloud-computing references alone do not select weather graphics.

## Verified preview

- File: `renderer/generated/motion-review/preview.mp4`
- Metadata: `renderer/generated/motion-review/props.json`
- Report: `renderer/generated/motion-review/validation.json`
- 50.80 seconds, 1280×720, 30 fps, H.264 with MP3 narration.
- Three existing narration scenes: evaporation, rainfall, and plants. Script content was not rewritten for this style test.
- Full decode passed. Source-audio offsets: 0 ms, 0 ms, and 0.333 ms.
- Inspected rendered frames for all three compositions.
- TypeScript check and eight renderer tests passed.

The studio was restarted while idle to refresh its renderer fingerprint. Existing video files remain on disk; the studio requires a new export to apply the changed renderer. The original full water-cycle export was 452.93 seconds at 1920×1080 and passed all 28 scene audio checks. That full export has not yet been regenerated with this motion treatment. Thirty-minute exports remain untested.
