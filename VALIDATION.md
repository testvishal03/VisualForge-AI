# Milestone 7 validation - VisualForge AI

Date: 2026-09-27. Local Windows laptop; CPU rendering and inference; no cloud model or upload.

## Implemented

- Atomic workspace catalog at `data/editor/workspaces.json`: single-video and series workspaces, names, themes, channel labels, audience guidance, duplication, episode ordering, recoverable Trash and restore.
- Legacy project adoption leaves documents and revisions untouched. Trash preserves every project file and shared WAV. Duplicate workspaces copy editable source and clear exported-artifact references.
- Twelve visual types, seventeen local SVG icons, supported semantic structures extracted from narration, and alternate compositions for general explanation/process/relationship/timeline/system-part layouts. Specialized water-cycle illustration, cyclic diagram, percentage chart, and comparison each have one composition.
- Measured sentence cues control labels, line drawing, movement, and highlights. Items sharing a sentence highlight together. Transitions remain non-overlapping; every scene retains 0.5 seconds of end padding.
- Separate `draft.mp4` (1280x720) and `video.mp4` (1920x1080), both 30 FPS H264 + 48 kHz MP3. Publication happens only after full decoding, source correlation, audio-offset and padding checks pass.
- Exact scene-count planning and bounded per-scene narration word budgets; runtime estimate before speech and measured runtime afterward. A duration overrun gets at most one rewrite; the shortest structurally valid candidate is retained and cached if it still misses the preferred maximum. Estimated or measured overruns receive a visible review warning. Hard schema and blocking content checks still fail closed. Audience guidance reaches both outline and scene drafting.
- Targeted visual replanning, verified audio reuse, artifact fingerprints incorporating theme and render profile, unchanged-output reuse, and sequential heavy jobs.

## Verification

The complete Python suite passed 73 tests after adding workspace and export tests. Focused regression checks also cover the final title/audience changes. Renderer tests passed 7 cases, TypeScript typechecking passed, and browser JavaScript syntax checking passed.

Tests cover migration without source mutation, Trash/restore, duplicate independence, exact episode membership during reordering, invalid settings, busy-task guards, style/profile invalidation, failed validation preserving an earlier export, percentage validation, missing-evidence fallbacks, duration arithmetic, targeted budget retries, and existing cache/cancellation behavior.

Browser checks use a new Chrome tab and preserve existing tabs. Workspace creation and script-to-draft submission were exercised through the UI. Dialog error feedback and draft-button binding issues found during testing were corrected.

## Actual media

The authored demonstrations are grouped in **Visual storytelling demos**. All preserve their narration except an explicitly revised garden takeaway after the quality gate rejected its initial vague example.

| Video | Layouts | Runtime | Exports |
| --- | --- | --- | --- |
| Water cycle in motion | Illustrated water cycle, takeaway | 25.90 s | 720p and 1080p |
| Inside a computer | System parts, process | 24.83 s | 720p |
| A garden through time | Timeline, takeaway | 26.90 s | 720p |

Detailed phase results: `data/milestone7-validation.json`. Each project has separate profile validation reports and render props. Actual Remotion preview PNGs were inspected for title fit, legibility, connections, and matching captions.

The first cold water-cycle run took 234.517 seconds including fresh speech and renderer startup. A subsequent warm draft render took 88.252 seconds; the warm final render took 63.409 seconds. These runs had different cache/startup conditions and are not a controlled 720p-versus-1080p speed comparison. An unchanged verified final output was reused in 0.028 seconds. The first computer draft took 69.630 seconds and the first successful garden draft took 64.928 seconds, including their new narration.

## Scope and limitations

The visual director is a bounded evidence-based grammar. It does not understand every possible topic, generate arbitrary illustrations, retrieve stock footage, or fact-check claims. Unsupported concepts fall back to simpler cards. Timelines require explicit ascending years; numeric charts require two to four explicit percentages. The water illustration requires all four phases in narrated order. Labels, narration, and diagrams remain editable.

The only configured narration voice is the existing English Kokoro Sarah profile. A word budget improves duration control but cannot promise exact runtime; the UI flags a deviation beyond the greater of five seconds or 15 percent. Authored scripts are never automatically cut. The small local model can still be slow, retry, or fail validation, and generated facts require review.

Series workspaces are local organizational tools. No YouTube playlist or upload is created. Trash is recoverable and does not free disk space; permanent deletion is not included.

## Final results and browser checks

All three published authored demos match the final renderer fingerprint. `data/milestone7-final-media.json` records final dimensions, runtimes, source correlations, and maximum audio offsets. The final renderer produced water draft/final exports in 59.828/47.107 seconds with cached speech, computer draft in 34.882 seconds, and garden draft in 39.187 seconds. Verified final reuse took 0.017 seconds. These timings are observations, not controlled speed benchmarks.

Browser checks passed for creating a series and a single-video workspace, renaming, changing theme, duplicating an empty workspace, moving that copy to Trash, restoring it, and moving an episode up and back down. Empty QA workspaces were left recoverably in Trash. The three demonstration episodes remain in their original order. No existing user workspace was deleted. Earlier console errors were corrected; no new errors appeared in the final workflow.

Static chart and cycle fixtures were rendered in Sunset and Forest themes and visually inspected. The cycle connector routing was corrected during this check. These are labeled synthetic geometry fixtures, not narrated teaching videos.

## Actual prompt-generation limitation

The 30-second local prompt test is project `e78449f10720` (workspace **30-second prompt test**). It did NOT produce a video. Initial outline generation repeated a JSON key and failed after three attempts (316.735 seconds). Correcting conflicting short-outline instructions produced an exact three-scene outline on the first attempt, but the first narration repeatedly missed the strict word budget (149.713 seconds). Duration handling was then changed to a bounded rewrite with an explicitly flagged, structurally valid fallback.

The final resumed test reused the validated outline and caption. A targeted rewrite shortened scene 1 from 43 to 24 words, and scene 2 also validated at 24 words. Scene 3 returned prose instead of JSON and then twice exceeded the hard 60-word scene limit. The run failed after 189.678 seconds, preserved its checkpoints, and published no incomplete or unchecked MP4. The model also proposed misleading advice about returning library books late in its outline, demonstrating why generated facts still need review. It was not silently replaced with authored text to manufacture a successful prompt result.

Failure evidence is retained in `data/milestone7-prompt-result.json`, `data/milestone7-prompt-retry-result.json`, and `data/milestone7-prompt-final-result.json`; stage logs and validated field checkpoints remain in the project folder. The current small local model is not reliable enough to promise prompt-only publishing. The authored-script workflow is the validated dependable path for this release.

Final recovery UI check: the unsuccessful prompt workspace shows **Generation failed**, an incomplete-draft explanation, and a checkpoint retry action. The completed series shows **Ready** for the 1080p water video and **Draft ready** for the other two episodes. Browser playback of the final MP4 advanced beyond 11 seconds with readyState 4 and no media error, then was paused for handoff. The local server remains available at http://127.0.0.1:8765/.
