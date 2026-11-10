# Project status

_Last updated: 2026-11-10_

“Verified” means exercised by an automated test or a real run on the dev machine (i7-10700, 32 GB RAM,
no GPU, Windows 11). Nothing below is marked complete unless it ran.

## Completed and verified

| Area | Feature | Evidence |
|---|---|---|
| Research | Competitor, feature matrix, 20+ opportunities, positioning, technology, AI models, licence audit, free infrastructure | `docs/research/*` |
| Backend | FastAPI app, 22-table schema, Alembic migration (upgrade/downgrade on SQLite, DDL renders for PostgreSQL) | migration run, `test_*` |
| Auth | Local accounts (Argon2id, JWT, rotating refresh cookie, reuse detection with grace window, CSRF header), Supabase JWKS mode | `test_api.py` (Supabase mode not run against a live project) |
| Isolation | Ownership checks on every route; cross-user access returns 404; signed media URLs | `test_users_cannot_access_each_others_data`, signed URL tamper test |
| Security | Rate limits, body-size limit, upload sniffing/re-encode, path-traversal-safe storage, safe FFmpeg invocation, audit log, security headers | `test_api.py` |
| Queue | DB-backed jobs, retries with back-off, cancellation, timeouts, stale-job recovery, per-user limits | `test_pipeline.py`, e2e |
| Story Director | Wikipedia reference → one-pass story (3 hooks + narration in sized sections + claims) → fact check (3 claims) → deterministic scene split → compact storyboard → direction polish | real run with `qwen3.5:4b` (≈3.7 min incl. research and fact check for 45 s) + fixture tests |
| Visual intelligence | 9 visual types incl. animated maps (offline geodata), timelines, infographics, comparison, newspaper, kinetic type, parallax | smoke render of every type, `test_direction.py` |
| Render engine | Camera moves, 2.5D parallax, 12 atmosphere effects, colour grading, animated captions (5 styles) synced to real word timings, xfade transitions, thumbnail | pipeline tests, e2e, 66 ms/frame at 1080×1920 |
| Audio | Kokoro TTS (54 voices, blending) in an isolated GPL worker; faster-whisper word timestamps aligned to script; procedural music and SFX with ducking | real runs |
| Caching | Per-asset input hashes and per-scene clip cache; an edit regenerates only what changed | `test_story_then_production_then_scene_edit_reuses_assets` |
| Editor | Scene list (drag reorder), monitor with timecode, inspector (narration, visuals, camera, effects, transitions, captions, SFX, music cue, duration, visual data), image upload/variants/restore, per-scene regenerate, timeline with 5 tracks, Hook Lab, fact-check and pacing panels, project settings | e2e + manual browser review |
| Other pages | Landing, auth, dashboard, creation wizard, projects library, Series Factory + bible, content planner (calendar, drag scheduling, AI topic discovery), media library, voice studio, Story DNA, settings with AI status | type-checked build, browser review |
| Tests | Backend 22 (pytest, incl. assembler regression), frontend 13 (Vitest + RTL), e2e 3 (Playwright: auth; create→edit→regenerate→render→download→re-export; dashboard one-line video) | all passing on 2026-11-10 |
| Real local AI, end to end | One click: Wikipedia research → `qwen3.5:4b` story + fact check + storyboard → OpenVINO LCM images → Kokoro voice → Whisper timing → render → 1080×1920 MP4. | 8 min 5 s for a 47.6 s video on 2026-11-10 (was 11.9 min with the four-call story and ComfyUI, without research); Roanoke re-export with cached assets 58 s |
| Quick creation | Dashboard one-line “Make my video”; single-screen New video page with example topics and “More options”; elapsed time on progress | e2e `one line on the dashboard produces a finished video` |
| Subtitles | SRT/WebVTT export from aligned word timings | `test_create_edit_regenerate_render_download` |
| Ops | Docker Compose (lite/full/GPU), setup/start scripts for Windows/macOS/Linux, Supabase RLS SQL, docs | Windows scripts run end to end |

## In progress / partially verified

| Item | State |
|---|---|
| Fact checking against Wikipedia | Works when `NARRAVO_RESEARCH_CONTACT` is set (Wikimedia blocks requests without a contact in the User-Agent); set to the project repo URL in this machine's `backend/.env`. Checks up to 3 claims per script. Without a contact, claims stay “Not checked” and the UI says why. |
| Docker images | Written, not built on this machine (Docker is not installed here). |
| Supabase / R2 deployment | Code paths implemented (JWKS auth, RLS SQL, S3-compatible storage); not exercised against live accounts. |
| macOS/Linux setup script | Written; only the Windows script was executed. |

## Outstanding

* Depth estimation model (e.g. Depth-Anything-V2-Small, Apache-2.0) as an optional upgrade to the heuristic parallax depth.
* Per-user storage quota and CPU-time quota for public multi-tenant hosting.
* Redis-backed rate limiter for multiple API replicas.
* Content repurposing (one story → several lengths/aspect ratios in one click); the data model supports it.
* Template marketplace UI beyond private/public templates (no payments, by design).
* Code-splitting of the 297 kB main bundle further; accessibility audit with a screen reader.

## Known issues

* Final exports are large (≈100–125 MB for 48 s at CRF 19) because film grain and particles compress poorly;
  a higher CRF or less grain would shrink them. Not changed yet, since it is a quality decision.
* The 4B model still slips on details even with reference text (a run named the Mary Celeste's captain
  wrongly); the fact checker flags some of these, so review the Script tab before publishing.
* Fixed 2026-11-10: a crossfade right after a hard cut made FFmpeg fail on mismatched timebases (affected
  real exports; now covered by `tests/test_assembler.py`). Alembic's logging setup silenced the app's INFO
  logs after start-up (fixed).

* Small local models (4B) can produce factual errors in scripts; e.g. a Roanoke draft claimed survivors returned to England. The fact checker and human review are the mitigation; larger models (`qwen3.5:9b`) help.
* Small models often omit structured visual data; the direction-polish step fills it from narration or downgrades the visual type, so procedural scenes may show fewer data points than intended.
* Offline geocoder covers Natural Earth 1:110m places plus a curated list; unknown places (e.g. Hatteras Island) make the scene fall back to parallax.
* The project status becomes “Video ready” after a draft preview too.
* SD 1.5-family models (including the default LCM Dreamshaper) can duplicate subjects on tall canvases; images are generated at 512×768 (512×640 for portraits) and cropped.
* The first real script had a factual slip (“Croatoan on every post”); it was corrected by hand in the editor before the demo was rendered.

## Technical decisions

See `docs/architecture/system-architecture.md` (“Key technical decisions”). Highlights: own Python
compositor instead of Motion Canvas; Python 3.13; DB-backed queue; procedural music/SFX; Kokoro in a GPL
worker process; deterministic narration split; default API port 8010.

## Decisions

1. **Product name**: renamed from ReelForge AI to **NaRRAVO** on 2026-11-10 (reelforgeai.io sells a near-identical
   product). Name check in `docs/research/market-positioning.md`: no AI video product called Narravo found;
   narravo.com belongs to an unrelated brokerage. EU/UK trademark registers not yet searched.
2. **Wikimedia contact**: the owner chose the GitHub repo URL (`https://github.com/nmoods/Navarro`), stored in
   the git-ignored `backend/.env`.
3. **Project licence**: still open. MIT is a placeholder for the main code (the TTS worker is GPL-3.0).
