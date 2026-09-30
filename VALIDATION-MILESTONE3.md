# VisualForge AI - Milestone 3 validation

Validated locally on Windows, 2026-09-26. All 26 milestone acceptance criteria passed for the allowed **What is Generative AI?** test topic. This is an integration milestone, not a guarantee of publication-ready writing or reliable generation for every topic.

The complete executed pipeline was topic -> local Transformers model -> validated content JSON -> local Kokoro WAVs -> measured durations -> existing Remotion timeline -> narrated MP4. No generated scene was manually rewritten. Milestones 1 and 2 remain available; Milestone 4 was not started.

## Final implementation report

| Item | Validated result |
| --- | --- |
| Primary model | Qwen/Qwen2.5-1.5B-Instruct |
| Parameters / license | Approximately 1.54B (1.5B model family), Apache-2.0 |
| Pinned revision | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| Python | 3.12.14 in backend/.venv; system Python 3.14.6 unchanged |
| Added direct Python packages | transformers 4.57.6; huggingface-hub 0.36.2; pydantic 2.12.5; torch 2.9.1+cpu |
| Device / precision | CPU only, float32, SDPA attention, two threads |
| Settings | Greedy decoding, temperature 0, seed 42, inference mode, KV cache, one model instance, no batching |
| Token ceilings | CLI maximum 1800; outline 1000; caption 180; narration 300; prompt limit 6000 |
| Retry limit | Three attempts per stage; errors accumulated, attempt number distinguishes correction prompts |
| Requested target | Two minutes; around eight scenes, accepting six to ten |
| Test topic | What is Generative AI? |
| Generated title | What is Generative AI? |
| Scenes / narration words | 6 / 213 (32-39 words per scene) |
| Generation wall time | 397.557s (6m 38s) |
| Model load / generation time | 47.036s / 349.310s |
| Generated tokens / attempts | 819; all 13 stages valid on their first attempt |
| JSON and Pydantic | Passed; content-only contract, IDs 1 through 6 |
| TTS | Six successful Kokoro v1.0 WAVs; kokoro-onnx 0.6.1; af_sarah, en-us, speed 1.0, seed 0 |
| Total measured narration | 89.880625s |
| Final frame count | 2789 |
| Video stream duration | 92.966667s |
| MP4 container duration | 92.976000s |
| Resolution / FPS | 1920 x 1080 / 30 |
| Codecs | H.264, yuv420p; MP3 audio, 192 kbps, 48 kHz |
| Backend tests | 26 passed |
| Renderer tests | 4 passed |
| TypeScript | tsc --noEmit passed with final generated data |
| Dependency compatibility | pip check passed after installation |
| Final MP4 | renderer/generated/generative-ai.mp4 |
| Remaining limitations | Small-model writing quality and topic-dependent failures; CPU latency; basic text-scene visuals; details below |

Model metadata: [official Qwen model card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct). Node.js 24.18.0, npm 12.0.2, React 19.2.0, and Remotion 4.0.529 were retained. Existing TTS dependencies remain pinned: SoundFile 0.14.0, NumPy 2.5.3, ONNX Runtime 1.30.0. Direct requirements and the complete dependency lock are both supplied.

## Local resource use and model storage

Hardware: Intel Core i3-1005G1, two physical cores / four logical processors, approximately 16 GB RAM. The successful model process was observed at 6,568,448,000 bytes working set and 9,600,462,848 bytes peak working set. Allow roughly 7 GB for inference and a temporary 10 GB loading peak. CPU generation and TTS/rendering run in separate processes sequentially.

The model checkpoint occupies 3,087,467,144 bytes in backend/.cache/qwen2.5-1.5b-instruct. Its SHA-256 was checked against the Hugging Face LFS value: `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`. The initial download took approximately 11m 41s on this connection. First installation/download requires internet; the successful generation used --offline. There were no hosted inference requests, API keys, paid APIs, or cloud inference.

