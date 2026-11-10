# System architecture

NaRRAVO is a **modular monolith**: one FastAPI codebase with strict internal boundaries, plus three
isolated processes for components with incompatible licences or heavy resource needs. Every AI capability
runs locally; nothing depends on a paid API.

```
 Browser (React SPA)                        Cloudflare Pages / nginx / Vite dev
     │  HTTPS, Bearer access token (memory) + httpOnly refresh cookie
     ▼
 ┌───────────────────────────── FastAPI (backend/app) ─────────────────────────────┐
 │ api/        routes, schemas validation, auth deps, ownership checks, presenters  │
 │ core/       settings, security (Argon2, JWT, signed media URLs), middleware      │
 │ application/ use cases: StoryDirector, story_service, production, uploads        │
 │ domain/     enums + Pydantic story schemas (also the LLM JSON schemas)           │
 │ infrastructure/ adapters: database, storage (local/R2), providers registry       │
 │ media/      render engine (pure: spec in → MP4 out, no DB, no network)           │
 │ workers/    DB-backed job queue, handlers, worker loop (embedded or standalone)  │
 └──────────────┬──────────────────┬───────────────────┬───────────────────────────┘
                │ SQL               │ files / S3 API    │ localhost HTTP / pipes
                ▼                   ▼                   ▼
        PostgreSQL / SQLite   Local disk / R2     Ollama (LLM) · ComfyUI (images, GPL, HTTP)
        (Supabase in prod)                        Kokoro worker (TTS, GPL, stdin/stdout JSON)
                                                  faster-whisper (in-process) · FFmpeg (subprocess)
```

## Layers and dependency rule

Dependencies point inwards: `api → application → domain`, with `infrastructure` implementing the
**ports** declared in `application/ports.py`. The render engine (`media/`) depends on nothing else in the
app except `core.errors.JobCancelledError`, so it can be unit-tested and moved into its own worker image.

| Package | Responsibility | Must not |
|---|---|---|
| `domain/` | Vocabulary (enums), story/storyboard schemas, length budgets | import infrastructure |
| `application/` | Use cases: Story Director, persistence of stories, production pipeline, uploads | know HTTP |
| `infrastructure/` | Adapters: Ollama, ComfyUI, Kokoro, Whisper, Wikipedia, storage, SQLAlchemy models | contain business rules |
| `media/` | Frame rendering, captions, effects, maps/charts, audio synthesis and mixing, assembly | touch DB/network |
| `api/` | HTTP contract, authN/Z, rate limits, response shaping | contain pipeline logic |
| `workers/` | Queue, retries, cancellation, timeouts, handler dispatch | be imported by `media/` |

## Provider architecture

Each capability is a Protocol in `application/ports.py` with `health()` exposing availability and
capabilities. Adapters are chosen by configuration in `infrastructure/providers.py`:

| Port | Default adapter | Fallback / alternative | Test double |
|---|---|---|---|
| `LLMProvider.complete_json` | `OllamaProvider` (structured outputs, schema-repair retries) | any Ollama model | `FixtureLLM` |
| `ImageProvider.generate_image` | `ComfyUIProvider` (SD1.5 + LCM-LoRA workflow) | `ProceduralImageProvider` (auto mode, labelled) | `FixtureImageProvider` |
| `TTSProvider.generate_speech/list_voices` | `KokoroProvider` (isolated worker, voice blending) | — (clear error) | `FixtureTTS` |
| `TranscriptionProvider.get_word_timestamps` | `FasterWhisperProvider` + script alignment | estimated timing (labelled) | `FixtureTranscriber` |
| `ResearchProvider.search_sources/retrieve_source` | `WikipediaResearchProvider` (fixed host) | disabled → claims marked uncertain | `FixtureResearch` |

The higher-level operations named in the brief (`generate_script`, `generate_storyboard`,
`generate_hooks`, `generate_scene_prompt`, `verify_claims`) live in `application/story_director.py` and are
written against the ports, so swapping the LLM never changes business logic. Test doubles are refused by
configuration validation in production and flagged `is_test_double` in the UI.

## Processes

| Process | How it runs | Why separate |
|---|---|---|
| API (+ embedded worker in dev) | `uvicorn app.main:app` | — |
| Worker | `python -m app.workers.runner` | CPU-heavy rendering must not block the API; scale independently |
| Kokoro TTS worker | spawned by `KokoroProvider`, JSON lines over stdin/stdout | espeak-ng/phonemizer are GPL-3.0; process isolation keeps the backend permissively licensed |
| ComfyUI | own venv, `127.0.0.1:8188` | GPL-3.0, PyTorch, GPU; called over HTTP |
| Ollama | own binary, `127.0.0.1:11434` | model server |
| Scene render pool | `ProcessPoolExecutor` (up to 4) | NumPy/OpenCV per-frame work is CPU bound |

## Key technical decisions

| Decision | Choice | Reason |
|---|---|---|
| Renderer | Own Python compositor (NumPy/OpenCV/Pillow → FFmpeg pipe) instead of Motion Canvas | Motion Canvas has no supported headless render path and no release since Dec 2024 (see research/technology-evaluation.md). A deterministic server-side engine renders 1080×1920 at ~66 ms/frame on an 8-core CPU and caches per scene. Revideo remains a future option. |
| Transitions | FFmpeg `xfade` at assembly time | Per-scene clips stay independently cacheable |
| Python | 3.13 via uv | onnxruntime has no 3.15 wheels; kokoro-onnx supports < 3.14 |
| Queue | Database table with `FOR UPDATE SKIP LOCKED` | No Redis needed; interface allows migration later |
| Music & SFX | Procedurally synthesised | Royalty-free by construction, no licence audit per track |
| Narration fidelity | Script split deterministically; LLM designs visuals for fixed text | Small local models cannot silently rewrite approved lines |
| Maps | Natural Earth 1:110m (public domain) + offline gazetteer | No geocoding API, no rate limits, deterministic |
| Auth | Built-in (Argon2id + JWT + rotating refresh cookie) or Supabase JWKS | Works fully offline; Supabase optional for hosted deployments |
| Media delivery | HMAC-signed expiring URLs (or R2 presigned URLs) | `<video>` tags cannot send bearer tokens; no public buckets |

## Scaling path

1. Run the worker separately (`NARRAVO_EMBEDDED_WORKER=false`), raise `WORKER_CONCURRENCY` per box.
2. Point several worker machines at the same PostgreSQL; claims are `SKIP LOCKED`.
3. Move media to R2 (`NARRAVO_STORAGE_BACKEND=r2`); workers keep a local read-through cache.
4. Replace the in-process rate limiter with Redis when running more than one API replica.
5. Split providers onto GPU hosts by setting `OLLAMA_URL`/`COMFYUI_URL` to private network addresses.
