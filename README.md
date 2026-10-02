# VisualForge AI

Turn a topic, a script, or a Markdown page into a narrated, animated explainer video, entirely on your own computer. A local language model plans the visuals, a local Kokoro voice reads the narration, and Remotion renders the MP4 with word-synced captions and animations. No cloud services or paid APIs are used.

## Quick start

```powershell
cd "D:\Personal Project\VisualForge AI"
backend\.venv\Scripts\python.exe backend\scripts\review_app.py
```

Open **http://127.0.0.1:8765/**, click **New video**, then either describe an idea or use **Paste a script**. You can paste plain narration, notes, a Markdown page, or a production script with **Voiceover** sections; Markdown is converted to narration automatically. After rendering, the result screen offers the video, a thumbnail and a YouTube description. Try `data/examples/generative-ai-explained.txt` to see every explainer animation.

First-time setup (Python 3.12 environment, model downloads, `npm install`) is described under *Windows setup* below.

## Word-synced narration, transitions and publishing

- **Word-level sync.** Kokoro's own phoneme durations give every spoken word a start and end time; no extra model is used. Captions highlight the spoken word, and diagram objects, arrows and motion start on the word that names them (0.15 s early). Sentences whose words cannot be matched exactly are marked `estimated` rather than guessed.
- **Transitions.** Scenes exit inside their silent end padding, then the next one enters over a solid background, so two scenes' text is never superimposed. Objects shared by consecutive scenes stay on screen and glide into place. Named-again objects pulse on their word; objects float gently and the stage slowly pushes in.
- **Topic guide.** A "Topic 2 / 4" rail shows progress through the lesson, and an "Up next" card previews the next topic before each cut. Set `style.topicMap: false` to turn it off.
- **Intros and outros.** New workspaces open with the title and an "In this video" topic list (3 s) and close with a "What you learned" recap, sign-off and, for series, the next playlist topic (5 s). Toggle both under **Workspace settings**.
- **Voices.** Choose from ten local English Kokoro voices under **Workspace settings** and use **Listen** to hear a sample. New workspaces use Heart, the highest-rated Kokoro voice; existing workspaces keep their current voice, so recorded narration stays valid. Narration is AI-generated, and the description says so.
- **Thumbnail and description.** After an export passes validation, the studio renders a 1280×720 thumbnail from the lesson's own concepts and writes a YouTube description. The description has chapter times taken from the measured video; they are included only when they meet YouTube's rules of three or more chapters, each at least 10 s. Copy or download both from the result screen. If this step fails, the verified video is still kept.
- **Explanation scenes are illustrated.** Generic explanation and example scenes, which used to be text cards, now draw the concepts their own headline, caption and narration name. Each label is quoted verbatim from the sentence that introduces it, and verbs, adverbs and filler words are filtered out. Every sentence gets a visual cue: a new concept, a highlight on what the sentence mentions, or a camera close-up on the object it is still about. Arrows follow reading order ("converts X into Y" draws X → Y). Negated relationships ("we cannot send…") draw no arrow. Items travel along each arrow and take the shape of their destination: token chips, pages or dots. If a plan cannot be fully grounded, the scene keeps its previous card or diagram.
- **The local model checks labels.** The visual planner (Qwen3-4B, local) picks diagram labels only from noun phrases or short actions found in their own sentence, never sentence fragments like "Now let's see how…". Picks are constrained during generation and validated afterwards. For explanation scenes it also chooses the 2–5 concepts to show. Near-duplicates ("chunk" and "chunks") are rejected. A nearly valid answer is salvaged instead of spending another attempt, and scenes whose picks fail fall back to the rule-based extractor. On six sample scenes, planning took 5m15s on a 4-core CPU, and one scene fell back.
- **Explainer animations.** Narration that explains a familiar idea gets a dedicated animation, timed to its words:
  - **Next token:** prompt words appear as token chips, the likely next pieces rise as bars (labelled illustrative), one joins the sentence, and the loop repeats.
  - **Noise → image:** static resolves into the named shape (heart, star, sun…), with a step counter.
  - **Judge vs. create:** an item drops into the bins the narration names; the other side draws something new.
  - **Learning steps:** numbered "Feed it / Find patterns / Prompt it" cards.
  - **Limitations:** cards for wrong answers, bias and fact-checking.
  - **Tokenization:** a sentence from the narration splits into the local model's real tokens, and then their real token IDs appear.
  - **Embedding map:** concepts appear as they are named. Their positions are measured with a small local embedding model (bge-small-en-v1.5, 37 MB, installed by `setup_gguf.py`): a 2D projection of the real vectors, with each concept joined to its nearest neighbour and labelled with the cosine similarity. Without that model the map falls back to an illustrative layout that groups the concepts the narration calls close, and says so on screen.
  - **Retrieval:** question, embedding, vector search, closest chunks, language model and answer light up in order, but only the stages the narration names.

  Title and takeaway cards keep their own design. Try `data/examples/generative-ai-explained.txt` and `data/examples/embeddings-and-rag.txt` with **Paste a script**.
