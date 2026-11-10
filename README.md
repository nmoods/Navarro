# NaRRAVO

**Turn any idea into a cinematic story.** NaRRAVO is an open-source, local-first studio for faceless
short-form video. It researches a subject, writes the narration, directs every scene, voices it, times the
captions to the voice and renders a finished MP4 for TikTok, Reels or Shorts. Everything runs on your
own hardware. There are no credits, no paywalls and no paid AI APIs.

> Name check (2026-11-10): no AI video product called Narravo was found. The name is used by unrelated
> projects (a London brokerage at narravo.com, an iOS text-to-speech app, a hobby novel-writing app, a YouTube
> audio-story channel). Details and what is still unchecked are in `docs/research/market-positioning.md`.

## What makes it different

| | |
|---|---|
| **Visual intelligence** | Each scene gets the visual that explains it: animated maps (offline geodata), timelines, infographics, comparisons, archival front pages, kinetic typography, character portraits, or AI images with camera motion and 2.5D parallax. It is not a slideshow. |
| **Cinematic engine** | Its own renderer, with 12 camera moves, depth parallax, fog, smoke, embers, rain, snow, light rays, lightning, grain, 11 transitions and per-style colour grading. Scenes are cached individually. |
| **Story Director** | Reads Wikipedia, then writes the angle, three hooks (Hook Lab) and narration to length in one pass, then directs the storyboard. All output is validated JSON. The narration you approve is never silently rewritten. |
| **Fact checker** | Claims are checked against Wikipedia and shown as supported, contradicted or not found, with source links. |
| **Edit one scene** | Change a line, image or caption and only that scene is rebuilt. Assets are cached by input hash and earlier image variants can be restored. |
| **Story DNA** | Reusable channel identity: style, palette, voice, captions, music, camera preferences and watermark. |
| **Series Factory** | Plan connected episodes with a series bible. Recurring characters keep consistent seeds across episodes. Episodes are produced in a queue, and one failure never stops the rest. |
| **Voice studio** | 54 Kokoro voices in 9 languages, with voice blending and speed control. |
| **Honest audio** | An original score is composed per video from scene cues, with synthesised sound effects and narration ducking. All of it is royalty-free by construction. |

## Making a video

Type an idea on the dashboard and press **Make my video**. NaRRAVO writes, illustrates, voices, captions and
edits a 45-second vertical video, then opens it in the editor where every scene can be changed. The
**New video** page adds length, format and look, and *Review the storyboard before rendering* if you want
to approve the script first.

## Quick start

```bash
# backend (Python 3.13 is installed automatically by uv)
cd backend && uv sync
uv run uvicorn app.main:app --reload            # http://127.0.0.1:8010/api/docs

# frontend
cd frontend && npm ci && npm run serve          # http://127.0.0.1:5173 (npm run dev while editing UI code)

# local AI (one-time setup, then start each session)
powershell -File infrastructure\scripts\setup-ai.ps1   # or ./infrastructure/scripts/setup-ai.sh
powershell -File infrastructure\scripts\start-ai.ps1
```

No models yet? Run the backend in lightweight mode with test stand-ins. See
[installation](docs/user-guide/installation.md).

## Stack

React 19 · Vite 8 · TypeScript 7 · Tailwind 4 · shadcn/ui · Motion · Zustand · TanStack Query ·
React Hook Form + Zod — FastAPI · Pydantic 2 · SQLAlchemy 2.1 · Alembic · PostgreSQL/SQLite — Ollama
(Qwen 3.5) · OpenVINO GenAI (LCM Dreamshaper v7 + TAESD; ComfyUI optional) · Kokoro-82M · faster-whisper — NumPy · OpenCV ·
Pillow · SciPy · FFmpeg.

## Repository layout

```
backend/            FastAPI app: api/ core/ domain/ application/ infrastructure/ media/ workers/, tests/, alembic/
frontend/           React SPA: src/app, src/features/*, src/components, src/services; tests/unit, tests/e2e
ai-engine/tts-worker/   Isolated Kokoro TTS process (GPL-3.0 because of espeak-ng)
infrastructure/     setup/start scripts, Dockerfiles, Supabase RLS policies
docs/               research, architecture, database, security, API, user guides, PROJECT_STATUS.md
```

## Documentation

* Research: [competitors](docs/research/competitor-analysis.md), [feature matrix](docs/research/feature-comparison.md),
  [opportunities](docs/research/product-opportunities.md), [positioning](docs/research/market-positioning.md),
  [technology](docs/research/technology-evaluation.md), [AI models](docs/research/ai-model-comparison.md),
  [licence audit](docs/research/license-audit.md), [free infrastructure](docs/research/free-infrastructure.md)
* [System architecture](docs/architecture/system-architecture.md) · [Generation pipeline](docs/architecture/generation-pipeline.md)
* [Database schema](docs/database/schema.md) · [API](docs/api/README.md)
* [Security architecture](docs/security/security-architecture.md) · [Threat model](docs/security/threat-model.md)
* [Installation](docs/user-guide/installation.md) · [Deployment](docs/user-guide/deployment.md)
* [Project status](docs/PROJECT_STATUS.md)

## Licences

NaRRAVO's own code is MIT-licensed (see `LICENSE`). Third-party components keep their licences, listed in
`THIRD_PARTY_NOTICES.md`. Pay particular attention to the CreativeML OpenRAIL-M use restrictions that apply
to images generated with Stable Diffusion 1.5 and models derived from it (including the default LCM
Dreamshaper v7).
