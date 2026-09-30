# Qwen3 GGUF integration

Hardware: Intel Core i3-1005G1 (2 cores / 4 threads), approximately 16 GB RAM, Intel UHD integrated graphics. Inference is configured for CPU only, two threads, one slot, and a 4,096-token context.

## Automated checks

- 83 backend tests passed, including 10 GGUF-specific tests.
- JavaScript syntax check passed for the studio model-status display.
- Tested schema propagation, bounded generation arguments, truncated-response rejection, owned-process cleanup, missing-model errors, explicit legacy selection, model-specific checkpoint invalidation, accurate report metadata, download resumption, and preservation of existing weights on checksum failure.
- The complete suite requires access to existing media files and process-tree termination. A sandboxed run could not read one existing WAV or terminate a timeout fixture. The final run with the required access passed.

## Real-model check

Completed: the 2,497,281,120-byte model passed the pinned SHA-256 check and was activated. The real prompt produced a three-scene 720p MP4 with full decoding and audio-sync validation passing. Project: `88fcff790f6a`, workspace: `Qwen3 local model test`. Script generation took 128.137 seconds (8.622 seconds loading); the complete job took 244.109 seconds. Measured llama.cpp peak working set was 5,139,329,024 bytes, excluding the Python worker and other applications. All fields passed structural validation; two narration fields needed duration rewrites. Actual video duration was 20.2 seconds for a 30-second target, so the editor correctly flags a duration warning. Facts were not independently verified. This one short-video test does not validate 7?30 minute generation.

The queued real-video check completed successfully. Live status is recorded in `data/gguf-validation-status.json`, with logs in `data/gguf-validation.log` and `data/gguf-setup-xet.log`. Status `complete` means the generated draft passed the existing media validator; it does not mean its facts were independently verified. A failure is recorded without claiming a successful video.

`backend/scripts/validate_gguf.py` runs a new 30-second-target prompt through the studio, using “How does a library work?” and the 720p draft profile. It saves results to `data/gguf-validation.json`; the project retains the generation report, measured speech, MP4 validation, and worker logs. The test performs no upload.

Installation verifies SHA-256 for both the runtime archive and the model before writing the active configuration. A failed download does not activate an incomplete model. The old Transformers weights remain available for deliberate rollback.
