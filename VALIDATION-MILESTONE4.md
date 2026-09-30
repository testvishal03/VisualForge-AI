# VisualForge AI - Milestone 4 validation

Completed locally on Windows, 2026-09-26. All five requested improvements are implemented and tested. The result is a complete checked video with one explicitly reported editorial warning; automated checks do not establish factual accuracy.

[Final video](data/runs/what-is-generative-ai-6523818ccc/video.mp4) | [Six-scene visual preview](data/runs/what-is-generative-ai-6523818ccc/preview.png) | [Run manifest](data/runs/what-is-generative-ai-6523818ccc/run.json) | [Resume evidence](data/runs/what-is-generative-ai-6523818ccc/resume-evidence.json)

## Acceptance results

| Requested improvement | Implementation and evidence |
| --- | --- |
| One pipeline command | generate_video.py runs script -> quality -> audio -> visuals -> props -> render -> validate; the real local-model run completed all seven stages |
| Resume failed work | Atomic run manifest, output SHA-256 checks, input/settings/code fingerprints, exclusive run lock, and per-field script checkpoints; actual stop-after-audio/resume reused script, quality, and WAVs |
| Better script quality control | Strict schema and accuracy-language guard retained; repeated explanations and weak examples produce targeted errors; promotional wording, long narration, and shallow mechanisms produce review warnings; bounded per-field retries |
| Reusable visual layouts | Title/explanation, three-step process, side-by-side comparison, example, and takeaway layouts; all six kinds appear in the inspected MP4 |
| Laptop-friendly execution | Separate sequential processes, CPU defaults of two threads, render concurrency capped at two, stage logs, elapsed times, Python peak working-set measurements, timeout and interrupt cleanup |

No PowerPoint integration, dashboard, LangGraph, hosted inference, cloud service, new model, external visual assets, or additional Python/npm dependency was added.

## Real end-to-end run

