# Milestone 5 validation: local review studio

Implemented the local topic/draft review editor, editable and reorderable scenes, six visual layouts, single-scene model refinement, narration/exact-frame previews, and selective speech regeneration.

## Automated checks

- 53 Python tests passed, including 13 editor tests covering cache reuse, one-scene narration invalidation, reorder reuse, corrupted audio recovery, atomic failure behavior, optimistic revisions, layout validation, local HTTP access guards, range playback, new-topic draft persistence, cancellation, corrupted previews, and exclusive Windows server-port binding.
- Five renderer tests passed against actual WAV samples and metadata.
- TypeScript typecheck and browser JavaScript syntax check passed.
- Tests that read earlier WAV artifacts and stop child processes required execution outside the restricted shell sandbox. They passed with that access; no application workaround was used.

## Browser and real-engine verification

Editable project: `data/editor/0871a2d95d7c/`. Imported the previous milestone as a copy, edited the opening title, moved a scene down and back, and saved. Original run files were preserved. Narration playback was exercised in Chrome.

Initial preparation generated six local Kokoro WAV files in 63.141 seconds. The first local Qwen refinement exhausted three validation attempts; all scene content and the project revision were verified unchanged. A second broad request also exhausted validation. A concrete biography/date refinement succeeded in 72.551 seconds; the saved-document comparison confirmed only scene 5 changed. Its 20-word narration is model-generated, with no hand substitution. No automated editorial issues remain, although factual/editorial review is still required.

After refinement, preparing all narration generated scene 5 only and reused scenes 1, 2, 3, 4 and 6 in 17.352 seconds. The five reused WAVs have identical paths, SHA-256 hashes and modification times. Scene 5 changed from 13.899 to 8.649 seconds. Changing its layout from Explanation to Example regenerated zero WAVs and reused all six in 0.789 seconds.

An exact process-diagram frame rendered in 38.956 seconds using the cached scene 2 narration. Chrome displayed the rendered image correctly alongside the editable diagram labels. The project survived a server restart with its edits and speech intact.

Evidence files within the project folder: `regeneration-evidence.json`, `selective-audio-evidence.json`, `layout-audio-evidence.json`, `speech-before.json`, and `speech-reuse-verification.json`.

## Final media result

[Edited MP4](data/editor/0871a2d95d7c/video.mp4) | [Process preview](data/editor/0871a2d95d7c/preview-02a38c1c888f.png) | [Edited scene extracted from MP4](data/editor/0871a2d95d7c/edited-scene.png) | [Machine-readable validation](data/editor/0871a2d95d7c/media-validation.json)

- 1920 x 1080, 30 FPS, 2632 frames, 87.733333 seconds of video (container 87.744 seconds).
- H.264 video and MP3 audio at 48 kHz, preserving the previously validated audio alignment strategy.
- Full decode passed. Minimum source-to-MP4 narration correlation: 0.989398589; maximum absolute narration offset: 0.000333333 seconds, below one frame. Maximum end-padding RMS: 0.000001011.
- Render plus validation: 186.802 seconds, zero speech files generated and six reused. MP4 size: 4,194,685 bytes. SHA-256: `39fcaa4d675c3327069d683dbed0a50d944533a61f3d24ded70b5dea5aae6d93`.
- Repeated render reused the verified MP4 in 0.015 seconds with its hash and modification time unchanged.
- Chrome playback advanced past five seconds with readyState 4 and no media error, then was paused. Download control points to the checked video. The exact preview and extracted edited-scene frame were visually inspected; text and layout fit.
- Existing milestone videos and original source scripts remain intact. The updated editor is running at http://127.0.0.1:8765/.

## Implementation

- `backend/scripts/review_app.py`: localhost HTTP API, static editor, project import/create/save, task controls, and byte-range media serving.
- `backend/services/editor_store.py`: stable scene identifiers, validation, persisted documents, optimistic save revisions and preview fingerprints.
- `backend/services/editor_jobs.py`: one heavy task at a time, isolated subprocesses, cancellation, exact previews, validated final MP4 publication and artifact integrity checks.
- `backend/services/incremental_audio.py`: content/voice-keyed, hash-verified WAV cache independent of layout and scene order.
- `backend/scripts/regenerate_scene.py`: bounded single-scene Qwen refinement, preserving other scenes and original content on failure.
- `review/`: local HTML/CSS/JavaScript review workspace without a new package dependency.
- Existing audio CLI accepts opt-in `--incremental`; default milestone behavior is unchanged. The process runner accepts cancellation; renderer preview props preserve the original scene count.

## Limits

The local 1.5B model still needs editorial review and may exhaust bounded retries. Quality heuristics do not verify facts. Live layout sketches are approximate; exact previews use Remotion. A complete new-topic draft uses the existing generator; its editor lifecycle was tested with a deterministic model fixture, while actual local inference was exercised through scene refinement. Tasks do not automatically resume after closing the server; saved projects and verified audio persist. No PowerPoint engine, cloud service, database, or LangGraph dependency was added.

Previous measurements are preserved in [VALIDATION-MILESTONE4.md](VALIDATION-MILESTONE4.md) and [VALIDATION-MILESTONE3.md](VALIDATION-MILESTONE3.md).