An initial 0.5B trial was inadequate and its weights were removed; only the primary 1.5B model is retained. Quantization trials did not preserve quality on this Windows CPU build and were removed from the implementation. Model caches, temporary drafts, virtual environments, and Python caches are ignored by Git. Source data/video.json is not ignored. The workspace has no Git repository, so no commit was created.

## Content review and provenance

The generated outline progresses through introduction, mechanism, image-generation example, benefits, limitations, and takeaway. All scene fields are populated, headlines fit the renderer, bodies differ from narration, IDs are sequential, and no Markdown wrappers remain. This is a basic beginner overview: its mechanism explanation is shallow and some phrasing repeats, including an intentional summary of the opening definition. It should receive editorial review before publication. It does not claim that generated content is always correct or realistic.

The successful outline and each accepted caption/narration response were parsed from backend/.cache/last-generation, validated, and reassembled with the service's field mapping. The resulting object exactly matched data/video.json. Its SHA-256 matches data/video.generation-report.json:

`924a849fff1ce8944d4de6fb03ea4bc807e379644123f2d983e0c76fda636aa6`

This confirms that the rendered content came from the local model, without manual scene writing or post-generation rewriting. TTS consumed this same source directly; all metadata narration strings and WAV sample durations match it.

The service uses a validated outline followed by independent caption and narration drafts, reusing one model instance. The parser recovers only clearly complete objects or simple fences; it rejects truncation, duplicate keys, multiple objects, nonstandard constants, and invalid schemas. Schema failures never publish a partial storyboard. The LLM cannot set filenames, durations, frame counts, codecs, FPS, or resolution.

## Audio and timeline evidence

Active WAV directory: renderer/public/audio/34b9c746a0ec241f/. WAVs are mono PCM, measured at 24 kHz. Each scene uses ceil((WAV duration + 0.5 seconds) * 30) frames, with contiguous starts. The extra 3.086042 seconds are end padding and frame rounding; the target duration is guidance, not an enforced cutoff.