- **Notes to narration.** In **Paste a script**, paste notes or a Markdown page and click **Convert notes to narration**. The page title becomes the video title, and each `##` section becomes a scene. Bullets become sentences, numbered steps are read as "First / Next / Finally", and bare example lines are read as quoted examples, which the explainers can use. Emoji, arrows and Markdown marks are removed so the voice does not read them out. Your wording is kept, and the result stays editable before you generate. A blank line after any paragraph of 15 or more words now always starts a new scene.
- **Script check.** While you type in **Paste a script**, a check shows the scene count, narration length, the animations each scene will get, and how long generating should take on this computer. It warns about text the voice reads wrongly (web addresses, arrows, "e.g.", "vs.", "#1", "$5", "10M", slashes, stage directions, speaker labels, and acronyms read as words, such as "or ANN." spoken as "an"), plus long, repeated or unquoted sentences. Mechanical problems have an **Apply** button, or **Apply all fixes**; anything that depends on meaning is left to you.
- **AI visuals for long scripts.** Scripts with more than 16 scenes would need about 40 seconds of AI planning per scene, so only the scenes whose rule-based labels are weakest (a lone verb such as "built", vague phrases such as "smarter trick") are planned, worst first, within five minutes. An AI plan replaces the rule-based visual only when its labels score clearer.
- **Background music (optional).** Workspace settings can add a quiet generated music bed that dips about 24 dB under the narration. It is off by default, and the render check still verifies every scene's narration.
- **Faster renders.** Each render receives only the narration it uses, instead of Remotion copying the whole shared audio cache on every call, and narration synthesis uses up to four CPU threads. Both changes produce bit-identical output.

## Illustrated story scenes

Source-grounded scene plans can now render as open, light illustrated boards. Narration introduces locally drawn SVG people, objects, and connections at the measured sentence cues. A bounded planner selects layouts for spoken sequences, system parts, relationships, comparisons, and context-window examples across topics. Unsupported claims or missing exact labels retain their existing scene treatment. Authored token, chart, code, and numeric demonstrations keep their specialized renderers.

The isolated Tokens and Context Windows preview uses scenes 2, 3, 7, and 8 from the existing script. Recreate it without altering the saved episode:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/preview_illustrated_story.py
```

This is an original vector illustration system, rather than a copy of reference video artwork.

## Quantized local model

The studio supports **Qwen3-4B-Instruct-2507 Q4_K_M** through a project-local llama.cpp CPU server. Install and activate the pinned model once:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/setup_gguf.py
```

