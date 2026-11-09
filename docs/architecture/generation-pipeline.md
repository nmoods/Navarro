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
| 3 | Story brief (audience, angle, arc, key facts with confidence) | `StoryDirector.generate_brief` |
| 4 | Hook Lab: six hooks, one per style | `generate_hooks` |
| 5 | Script to a word budget (2.45 words/s), revision pass if far off | `generate_script` |
| 6 | Fact check: each claim → search → extract → LLM verdict + source URL | `fact_check` |
| 7 | Deterministic split into 4–12 scenes at sentence boundaries | `narrative.split_into_scenes` |
| 8 | Storyboard: visual type, camera, effects, transition, SFX, music cue, palette, visual data per scene; narration enforced verbatim | `generate_storyboard`, `enforce_narration` |
| 9 | Pacing analysis (density, repetition, hook strength) stored on the storyboard | `narrative.analyse` |
| 10 | Images through ComfyUI (or procedural art when offline in `auto` mode), cached by input hash | `ProductionService.ensure_image` |
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

| Operation | Time |
|---|---|
| Kokoro TTS | 12.7 s of speech in 4.2 s (≈3× real time) |
| faster-whisper `base.en` int8 | ≈2.5 s for a 13 s clip |
| Scene render 1080×1920, parallax + fog + dust + captions | ≈66 ms/frame |
| Procedural visuals (map, timeline, charts) at 540×960 draft | 17–31 ms/frame |
| Music + SFX mix for 44 s | 2.5 s |
| Final assembly with 8 transitions (44 s) | 5.8 s |