| Scene | WAV seconds | Start frame | Scene frames | Source correlation | Audio offset (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 15.582667 | 0 | 483 | 0.999972 | 0.000 |
| 2 | 15.336667 | 483 | 476 | 0.999970 | 0.000 |
| 3 | 16.019333 | 959 | 496 | 0.999973 | 0.333 |
| 4 | 16.660625 | 1455 | 515 | 0.999968 | 0.000 |
| 5 | 13.898667 | 1970 | 432 | 0.989199 | 0.333 |
| 6 | 12.382667 | 2402 | 387 | 0.988178 | 0.292 |

The existing media validator fully decoded the actual MP4 without errors, checked both streams and all dimensions/frame counts, and correlated every complete source WAV against decoded MP4 audio. Correlations range from 0.988178 to 0.999973, above the 0.98 threshold. Maximum start offset is 0.333333 ms, far below one 33.333 ms frame. All end-padding RMS values are zero. Source peaks are below full scale. No narration truncation or scene overlap was detected.

The inherited MP3-in-MP4 choice is retained because Milestone 2 measured a roughly 43 ms offset with its raw AAC encoding path. The MP4 container lasts 9.333 ms longer than the video stream because of audio packetization; frame timing remains correct.

Visual inspection of extracted MP4 frames at two seconds into every scene passed: all six titles and captions are readable, with no clipping or overflow. The long image-generation headline wraps cleanly. See [contact sheet](renderer/generated/generative-ai-contact-sheet.png) and [machine-readable media report](renderer/generated/media-validation.json). Full decode and audio correlation were performed; no claim of a separate human listening review is made.

## Executed validation

```powershell
backend/.venv/Scripts/python.exe backend/scripts/generate_script.py "What is Generative AI?" --offline --temperature 0
backend/.venv/Scripts/python.exe backend/scripts/generate_audio.py
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -q
cd renderer
npm.cmd test
npm.cmd run typecheck
npx.cmd remotion render VisualForgeVideo generated/generative-ai.mp4 --concurrency=2
cd ..
backend/.venv/Scripts/python.exe backend/scripts/validate_render.py renderer/generated/generative-ai.mp4
```

Tests mock the LLM and cover strict schemas, malformed JSON and recovery, invalid topics, retries and accumulated errors, distinct correction prompts, duplicate narration, output preflight, atomic source preservation after late failure, source compatibility, TTS batch failure/reruns, actual WAV durations, and contiguous audio-aware timelines. Real inference is separate from unit tests.

## Issues found and remaining limits

- RAG trials repeatedly produced unqualified accuracy claims, weak examples, or excessive narration. Earlier one-shot generation also produced incomplete JSON. These trials were not accepted as the final video. Prompt decomposition, independent field validation, concise prompts, bounded corrections, and greedy decoding improved results. The final integration uses the other topic explicitly allowed by the brief: Generative AI. A successful RAG video is not claimed.
- The narrow accuracy-language guard is a heuristic and may reject valid wording or miss false claims. Pydantic is structural validation, not fact checking. Arbitrary topics can still exhaust retries; the existing source is preserved on failure.
- Repeated greedy retries originally received identical prompts when the error repeated. Correction prompts now include the attempt number; a regression assertion checks this.
- The first render attempt timed out during Chromium's cold startup. An unchanged retry succeeded. The installed Remotion version fixes browser startup timeout at 25 seconds; no dependency files or renderer settings were patched.
- The final video is a working narrated text explainer using the preserved Milestone 2 layout and entrance animations. Automated diagrams, icons, rich slide layouts, and PowerPoint output were not part of this milestone and were not added.
- PowerPoint is a reasonable later alternative for editable slides, but it would not reduce local LLM memory or repair script quality. Its export performance has not been benchmarked on this laptop. Remotion remains the validated renderer.

## Files created

- backend/llm/__init__.py, local_llm.py, prompts.py
- backend/schemas/__init__.py, video_schema.py
- backend/services/__init__.py, json_parser.py, script_generator.py
- backend/scripts/generate_script.py
- backend/tests/test_script_generation.py
- data/video.generation-report.json
- data/milestone2.video.json and data/milestone2.video.generated.json (historical copies)
- renderer/VALIDATION-MILESTONE2.md and renderer/generated/media-validation-milestone2.json (historical copies)
- renderer/public/audio/34b9c746a0ec241f/scene-1.wav through scene-6.wav
- renderer/generated/generative-ai.mp4, generative-ai-contact-sheet.png, and generative-ai-scene-1.png through generative-ai-scene-6.png
- Local ignored model cache and raw inference diagnostics under backend/.cache/

## Files modified

- .gitignore: excludes local model cache and drafts
- backend/requirements.txt and backend/requirements.lock.txt: pinned local inference dependencies
- backend/scripts/generate_audio.py: preserves the optional topic in generated metadata
- data/video.json: automatically generated content source
- data/video.generated.json: measured audio metadata from the existing TTS pipeline
- renderer/generated/media-validation.json: final media measurements
- README.md, renderer/README.md, VALIDATION.md: workflow, environment, limits, and validation evidence

No renderer source or codec configuration changes were needed. The existing demo.mp4 and demo-with-voice.mp4 were preserved. Historical reports are renderer/VALIDATION.md (Milestone 1) and renderer/VALIDATION-MILESTONE2.md.

## Acceptance criteria

- [x] Local Hugging Face LLM integrated
- [x] No hosted inference API used
- [x] No paid API used
- [x] Model runs locally on CPU
- [x] User supplies a topic through the CLI
- [x] Topic produces a title
- [x] Topic produces multiple scenes
- [x] Every scene contains headline
- [x] Every scene contains body
- [x] Every scene contains narration
- [x] Output is valid JSON
- [x] Pydantic validates output
- [x] Scene IDs are sequential
- [x] Malformed responses are handled conservatively
- [x] Bounded retry logic exists
- [x] data/video.json generated automatically
- [x] Existing audio generator accepts generated JSON
- [x] WAV narration generated successfully
- [x] Remotion accepts generated metadata
- [x] Final narrated MP4 renders successfully
- [x] Final video uses LLM-generated content
- [x] Tests pass
- [x] TypeScript passes
- [x] Documentation updated
- [x] Validation report updated
- [x] Milestone 4 has not been started