Executed from the project root:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/generate_video.py "What is Generative AI?" --offline --stop-after audio
backend/.venv/Scripts/python.exe backend/scripts/generate_video.py "What is Generative AI?" --offline
```

The first invocation generated a fresh script with the actual cached local model, checked it, generated six WAVs, and deliberately stopped after audio. The next invocation verified and reused those completed stages, generated the visual plan, rendered the MP4, and ran media validation automatically. No generated narration or process labels were manually rewritten.

| Result | Measurement |
| --- | --- |
| Topic / title | What is Generative AI? |
| Local model | Qwen/Qwen2.5-1.5B-Instruct, approximately 1.54B parameters, Apache-2.0 |
| Model revision | 989aa7980e4cf806f80c7fef2b1adb7bc71aa306 |
| Model settings | CPU float32, two threads, greedy decoding, temperature 0, seed 42 |
| Script | Six scenes, 213 narration words; all 13 outline/field requests valid on first attempts |
| Visual plan | Process labels valid on first attempt; no fallback warnings |
| TTS | Local Kokoro v1.0, af_sarah, en-us, speed 1.0, seed 0 |
| Narration duration | 89.880625s |
| Final frames | 2789 |
| Video stream duration | 92.966667s |
| Container duration | 92.976000s |
| Dimensions / FPS | 1920 x 1080 / 30 |
| Codecs | H.264 / MP3, 48 kHz audio; existing codec configuration retained |
| File size | 4,471,376 bytes |
| Run status | complete_with_review |

The source SHA-256 is `924a849fff1ce8944d4de6fb03ea4bc807e379644123f2d983e0c76fda636aa6`. It matches the earlier independently validated Milestone 3 script under the same greedy settings. This run invoked the model afresh, rather than importing that file. The run's script log, generation report, and validated field drafts provide local evidence. The original global data/video.json and data/video.generated.json remain unchanged.

## Resource and duration measurements

Machine: Intel Core i3-1005G1, two physical cores / four logical processors, approximately 16 GB RAM. Python 3.12.14, Transformers 4.57.6, PyTorch 2.9.1+cpu, and Remotion 4.0.529 remain unchanged.

| Stage | Elapsed seconds | Peak Python working set (bytes) |
| --- | ---: | ---: |
| script | 414.844 | 9600942080 |
| quality | 0.109 | Not measured |
| audio | 75.390 | 821252096 |
| visuals | 53.359 | 9282785280 |
| props | 0.016 | Not measured |
| render | 350.297 | Not measured |
| validate | 16.375 | 178966528 |

The heavy stages total roughly 15 minutes for this cold end-to-end workload, excluding the deliberate pause and development activity. The model processes exited before the next stage ran. Script peak RAM was approximately 9.60 GB; TTS peak was approximately 0.82 GB. These are process peak working sets, not total system memory. Renderer subprocess-tree memory is not measured; the report does not imply otherwise. No GPU was required.

## Resume verification

After completion, the same command was run again with the final implementation. All **seven** stages were reused, with **zero** stage executions. External wall time was **0.750 seconds**. SHA-256 hashes and modification timestamps for all **13** recorded artifacts were unchanged, including the source, six WAVs, props, MP4, and media report. The assertion results and snapshots are in resume-evidence.json.

A completed stage is trusted only when its fingerprint matches and each recorded output still exists with the expected content hash. Missing/modified artifacts trigger regeneration. A dependent stage can still be reused if regenerated upstream data is byte-identical. Changes to relevant renderer code, props, audio, or render concurrency invalidate rendering. Changing quality rules rechecks content. A newly invalid cached field is regenerated instead of accepted silently.

The automated tests separately exercise a KeyboardInterrupt during a later stage, recovery without redoing the earlier stage, corrupt JSON draft recovery, artifact tampering, changed settings, missing outputs, exclusive locking, bounded retries, and a timed-out real subprocess that was terminated before it could write a delayed marker. The real video test used an intentional saved checkpoint; no claim is made that the OS was forcibly crashed during rendering.

## Quality result

The quality report contains one warning: scene 5 uses promotional wording ("amazing"). The CLI clearly prints **NEEDS REVIEW**, and run.json records complete_with_review. No structural or blocking quality errors remained. The service does not silently rewrite imported scripts: imported content with hard errors stops for correction.

The model-generated process diagram reads:

1. Train on original data
2. Mimic original data's style
3. Generate new content

These labels are supported by the existing explanation and are suitable for this basic overview. They remain a simplified description, not a technical account of model training or inference. Comparison captions are copied from the model-generated benefits and limitations scenes. Visual planning changes neither narration nor timing.

The content remains a basic beginner overview with some repeated phrasing. Language heuristics can miss false claims or flag valid wording, and successful JSON/schema checks cannot guarantee factual correctness. Review content and diagram meaning before publication. Earlier RAG-generation limitations are documented in [Milestone 3's preserved report](VALIDATION-MILESTONE3.md).

## Audio and visual verification

| Scene | WAV seconds | Start frame | Scene frames | Source audio correlation |
| --- | ---: | ---: | ---: | ---: |
| 1 | 15.582667 | 0 | 483 | 0.999972 |
| 2 | 15.336667 | 483 | 476 | 0.999970 |
| 3 | 16.019333 | 959 | 496 | 0.999973 |
| 4 | 16.660625 | 1455 | 515 | 0.999968 |
| 5 | 13.898667 | 1970 | 432 | 0.989199 |
| 6 | 12.382667 | 2402 | 387 | 0.988178 |

The final validator used this run's exact props, not the global demo metadata. Full MP4 decoding passed. Every full narration matched its source WAV; minimum correlation was 0.988178, above the 0.98 threshold. Maximum start offset was 0.333333 ms, well below one 33.333 ms frame. End-padding RMS was zero for every scene. No truncation or narration overlap was detected.

Actual MP4 frames at two seconds into each scene were extracted and inspected. Titles, process labels, comparison captions, icons, and footers fit without clipping. The six-scene contact sheet is linked above. The new visual layouts preserve the previous audio-aware timeline; legacy scenes without a visual field still render through TextScene. The first real render attempt in this run succeeded.

## Tests

- **40 backend tests passed**: existing schema/parser/audio tests plus recovery, quality, visual planning, CLI preflight, worker metrics, timeout cleanup, artifact corruption, and locking.
- **5 renderer tests passed**: existing timing/WAV checks plus all visual kinds, valid item counts, and malformed visual rejection.
- **TypeScript passed**: npm.cmd run typecheck / tsc --noEmit.
- **Real integration passed**: local model -> six WAVs -> visual plan -> MP4 -> full media checks.
- **Real cached rerun passed**: seven stages reused, no recorded artifact rewritten.
- **Visual inspection passed**: all six final scenes.

## Files and compatibility

Created:

- backend/scripts/generate_video.py: one-command orchestration and CLI
- backend/scripts/generate_visuals.py: local visual-plan generation
- backend/scripts/stage_worker.py: isolated Python stage and resource metrics
- backend/services/run_state.py: durable verified stage reuse and locking
- backend/services/process_runner.py: logged subprocess execution, timeouts, cleanup
- backend/services/quality.py: targeted errors and editorial review report
- backend/services/visuals.py: deterministic layout selection and validated process labels
- backend/tests/test_milestone4.py: recovery, quality, worker, and CLI tests
- renderer/src/components/VisualScene.tsx: reusable layouts and local SVG icons
- VALIDATION-MILESTONE3.md: historical report preserved
- data/runs/what-is-generative-ai-6523818ccc/: source, reports, props, drafts, logs, MP4, extracted frames, and resume evidence

Modified:

- backend/services/script_generator.py and backend/scripts/generate_script.py: field checkpoints and targeted editorial checks
- backend/scripts/validate_render.py and renderer/scripts/timeline.ts: run-specific metadata and report paths, with old defaults retained
- renderer/src/Video.tsx, types.ts, and timeline.ts: optional validated visual plans
- renderer/tests/timeline.test.ts: layout contract and timing checks
- .gitignore: generated run folders excluded
- README.md, renderer/README.md, VALIDATION.md: current workflow, behavior, limits, and measurements

Milestone 1-3 videos and source artifacts were preserved. The existing standalone script/audio/render commands still work. Run folders are local, ignored build artifacts. No commit was made because the workspace has no Git repository.
