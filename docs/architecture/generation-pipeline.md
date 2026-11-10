# Generation pipeline

All generation is asynchronous. The API enqueues a row in `generation_jobs`; a worker claims it, runs the
handler and reports progress after every step. The browser polls `GET /jobs/{id}` every 1.5 s.

## Job types and states

| Job type | Started by | Stages |
|---|---|---|
| `story` | create project, “Write the storyboard”, Hook Lab selection | `script_generation → storyboard_generation` |
| `production` | “Export video”, series episodes, one-click create | (story if missing) → `image_generation → voice_generation → animation → rendering → finalizing` |
| `preview` | “Preview” | same as production at half resolution, draft encode |
| `scene_regeneration` | inspector buttons | `storyboard_generation → image_generation → voice_generation` (one scene only) |
| `series_plan` | create/replan series | `script_generation` |
| `series_production` | “Produce all episodes” | fans out one `production` child per episode |

Terminal states: `completed`, `failed`, `cancelled`. `pending` jobs can be retried with exponential
back-off (15 s, 30 s…) up to `job_max_attempts` when the error is retryable (provider glitches, crashes).
Provider-unavailable errors fail immediately with an actionable message.

## The 20 steps

| # | Step | Where |
|---|---|---|
| 1 | Validate request (Pydantic, ownership, per-user active-job and hourly limits) | `api/routes/projects.py`, `workers/queue.enqueue` |
| 2 | Research: Wikipedia search + extract used as reference material | `StoryDirector.gather_reference` |
| 3 | Story in one pass: angle, music mood, three hooks (first in the preferred or Hook-Lab-chosen style), narration in three sections sized to the word budget (2.45 words/s), up to 3 claims; one revision if far off length | `StoryDirector.write_story` |
| 4 | (merged into 3: there is no separate brief or hooks call, which saves two LLM round trips) | — |
| 5 | (merged into 3) | — |
| 6 | Fact check: up to 3 claims → search → extract → LLM verdict + source URL | `fact_check` |
| 7 | Deterministic split into 4–12 scenes at sentence boundaries | `narrative.split_into_scenes` |
| 8 | Storyboard: visual type, image prompt, camera, effects, transition, SFX, music cue, visual data per scene. The model never echoes narration; it is attached from step 7 | `generate_storyboard`, `attach_narration` |
| 9 | Pacing analysis (density, repetition, hook strength) stored on the storyboard | `narrative.analyse` |
| 10 | Images through OpenVINO (LCM Dreamshaper v7 INT8 + TAESD, 4 steps), else ComfyUI, else procedural art (`auto` mode); cached by what the image shows (prompt, size, seed), so switching engines never redraws unchanged scenes | `ProductionService.ensure_image` |
| 11 | Voiceover per scene through Kokoro, cached by (voice, speed, language, text) | `ensure_narration` |
| 12 | Word timestamps with faster-whisper, aligned back onto the exact script tokens | `ensure_transcript`, `align_to_script` |
| 13 | Timeline plan: clip lengths and offsets so narration never overlaps across transitions | `media/assembler.plan_timeline` |
| 14 | Scene specs (captions with real timings, emphasis, overrides) | `build_specs` |
| 15 | Render scene clips in a process pool; reuse cached clips by content hash | `render_clips`, `media/scene_renderer.py` |
| 16 | Procedural score shaped by music cues + SFX + ducking + limiter | `media/audio/*` |
| 17 | Assemble with FFmpeg `xfade`/`concat`, mux AAC, `+faststart` | `media/assembler.assemble` |
| 18 | Thumbnail (hero frame + title) | `ProductionService.thumbnail` |
| 19 | Store MP4/JPEG as user-owned media, create `video_exports`, update project | `produce` |
| 20 | Mark job completed; UI swaps the monitor to the new render with signed URLs | worker + `useJob` |

## What gets regenerated when you edit

Every asset row in `scene_assets` stores an `input_hash` of everything that influenced it.

| You change | Regenerated | Reused |
|---|---|---|
| Captions, camera, effects, transition, visual data | that scene's clip | image, voice, transcript, other clips |
| Narration of one scene | that scene's voice + transcript + clip | its image, all other scenes |
| Image prompt / style / regenerate image | that scene's image + clip | voice, other scenes |
| Voice or speed (project) | all voices + transcripts + clips | images |
| Music or SFX | only the audio mix + final assembly | every clip |
| Uploaded/restored image | nothing until render; image is pinned (`locked`) and never overwritten | — |

Clips live in `work_root/clips/<hash>.mp4` (LRU-trimmed to 5 GB). Temporary job folders are removed after
each job and by the hourly maintenance pass.

## Cancellation, timeouts, recovery

* Cancel sets `cancel_requested`; the worker checks it between steps, every rendered second of video and
  while waiting on FFmpeg, then kills child processes.
* Each job has `timeout_seconds` (default 3600) checked cooperatively; FFmpeg calls have their own
  timeouts.
* Workers heartbeat on every progress update. Jobs whose heartbeat is older than
  `job_stale_after_seconds` are re-queued (or failed when attempts are exhausted) by `recover_stale`.

## Performance (measured on the dev machine: i7-10700, 8 cores, no GPU)

Real one-click run on 2026-11-10 (“Why the Mary Celeste was found empty”, 45 s target, 6 scenes, 3 AI images):

| Step | Time |
|---|---|
| Wikipedia research + one-pass story (`qwen3.5:4b`, ~450 output tokens) | 70 s |
| Fact check, 3 claims | 55 s |
| Storyboard (~700 output tokens) | 97 s |
| Images (OpenVINO LCM Dreamshaper INT8 + TAESD, 4 steps, 512×768, ≈21 s each) + voice + word timing | 107 s |
| Animation of 6 scenes at 1080×1920 (process pool) | 70 s |
| Music, mix, assembly, encode, thumbnail | 86 s (assembly now uses all cores: ≈40 s less) |
| **Total, idea to 47.6 s MP4** | **8 min 5 s** |

Previously (2026-11-09, four LLM calls and ComfyUI `--cpu`): 11.9 min without research. Re-exporting a
project whose images, voices and clips are cached: under a minute.

| Component benchmark | Time |
|---|---|
| OpenVINO pipeline load (once, at API start-up) | 9–11 s |
| OpenVINO image, 512×768, 4 steps: full VAE decoder / TAESD decoder | 34 s / 21 s |
| SD 1.5 + LCM-LoRA, 6 steps, ComfyUI `--cpu` | ≈125 s |
| Kokoro TTS | 12.7 s of speech in 4.2 s (≈3× real time) |
| faster-whisper `base.en` int8 | ≈2.5 s for a 13 s clip |
| Scene render 1080×1920, parallax + fog + dust + captions | ≈66 ms/frame |
| Final assembly of 47.6 s, x264 medium: 4 threads / all threads | 82 s / 44 s |
