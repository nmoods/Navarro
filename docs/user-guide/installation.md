# Installation

ReelForge runs entirely on your computer. A GPU is optional.

## Requirements

| | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32 GB |
| Disk | 15 GB free (models + cache) | 40 GB |
| GPU | none (CPU mode) | NVIDIA with 6 GB+ VRAM for fast images |
| Software | Git, Node.js 22+, Python launcher (any), internet for first-time downloads | |

Python 3.13 is installed automatically by `uv`; your system Python version does not matter.

## Two modes

| Mode | What runs | Use it for |
|---|---|---|
| **Lightweight development** | Real API, database, queue, render engine and FFmpeg; deterministic stand-ins for the LLM, images, voice and transcription (clearly labelled “Test mode”) | UI work, tests, CI — no model downloads |
| **Full local AI** | Ollama (Qwen 3.5), ComfyUI (Stable Diffusion 1.5 + LCM-LoRA), Kokoro TTS, faster-whisper | Real videos |

## 1. Backend

```bash
# from the repository root
cd backend
uv sync                      # creates .venv with Python 3.13 and locked dependencies
uv run alembic upgrade head  # also runs automatically when the API starts
```

Lightweight mode (no models needed):

```powershell
# Windows PowerShell
$env:REELFORGE_LLM_PROVIDER="fixture"; $env:REELFORGE_IMAGE_PROVIDER="fixture"
$env:REELFORGE_TTS_PROVIDER="fixture"; $env:REELFORGE_STT_PROVIDER="fixture"
uv run uvicorn app.main:app --reload --port 8010
```

```bash
# macOS / Linux
REELFORGE_LLM_PROVIDER=fixture REELFORGE_IMAGE_PROVIDER=fixture REELFORGE_TTS_PROVIDER=fixture \
REELFORGE_STT_PROVIDER=fixture uv run uvicorn app.main:app --reload --port 8010
```

API docs: http://127.0.0.1:8010/api/docs

## 2. Frontend

```bash
cd frontend
npm ci
npm run dev      # http://127.0.0.1:5173
```

## 3. Full local AI

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File infrastructure\scripts\setup-ai.ps1   # one-time, ~9 GB of downloads
powershell -ExecutionPolicy Bypass -File infrastructure\scripts\start-ai.ps1   # each session
```

macOS / Linux:

```bash
./infrastructure/scripts/setup-ai.sh
./infrastructure/scripts/start-ai.sh
```

The scripts install everything inside `.runtime/` (git-ignored):

| Component | Licence | Size |
|---|---|---|
| Kokoro-82M + 54 voices, isolated worker env (`ai-engine/tts-worker`) | Apache-2.0 (worker GPL-3.0) | 340 MB |
| Ollama + `qwen3.5:4b` | MIT / Apache-2.0 | 3.3 GB |
| ComfyUI + PyTorch (CPU or CUDA) | GPL-3.0 (separate process) | ~1.5 GB |
| Stable Diffusion 1.5 (EMA-only) + LCM-LoRA | CreativeML OpenRAIL-M / OpenRAIL++ | 4.4 GB |
| faster-whisper `base.en` (downloaded on first use) | MIT | 150 MB |

Measured on an i7-10700 without a GPU: story and storyboard ≈6 min with `qwen3.5:4b`, each AI image ≈2 min,
voice ≈3× faster than real time, full production of a 45-second video ≈12 min. An NVIDIA GPU cuts image time
to seconds.

Then start the backend **without** the fixture variables. Open *Settings → AI services* to confirm each
provider is green. If ComfyUI is offline, ReelForge still renders using clearly labelled procedural art; if
Ollama is offline you can still write and edit scenes by hand.

### Choosing models

* Lower RAM: `REELFORGE_OLLAMA_MODEL=qwen3.5:2b`. Higher quality: `qwen3.5:9b`.
* More accurate captions: `REELFORGE_WHISPER_MODEL=small.en`.
* Any SD1.5 checkpoint you have the rights to can be placed in `.runtime/ComfyUI/models/checkpoints` and
  selected with `REELFORGE_COMFYUI_CHECKPOINT`. Check its licence first.

## 4. Docker (optional)

```bash
docker compose --profile lite up --build     # lightweight mode with PostgreSQL
docker compose --profile full up --build     # everything, CPU
docker compose -f docker-compose.yml -f infrastructure/docker/compose.gpu.yml --profile full up --build
```

## 5. Tests

```bash
cd backend && uv run pytest                 # unit, API, security, pipeline (renders real MP4s)
cd frontend && npm test                     # Vitest + Testing Library
cd frontend && npx playwright install chromium && npm run test:e2e   # full browser flow in test mode
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| “Story Director (Ollama) offline” | Run `start-ai`; check `http://127.0.0.1:11434/api/tags` lists the model |
| “checkpoint missing from ComfyUI” | Re-run `setup-ai`; the checkpoint name must match `REELFORGE_COMFYUI_CHECKPOINT` |
| “Kokoro worker python not found” | Run `uv sync` in `ai-engine/tts-worker` |
| Captions say “estimated timing” | faster-whisper could not load; check the API log; first run downloads the model |
| Render fails with an FFmpeg error | The job log contains FFmpeg's last error lines |
