# Milestone 6: automatic visual director

## Delivered behavior

One **Generate video** action accepts a prompt or a pasted narration script and runs the required stages through a validated MP4. Prompt mode uses the existing local Qwen script generator. Script mode preserves spoken content, groups it into scenes, and extracts readable titles and concise captions. A script title is optional.

The template director chooses process, comparison, relationship, example, opening, explanation, and takeaway layouts. It uses nine built-in SVG icons, timed reveals, active-point highlighting, a current-sentence caption, and scene fades. Relationship diagrams retain the source relationship phrase. Unsupported structures fall back to explanation cards rather than inventing diagram content.

## Actual script-to-video run

- Browser input: five paragraphs about libraries; generated project `3ca75110a216` with no manual scene setup.
- [Final video](data/editor/3ca75110a216/video.mp4): 1920 x 1080, 30 FPS, 1682 frames, 56.066667 seconds; H.264 video and MP3 audio at 48 kHz.
- Full decode passed. Minimum source correlation: 0.999966038. Maximum absolute narration offset: 0.000333333 seconds (less than one frame).
- Narration matches the pasted script after whitespace normalization. Eleven sentence beats are measured from actual synthesized WAV samples. All six joins contain exactly 2,880 zero-valued PCM16 samples, or 120 ms at 24 kHz.
- Process card reveal times: [0.0, 3.3506666666666667, 7.256] seconds relative to scene 2. Inspected frames before and after reveals show only the current/previous steps; the later steps appear with their matching spoken sentence.
- Inspected the opening, process, comparison, and relationship frames. Text fits and the relationship keeps its original meaning.
- Browser MP4 playback reached 36.88 seconds, readyState 4, with no media error; it was then paused.
- The first test render was deliberately cancelled to improve extracted titles. Cancellation stopped its subprocess and preserved all five completed WAVs. The final automatic run reused those five WAVs and completed in 99.970 seconds. This is render/validation time with cached speech, not cold-generation time.
- An exact preview of the completed process scene took 6.683 seconds and reused its WAV. The preview is sampled after the last planned reveal, so all diagram labels are visible.
- [Machine validation](data/editor/3ca75110a216/media-validation.json), [timing evidence](data/editor/3ca75110a216/director-evidence.json), [first step](data/editor/3ca75110a216/step-one.png), [third step](data/editor/3ca75110a216/step-three.png).

## Actual prompt-only run

Browser input: **How does a library work?**, with 30-second duration guidance. Project `0bd1b0944914` completed through [MP4 validation](data/editor/0bd1b0944914/media-validation.json) with no manually supplied script. The generated video has five scenes, 2131 frames, and 71.033333 seconds. Full decode passed; minimum narration correlation was 0.999967289.

The completed run took 831.864 seconds (about 13.9 minutes) on this laptop, including script generation, five new sentence-timed WAV files, rendering and validation. Script generation itself took 550.891 seconds and peaked near 9.60 GB working set. This demonstrates functional one-click generation, not fast local-model inference. The duration guidance is approximate: this run exceeded the requested 30 seconds.

The first prompt test revealed conflicting short-outline instructions and was cancelled. Short-video guidance now combines the lesson into three core points instead of requesting six separate sections. The corrected run still needed a retry because the model produced an overly long outline point, then completed normally.

**Editorial limitation observed:** scene 3 says a reader may keep a book "for as long as you like" but also must return it on time. A new nonblocking conflicting-conditions warning flags that claim, alongside the existing long-narration warning. The original model text remains visible for correction. Comparison selection was also tightened after this test: an internal "but" no longer makes unrelated sentences into opposing cards; explicit contrast transitions are required. This correction affects new plans and leaves saved storyboards unchanged. This prompt-generated video is a technical test artifact and needs editorial correction before publishing; the pasted-script library guide above is the recommended demonstration. [Recorded quality review](data/editor/0bd1b0944914/quality-review.json).

## Verification

64 Python tests and six renderer tests passed. TypeScript typecheck and browser JavaScript syntax checks passed.

Automated coverage includes narration preservation, title extraction, script limits, semantic template choice, measured sample timing, invalid timing rejection, corruption repair, sentence-audio cache isolation from legacy speech, targeted scene replanning, full prompt-job orchestration with deterministic stage fixtures, render reuse, script HTTP input, and open-tab save recovery after server token rotation. Renderer tests cover timing boundaries and reject reveals that do not correspond to measured speech boundaries.

Existing milestone scripts, videos, and saved user projects remain intact. An existing browser tab contained unsaved edits, so it was left open and all UI testing used a new tab. Trusted same-origin browser requests can recover from server token rotation without losing those unsaved fields; other callers still need the current token and the exact local Host/Origin checks.

## Implementation and limits

New planning logic: `backend/services/director.py`. Short-prompt outline guidance and conflicting-conditions editorial checks were also improved. Updated editor API, job orchestration, store validation, incremental audio, audio CLI, review UI, Remotion visual component/types, and renderer timing validation. No new package, cloud service, PowerPoint dependency, or model download was added.

This release uses extractive templates and explicit linguistic cues, not a general-purpose illustration generator. Pasted scripts should contain 30-720 English spoken words across 2-16 teaching paragraphs of 15-60 words. Oversized or invalid input is rejected with guidance instead of being silently truncated. The local language model can still exhaust validation retries; partial validated drafts and saved projects remain recoverable. Timing is measured at sentence level, not word-level forced alignment. Sentence synthesis can introduce different prosody from whole-paragraph synthesis. Quality heuristics do not verify facts.

Narration edits replan only the affected automatic scene; layout/order edits reuse speech. Older projects retain paragraph narration and their existing editing workflow. Failed or cancelled jobs never publish an unchecked MP4. The original command-line milestone pipeline remains available; the new automatic flow is exposed through the local studio.

Previous report: [VALIDATION-MILESTONE5.md](VALIDATION-MILESTONE5.md).