This downloads the 2.5 GB GGUF plus the Windows x64 CPU runtime, verifies both SHA-256 checksums, then writes `backend/models/local-model.json`. It uses Hugging Face's `hf-xet` helper when installed; `--http` selects resumable HTTP blocks as an alternative. Interrupted downloads retain their partial files. Allow roughly 6 GB of free space during installation. No cloud inference or system-wide installation is used. Model weights are from [Unsloth's quantization](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF); runtime binaries are from [llama.cpp](https://github.com/ggml-org/llama.cpp/releases/tag/b11206).

After installation, new studio jobs automatically use this profile, including individual scene regeneration. The studio header shows the configured model after reloading. Settings are two CPU threads, a 4,096-token context, no GPU offload, and one request at a time. The private inference server binds only to loopback with a per-worker random API key. The worker starts lazily and stops after script generation or failure, before narration and video rendering. Cancellation stops the stage's process tree.

Outline, caption, and narration requests use JSON schemas; existing content and duration checks still apply. Saved field checkpoints and command-line pipeline runs distinguish models, quantization, and runtime versions. Model changes do not rewrite existing storyboards or invalidate their recorded audio. Facts still need review; structured JSON does not establish factual accuracy.

For a deliberate rollback in PowerShell, set `$env:VISUALFORGE_LLM='transformers'` before starting the studio or a CLI job. Remove that environment variable to use the saved GGUF configuration again. The old Qwen2.5 model remains cached. GGUF inference never downloads weights automatically; a missing installation produces an error instead of silently switching models.


## Milestone 7: visual storytelling and workspaces

Start the studio with `backend/.venv/Scripts/python.exe backend/scripts/review_app.py`, then open **http://127.0.0.1:8765/**.

1. Choose **New workspace** for one video or a series / local playlist. Set its name, audience, channel label, and Ocean, Forest, or Sunset theme. Narration uses the existing local English Kokoro Sarah voice.
2. Choose **New video**, select the workspace, and enter a prompt or narration script. **720p draft** is the default first export; 1080p is also available directly.
3. Review the draft, edit individual scenes or use **Replan visuals for this scene**, and export the final 1080p MP4. Draft and final files are separate and both undergo decoding and audio-sync validation.

Workspaces support renaming, settings changes, duplication, episode reordering, and recoverable Trash/restore. Existing projects are adopted into single-video workspaces without changing their documents. Duplicates copy saved storyboards and reuse shared narration when possible; rendered files are not copied. Theme or brand changes invalidate previews and exports without changing narration. Audience changes guide newly generated scripts. Series are local organizational groups, not synchronized YouTube playlists. No upload is performed.

The director now has twelve scene types and seventeen SVG icons. It recognizes explicit sequences, contrasts, relationships, repeating cycles, dated timelines, system parts, and percentage data. A complete narrated water cycle gets a landscape illustration with evaporation arrows, cloud formation, rainfall, and collection flow. General diagrams offer alternate compositions; neighboring repeated layouts alternate their composition. Arrows draw and labels reveal at measured sentence boundaries. Charts require explicit percentages in the narration and never invent numerical data. Water-cycle illustrations, repeating cycles, charts, and comparisons currently use one composition each.

This is a bounded, evidence-based visual grammar, not arbitrary image or animation generation. Unsupported concepts fall back to simpler explanation or example cards. Pasted narration is preserved. Charts and diagrams still require editorial review for meaning and factual accuracy.

Prompt generation now requests an exact scene count, allocates a word budget per scene from the requested duration, and retries invalid fields. Overlong narration gets at most one duration rewrite; if the model still misses the budget, the shortest structurally valid draft is retained for review and cached. Invalid structure or blocking content checks still stop generation. The editor reports estimated runtime before speech and measured runtime after speech; a discrepancy beyond 15% or five seconds is flagged. A word budget cannot guarantee exact spoken duration. Authored scripts are never shortened automatically.

Heavy tasks remain sequential with cancellation and resumable speech/output caches. The 720p profile reduces output pixels, but model and speech generation take the same time. The final prompt-only test still failed on an overlong scene despite improved outline and duration handling; its validated field checkpoints were preserved. Use a reviewed written script for dependable generation with the current small model.

## Milestone 6: automatic visual director

Open **http://127.0.0.1:8765/** and choose **New video**. Select **A prompt or idea** (the local Qwen model writes the script), or **My written script** (your spoken narration is preserved). Click **Generate video** once. Scene planning, local Kokoro narration, measured visual timing, Remotion rendering, and MP4 validation run automatically. The resulting storyboard remains editable.

```powershell
backend/.venv/Scripts/python.exe backend/scripts/review_app.py
```

For pasted English scripts, use 30-720 words across 2-16 teaching paragraphs, each 15-60 words. The video title is optional and can be inferred from your narration. Omit stage directions and headings. Long paragraphs split at sentence boundaries; short ones join a neighbor when they fit. Invalid or oversized input is rejected rather than silently truncated. Prompts support approximate 30-second, one-, two-, or three-minute targets; actual duration follows the generated speech and can exceed the target. A tested prompt-only run took about 14 minutes on this laptop. AI-written content still needs factual review.

The director uses an extractive template planner with seven layouts and nine local SVG icons. Explicit **First / Next / Finally** steps become process cards; contrasts become comparisons; phrases such as **depends on** or **leads to** become connected relationship diagrams. Examples, openings, explanations and takeaways use matching cards. Labels come from the narration. Unsupported structures use a simpler layout, so this release does not invent arbitrary illustrations or diagrams.

Kokoro synthesizes each sentence separately; the system concatenates the WAV samples with 120 ms pauses and records exact sentence start/end times. Diagram elements reveal at their referenced sentence, the active point is highlighted, and the currently spoken sentence appears below. Scenes fade between explanations without overlapping narration. Timing is at sentence level, not word-level forced alignment. Splitting speech this way can slightly change prosody compared with an uninterrupted paragraph.

Narration edits replan only that automatic scene and regenerate its speech. Layout edits and reordering reuse verified sentence audio. Old projects retain their original paragraph narration mode. Interrupted automatic jobs keep the saved storyboard and completed speech; retry the generation or render the saved draft. Existing editor tabs retain unsaved fields across server restarts and can save once the active task finishes.


## Milestone 5: local review studio

Start the editor from the project root:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/review_app.py
```

Open **http://127.0.0.1:8765/**. Create a video or open an editable copy of an existing run. Review quality notes, edit scene titles, explanations and narration, reorder scenes, and select title, explanation, process, comparison, example or takeaway layouts. Process and comparison layouts require three and two editable labels respectively. Save changes before switching projects; task buttons save pending edits automatically.

Use **Regenerate this scene** to refine one scene with the local Qwen model. Other scenes stay unchanged; the selected scene resets to the Explanation layout because its previous diagram labels may no longer match. Give concrete requests, such as "Explain an invented date in an AI-generated biography and checking it against a reliable reference." Generation remains bounded and may fail validation; saved text is preserved on failure. Quality checks are editorial heuristics, not factual verification.

**Generate scene audio** prepares one narration; **Prepare all narration** reuses verified WAVs and generates only missing or changed speech. Titles, layouts and scene order do not invalidate speech. The live layout sketch updates immediately. **Render exact frame** produces a real Remotion frame with the saved layout. **Render video** calculates timing from the current WAV durations, renders, validates the MP4, and then exposes playback and download controls. Edits hide stale previews and final video links until regenerated.

Projects and stage logs persist under `data/editor/<project-id>/`. Shared speech is cached by narration and voice settings under `renderer/public/audio/`. Source runs remain untouched. One heavy task runs at a time; cancellation stops its subprocess tree while preserving saved edits and verified outputs. Restarting the server preserves projects, but an interrupted task must be started again. The editor binds only to localhost and has no cloud service, account or database dependency. Existing environment/model setup below still applies.


## Milestone 4: one-command generation

The six-scene video is 92.967 seconds; a fully cached rerun reused all seven stages in 0.750 seconds. One editorial wording warning remains clearly flagged.

From the project root, run:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/generate_video.py "What is Generative AI?" --offline
```

Omit `--offline` for the first model download. The command runs seven stages sequentially: **script, quality, audio, visuals, props, render, validate**. It prints progress and the final MP4 path. Each video has an isolated folder under `data/runs/<topic>-<settings-hash>/`; the earlier `data/video.json`, metadata, and milestone MP4s remain available.

### Recovery and reuse

Run the same command again after a failure or interruption. A completed stage is reused only when its input/settings/code fingerprint and every recorded output hash match. Changed or missing outputs are regenerated; downstream stages are reconsidered using their actual inputs. A rendering failure does not regenerate valid script or WAV files. Rendering gets at most two attempts to recover from a transient Chromium startup failure.

Script generation also saves validated outline/caption/narration drafts. A late script failure can reuse earlier valid fields on the next invocation. Reused fields are validated again; a corrupt or no-longer-valid draft is regenerated. These checkpoints are an optimization, not a replacement for validation.

```powershell
# Save a deliberate checkpoint, then resume without the stop option:
backend/.venv/Scripts/python.exe backend/scripts/generate_video.py "What is Generative AI?" --offline --stop-after audio
backend/.venv/Scripts/python.exe backend/scripts/generate_video.py "What is Generative AI?" --offline

# Use an existing script; its topic must match:
backend/.venv/Scripts/python.exe backend/scripts/generate_video.py "What is Generative AI?" --script data/video.json --offline
```

Options include `--minutes 2`, `--threads 2`, `--concurrency 1` or `2`, `--run-dir PATH`, `--stage-timeout 3600`, and `--force`. `--force` regenerates all stages without field reuse. To change narration manually, supply the edited file with `--script`; do not edit generated run outputs and expect the cache to trust them. Only one command can own a particular run folder at a time. Different runs are not globally serialized; run one video at a time on a modest laptop.

### Quality and visuals

Structural errors, repeated explanations, and examples lacking concrete cues trigger targeted narration retries during generation. Excessive length, promotional language, and shallow mechanism explanations are reported in `quality.json`. An exhausted hard error stops the pipeline; editorial warnings allow a checked video with a conspicuous **NEEDS REVIEW** result. These are language heuristics, not web research or factual verification. Imported scripts with hard errors stop for correction rather than being silently rewritten.

The renderer supports title/explanation cards, three-step process diagrams, side-by-side benefits/limitations, examples, and takeaways. Layout choice is deterministic. Comparisons reuse the existing benefits and limitations captions; process labels are concise summaries generated by the same local Qwen model in a separate process, with three bounded attempts. If labels fail schema validation, the original explanation layout is used and a warning is recorded. Process meaning still needs editorial review. Content, WAVs, and timing remain separate from visual planning.

The visual system uses consistent typography, built-in SVG icons, staggered entrances, and a scene progress indicator. It requires no external images, fonts, icon services, or paid APIs. Scenes without a visual plan retain the earlier text layout. Audio timing and codecs are unchanged.

### Outputs and laptop behavior

Each run contains `video.json`, `video.generated.json`, `quality.json`, `visuals.json`, `props.json`, `video.mp4`, `media-validation.json`, `run.json`, and stage logs. Model-generated field drafts live in the run's `drafts/` folder. These run artifacts are ignored by Git; source code and milestone reports are not.

Heavy stages execute in separate processes, one at a time, so the LLM exits before TTS or rendering. CPU threads default to two and rendering concurrency is capped at two. Logs capture failures; Python stage metrics record elapsed time and the process peak working set. Renderer subprocess-tree memory is not measured and is explicitly labeled as such. A timed-out or interrupted stage terminates its own process tree and leaves completed checkpoints intact.

The final validator uses the exact run-specific props and actual WAV files. It checks full decoding, resolution/FPS/frame count, source-to-MP4 audio correlation, start alignment, and silent end padding. A successful render alone does not mark the run complete.

Preview a saved run in Remotion with its `props.json`, or open its MP4. Earlier standalone Milestone 3 commands below still work. PowerPoint, LangGraph, cloud hosting, and a dashboard are not part of this milestone.

## Milestone 3


Generate an educational storyboard from a topic using a small local Hugging Face model, then run the existing narration and rendering pipeline:

```text
Topic
  -> Local Qwen instruction model (Transformers, CPU)
  -> Pydantic-validated storyboard: data/video.json
  -> Local Kokoro TTS
  -> WAV files + measured durations: data/video.generated.json
  -> Dynamic Remotion timeline
  -> Narrated 1080p MP4
```

### Local model and first download

The single primary model is [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct): approximately 1.54 billion parameters (marketed as 1.5B), Apache-2.0 license, pinned revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Model files are downloaded from Hugging Face, but **all inference runs locally**. No hosted inference API, token, paid service, or account is required.

The first run needs internet and downloads approximately 3.1 GB of model weights/tokenizer files into `backend/.cache/` (ignored by Git). Package installation also requires internet. After caching, use `--offline` to prohibit model downloads. The implementation already loads complete cached weights without contacting the Hub on later normal runs.

CPU-only PyTorch is pinned; CUDA is not required or selected. The model uses float32 for broad CPU compatibility, inference mode, one model instance per CLI process, no batching, two threads by default, and bounded input/output tokens. On this Windows laptop, allow roughly 7 GB RAM for inference and a temporary loading peak near 10 GB; 16 GB system RAM is recommended, with other memory-heavy apps closed. Expect several minutes for generation. The process exits before Kokoro or Remotion runs, releasing its memory. Quantization trials did not preserve output quality on this CPU build and are not part of the final implementation.

### Setup and full workflow

See the Windows environment setup below if `backend/.venv` does not exist. From the project root:

```powershell
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt

# Topic -> content JSON (the first run downloads the model)
backend/.venv/Scripts/python.exe backend/scripts/generate_script.py `
  "What is Generative AI?" --minutes 2

# Content JSON -> local narration WAVs + actual durations
backend/.venv/Scripts/python.exe backend/scripts/generate_audio.py

cd renderer
npm.cmd run dev
# In another terminal, from renderer:
npx.cmd remotion render VisualForgeVideo generated/generative-ai.mp4

# From the project root, after rendering:
cd ..
backend/.venv/Scripts/python.exe backend/scripts/validate_render.py renderer/generated/generative-ai.mp4
```

With the virtual environment activated, plain `python backend/scripts/generate_script.py "Your topic"` works too. In PowerShell, `.cmd` avoids blocked npm/npx script shims without changing execution policy.

Useful generation options:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/generate_script.py `
  "What is Generative AI?" `
  --minutes 2 --output data/video.json --offline `
  --threads 2 --max-new-tokens 1800 --temperature 0 --attempts 3
```

Duration is guidance, not a promise: the default aims for eight scenes and accepts 6–10, with around 25–45 narrated words per scene. `--minutes` accepts 0.5–4 minutes, with an overall range of 3–12 scenes. Kokoro's actual WAV lengths determine the final video length. The default temperature is zero (greedy decoding), with seed 42. A positive temperature enables sampling. Seed 42, pinned weights and settings improve repeatability, but bit-for-bit LLM output is not guaranteed across hardware/framework versions.

The validated example is **What is Generative AI?**, one of the brief's allowed test topics. RAG trials exposed factual-claim and instruction-following limitations in the small model; they did not produce an approved video. Passing the schema is not a guarantee that arbitrary topics will succeed.

### Content contract and error handling

`data/video.json` is the content source of truth: `title`, the original normalized `topic`, and sequential scene IDs with `headline`, `body`, and `narration`. The LLM cannot supply audio paths, durations, frame counts, FPS, or rendering configuration. These extra fields are rejected, not trusted.

Pydantic enforces required fields, strict integers, nonempty strings, short on-screen text, bounded narration, sequential IDs starting at 1, and distinct scene headlines/narration. A narrow language check rejects unqualified accuracy guarantees while allowing negated limitations; it is not a factual-verification system. The parser accepts valid JSON, a simple surrounding code fence, or one clearly recoverable complete object with prose around it. It rejects truncation, duplicate keys, multiple objects, nonstandard constants, and invalid schemas; it never invents missing text.

The service first asks the model for a compact outline (`title`, `topic`, sequential scene IDs, headlines, and teaching points). It validates that plan, then asks the same loaded model for each caption and narration independently. IDs and headlines remain fixed from the validated model-generated outline. All headlines, bodies, and narration come from model responses; deterministic code only validates and assembles them. RAG-related topics receive brief factual reference guidance distinguishing retrieval from training and explaining the role of retrieved context. Other topics receive general factual-writing guidance. It does not contain handwritten demo scenes. Each field prompt contains its current teaching point; narration also receives the validated caption, without earlier narration that could encourage copying. A text-similarity check rejects near-duplicate narration.

Validation failures trigger a fresh correction prompt containing the specific errors, without echoing the invalid text. Correction prompts retain accumulated errors and include the attempt number so repeated failures do not produce identical greedy-decoding prompts. At most three attempts run per stage, with one model instance for the whole command. The outline uses at most 1,000 new tokens and each caption at most 180 and narration at most 300; `--max-new-tokens` can lower those ceilings. This keeps each response focused and makes retries target the failing scene. Invalid topics and output paths fail before expensive loading. Failed parsing or validation, even in a later scene, leaves the previous `video.json` intact. Only a fully validated storyboard is written atomically. A sibling `video.generation-report.json` records settings, per-stage attempts/timing, total generated tokens, and the output hash. The CLI prints progress and a concise summary.

The CLI also saves raw responses as `backend/.cache/last-generation/outline-attempt-N.txt` and `scene-ID-body-attempt-N.txt` / `scene-ID-narration-attempt-N.txt` for diagnosing invalid output. These local diagnostic files are ignored by Git and are not consumed by TTS. One-shot full-storyboard generation was replaced after it produced short narration, missing scenes, and factual confusion during real validation.

For a missing model/tokenizer in offline mode, run once online to cache it. Download failures explain the first-run network/disk requirement. Memory errors suggest closing memory-heavy applications or reducing the token limit. The small model can still produce factual errors: inspect generated content before publishing, especially for unfamiliar topics. Schema validation checks structure, not factual truth.

### Tests and milestone scope

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v
backend/.venv/Scripts/python.exe -m pip check
cd renderer
npm.cmd run typecheck
npm.cmd test
```

Unit tests mock the LLM; they do not download or repeatedly execute model weights.

Milestone 2 source/metadata are preserved as `data/milestone2.video.json` and `data/milestone2.video.generated.json`, with its report at `renderer/VALIDATION-MILESTONE2.md`. To render that older metadata without replacing the current source, wrap it in a `videoData` props object and use Remotion's `--props` option.

There is no LangChain, LangGraph, dashboard, FastAPI, database, web research pipeline, vector database, background server, image generation, upload integration, or cloud hosting. Milestone 4 has not been started.

## Milestone 2

Local narrated educational videos from structured scene data.

```text
data/video.json — narration text
      ↓
Local Kokoro TTS (CPU)
      ↓
Per-scene PCM WAV files
      ↓
Real audio duration → data/video.generated.json
      ↓
Dynamic scene timing + end padding
      ↓
Remotion → narrated 1080p MP4
```

Python generates speech; React only consumes ready-to-use scene data. This stage uses no inference APIs, subscriptions, cloud TTS, or backend endpoints. Milestone 3 supplies content before this unchanged audio/rendering stage. Initial package/model downloads require internet; generation and rendering are local afterward.

### Windows setup

Use Node.js 22.18+ (24 recommended) and **Python 3.12**. Kokoro supports Python 3.10–3.13, but this project's pinned NumPy version requires 3.12+, so use Python 3.12 or 3.13. The system Python on this machine is 3.14, so a separate project-local 3.12 runtime was installed; system Python was not changed.

If `python --version` reports a supported version, run from the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.lock.txt
cd ..
```

`requirements.txt` lists the directly used TTS and local LLM packages; `requirements.lock.txt` pins every installed dependency for reproducing the validated environment. Both specify the official CPU PyTorch wheel index. To install from direct constraints instead, use `pip install -r requirements.txt`.

If PowerShell blocks activation, call the environment's Python directly; no execution-policy change is needed:

```powershell
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
```

If only Python 3.14 is installed, these optional bootstrap commands install Python 3.12 entirely inside the project:

```powershell
python -m pip install --target backend/.bootstrap uv==0.12.19
backend/.bootstrap/bin/uv.exe python install 3.12.14 --install-dir backend/.python --no-registry --no-bin
backend/.bootstrap/bin/uv.exe venv backend/.venv --python backend/.python/cpython-3.12.14-windows-x86_64-none/python.exe --seed --link-mode=copy
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
```

Download the pinned Kokoro v1.0 model and voices once (about 354 MB total). SHA-256 checksums are verified before use:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/download_models.py
cd renderer
npm install
cd ..
```

On this machine, setup and downloads have already been completed. Use `npm.cmd` / `npx.cmd` instead of `npm` / `npx` if PowerShell blocks their `.ps1` shims.

### Generate narration

Edit **only `data/video.json`** to change the source content. Every scene needs a unique integer `id`, non-empty `headline`, string `body`, and non-empty `narration`. There is no manual duration field.

```powershell
backend/.venv/Scripts/python.exe backend/scripts/generate_audio.py
```

With the venv activated, `python backend/scripts/generate_audio.py` is equivalent. Or from `renderer`, run `npm run generate:audio`.

The engine is [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), version 0.6.1, CPU inference, voice `af_sarah`, US English, speed 1.0. The model is initialized once per process. ONNX Runtime uses seed 0 and deterministic compute to make repeat runs reproducible on this pinned environment. The Python wrapper is MIT-licensed and the Kokoro model uses Apache 2.0. No fallback engine was needed.

Optional arguments:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/generate_audio.py --input data/video.json --output data/video.generated.json --voice af_sarah
```

Generation always regenerates the entire batch. WAVs are staged and checked before metadata is atomically replaced. Files are stored as `renderer/public/audio/<content-hash>/scene-ID.wav`; changed content or voice gets a different folder, keeping the previous metadata usable if generation fails. Repeating unchanged input reuses the same filenames. Old content folders are retained; only the latest metadata is rendered.

Malformed JSON, missing/empty narration, invalid IDs, invalid output folders, unknown voices, failed TTS, missing WAVs, and unreadable/truncated WAVs cause clear errors and a nonzero exit code. Failed synthesis does not publish partial metadata.

### Preview and render

```powershell
cd renderer
npm run dev
```

Select **VisualForgeVideo** in the local Remotion Studio URL. Click Play and leave audio unmuted. A browser user gesture may be necessary before audio starts.

```powershell
npx remotion render VisualForgeVideo generated/demo-with-voice.mp4
```

`npm run render` does the same. The original command with `generated/demo.mp4` also remains valid and renders the current narrated data to that filename; the existing Milestone 1 demo has been preserved.

The renderer checks audio availability before preview/render. If an audio file is missing, regenerate the batch. After source edits, run generation again before previewing or rendering; source JSON alone does not update the derived audio.

### Timing and audio

Generated `duration` means **actual WAV duration**, measured as sample count divided by sample rate. `SCENE_END_PADDING_SECONDS` in `renderer/src/timeline.ts` is the single padding setting (0.5 seconds). The same module exports FPS.

```text
scene frames = ceil((actual audio duration + end padding) × FPS)
scene start = sum of previous scene frame counts
total frames = sum of all scene frame counts
```

Each `Sequence` contains the reusable `TextScene` and `SceneAudio`, starting together at local frame zero. Audio has no trimming or looping. `SceneAudio` uses Remotion's supported [Html5Audio](https://www.remotion.dev/docs/html5-audio) component and `staticFile()` paths. The MP4 contains H.264 video and 192 kbps MP3 audio. MP3 preserves encoder-delay metadata through this Remotion version's intermediate audio file; the default raw AAC path produced a measurable 43 ms offset. No narration is trimmed to compensate.

The headline spring begins immediately; headline opacity completes at 0.5 seconds and body entrance runs from 0.4 to 1 second. Animation uses elapsed frame time, not fixed scene lengths. Keep text short enough for the fixed 1080p layout.

### Tests and media validation

From the project root:

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v
backend/.venv/Scripts/python.exe -m pip check
cd renderer
npm run typecheck
npm test
cd ..
backend/.venv/Scripts/python.exe backend/scripts/validate_render.py
```

Python tests cover source validation, reruns, batch failure, malformed input, invalid folders, and real generated files. Renderer tests compare metadata to actual WAV sample counts and test scene growth, padding, rounding, invalid inputs, and several FPS values. The media validator uses Remotion's bundled Windows FFmpeg/ffprobe to fully decode the MP4, verify codecs and timing, correlate each complete narration against its source, and check silent padding for overlap. It writes `renderer/generated/media-validation.json`.

[Milestone 1's historical validation](renderer/VALIDATION.md) remains available.

### Storyboard review and scene animation

The current renderer uses distinct opening/takeaway cards and concept/example/analogy cards, concise phrase captions, and gentler default transitions. Script prompts request a concrete situation, its mechanism, and its result. The existing Ocean, Forest, and Sunset themes also apply to optional intros and outros. These add 3 and 5 seconds respectively, only at the beginning/end of the complete video. Style and scene previews omit them.

Statistics must use numbers present in the narration. Code scenes need authored `codeLines`; the planner will not select an empty code scene. Older unsupported statistics or empty-code scenes remain editable and show errors before export: replan the affected visual or supply supported content.

The visual planner also chooses a scene composition: process demonstration, branching relationships, system layers, side-by-side comparison, timeline, or a close-up of each concept. Override it with **Scene composition** in each storyboard card. Compositions are constrained to compatible diagram kinds; charts retain their literal values. Replan an existing scene to request a new AI decision. Existing diagrams without an explicit composition use a suitable default.

Adjacent scenes with an exact shared concept label retain its label and icon in a continuity marker during the transition. This applies inside one rendered video or chapter; separately rendered chapters do not share objects across their boundaries.

Storyboard checks warn about three repeated compositions, dense on-screen text, and estimated long stretches with one visual. These are editorial heuristics. **Preview video style (30-60s)** renders a varied consecutive sample before approval, using complete narration and a maximum 60-second timeline. Short scripts produce shorter samples. In chapter storyboards, the button samples the selected chapter. Style samples are separate from draft/final exports and become stale when the document or visual style changes.

New prompt and pasted-script projects stop at a storyboard before generating narration or rendering the full video. Review each scene's narration and composition, choose its animation treatment, and use **Play scene** to render a short preview with narration. **Replan visuals**, **Rewrite scene**, and **Prepare audio** operate on the selected scene. Unchanged narration is reused from the audio cache.

Choose **Assemble concepts**, **Focus on relationships**, **Reveal step by step**, or the existing **Flow along connections** treatment for supported diagrams. Charts, cycles, and simple layouts retain their built-in animations. These are reusable educational graphics, not arbitrary generated footage. Distinct measured sentence cues drive reveals; concepts sharing a cue use illustrative pacing rather than claimed word-level alignment.

Use **Approve storyboard** before a new short project's full draft or final export. Editing the document invalidates approval. Existing projects remain compatible. Chapter projects have a **Storyboard** tab with the same scene controls and use their parent review approval before export.

### Narration-timed shot director

The episode review now includes **Watch a continuous preview** for a single-video storyboard. Choose a starting scene and render up to two minutes of consecutive, fully narrated scenes. In illustrated scenes, open **narration-timed shots** to choose a full view, follow view, or close-up for one spoken sentence. The shot plan is tied to measured narration beats, and changing one view leaves the spoken script intact. Generate the preview again after a shot change. A preview does not approve the storyboard or export the full episode.

The topic-aware visual director selects a flow, split, mapping, comparison, context-window, or network diagram from the supported narration and visual cues. It binds one visual action to each measured sentence and uses different SVG geometry, small concept icons, and carried objects across adjacent scenes. The episode review shows these actions beside each shot and flags repeated or crowded visuals. Diagrams illustrate relationships; they do not assert numeric model internals or token counts. Specialized real tokenizer examples, charts, code, and worked examples retain their dedicated renderers.

### Topic-aware visual planning

New prompt and pasted-script videos now run a local AI visual-planning stage before narration and rendering. The planner reads each scene and chooses a process, relationships, components, comparison, cycle, timeline, or a simple explanation. It selects concise labels directly from the narration and ties their reveals to measured sentence boundaries. Explicit percentage charts retain their source values.

This uses the same planning code for all subjects; topics do not need their own hand-built animation. Rendering uses a bounded library of diagrams, icons, and motion, rather than arbitrary generated footage. Complex or unsupported scenes can still need editing. Invalid model decisions retry up to three times, then use an explicit narration-based fallback recorded in the plan and job log.

For an existing short video, use the scene's visual replan action. For chapter videos, **Plan visuals from script** replans the chapters without rewriting narration; review and approve again before exporting. New chapter scripts receive AI visual planning automatically. These additional local-model calls take time on a CPU, and validated plans are cached for reuse.

### Long videos with chapters

In the studio, choose **Long video with chapters (7-30 min)** when creating a video. Select a target duration and enter the lesson topic.

1. Review and edit the chapter titles, teaching focus, visual approach, and target seconds. Chapter targets must add up to the selected video duration.
2. Approve the outline, then generate the chapter scripts. Completed chapters are saved; the same action resumes unfinished work after a failure or cancellation.
3. Review the narration, with one teaching scene per paragraph. Measure narration to see the actual duration. Expand or shorten individual chapters when needed, then measure again.
4. Approve the reviewed scripts and generate a 720p preview. Preview each chapter or download the combined draft.
5. Export the complete 1080p video when satisfied. Unchanged chapter outputs are reused within each render profile.

This workflow uses the configured local model, Kokoro, and Remotion. It requires no paid generation API. Duration is a target, not an exact promise. Diagram selection follows the script using the existing supported visual layouts; it does not create arbitrary cinematic footage. Review factual claims before publishing.



### Animated LLM worked examples

In a scene storyboard, open **Animated LLM worked example**, then **Add example**. Enter a short input (80 characters / 24 tokenizer tokens maximum), edit its label, and assign up to four actions to distinct narration sentences in order: tokens, token IDs, schematic processing, and generated continuation. **Use previous scene input** carries the same example into the next scene. Use **Prepare example** to inspect measured output, then **Play scene** or render. Short projects and chapter storyboards support the same controls.

The installed GGUF model provides actual token pieces/IDs and a bounded 12-token raw continuation. No extra model download or paid API is required. Measured results are cached outside editable documents by exact input and model identity; label/cue edits reuse inference. Changed inputs or model files invalidate the cache. Rendering prepares missing measurements before narration, closes the model worker, then starts TTS and Remotion. Invalid measurements fail explicitly.

Action starts follow measured narration sentence boundaries. Within-action reveal speed is illustrative, not inference latency or word alignment. Model layers are a labeled schematic, not recorded activations. Continuations may be unfinished or factually wrong; review before publishing. Checks catch certain explicit numeric token-count mismatches and warn about unsupported probability claims; they do not perform general fact checking. This milestone adds an opt-in LLM demonstration, not automatic worked examples for every subject.



### Simple automatic creation

The default studio now has two inputs: **Describe an idea** and **Paste a script**. Click **Generate video** once. There is no required length picker or storyboard approval step in this flow. For a prompt, the installed local model chooses a bounded target length and explains its choice. Short prompts use the existing short-video pipeline; targets of seven minutes or more automatically use the chapter pipeline. For a script, the narration stays intact and runtime follows its spoken length, pauses, and workspace bookends. Final duration is measured after narration.

The result screen shows estimated overall progress, the current stage, elapsed time, cancellation, and a single video player plus download link after validation. Rendering progress uses real completed-frame counts. Stage percentages are estimates and do not imply a reliable time remaining. The server runs the whole workflow independently of browser polling. Refreshing restores the active project, and Retry resumes using available checkpoints and cached artifacts. A failed or cancelled job remains visible with a retry action; connection loss is reported separately.

**Edit video** opens the existing detailed editor. Workspace and quality settings are optional; new simple creations default to 720p for faster local rendering, with 1080p available under **Output & workspace**. Script input supports 30-4,000 words and up to 64,000 characters. Video-generation time can substantially exceed video playback length on CPU hardware.

Frontend checks: `node --test review/progress.test.cjs`. Backend checks include automatic duration planning, script preservation, short/long routing, retries, cancellation, and UTF-8 subprocess logs.
