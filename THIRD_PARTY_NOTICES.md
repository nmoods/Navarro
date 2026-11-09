# Third-party notices

ReelForge AI bundles or downloads the following components. Full verdicts and sources are in
`docs/research/license-audit.md`.

| Component | Licence | How it is used | Obligations |
|---|---|---|---|
| Kokoro-82M weights and voices | Apache-2.0 | downloaded at setup | keep the NOTICE/licence |
| kokoro-onnx, phonemizer, espeak-ng (via espeakng-loader) | MIT, GPL-3.0, GPL-3.0 | **isolated process** in `ai-engine/tts-worker` (licensed GPL-3.0-or-later) | provide the worker's source code (included) |
| Qwen 3.5 models | Apache-2.0 | pulled through Ollama | keep the licence |
| Ollama | MIT | separate binary | — |
| ComfyUI | GPL-3.0 | separate process over HTTP, not distributed in this repo | if you redistribute ComfyUI, comply with GPL-3.0 |
| Stable Diffusion 1.5 | CreativeML OpenRAIL-M | weights downloaded at setup | **Use restrictions (Attachment A) must be passed on to users**; include a licence copy; no harmful uses |
| LCM-LoRA SD1.5 | OpenRAIL++-M | weights downloaded at setup | same flow-down |
| faster-whisper, CTranslate2 | MIT | in-process | — |
| Whisper weights | MIT | downloaded on first use | — |
| FFmpeg (imageio-ffmpeg build or system ffmpeg) | LGPL/GPL depending on build | subprocess | if you distribute binaries, comply with their licence |
| OpenCV | Apache-2.0 | library | — |
| Pillow | MIT-CMU (HPND) | library | — |
| NumPy, SciPy | BSD-3-Clause | library | — |
| soundfile / libsndfile | BSD-3-Clause / LGPL-2.1 | library | — |
| FastAPI, Pydantic, SQLAlchemy, Alembic | MIT | library | — |
| React, Vite, Tailwind CSS, Zustand, TanStack Query, Motion, Zod, React Hook Form, Radix UI, shadcn/ui, Lucide, Sonner | MIT / ISC | frontend | — |
| Bricolage Grotesque, IBM Plex Sans (Fontsource) | SIL OFL 1.1 | UI fonts | keep the licence |
| Anton, Bebas Neue, Archivo Black, Montserrat, Inter, Playfair Display, Oswald, UnifrakturMaguntia | SIL OFL 1.1 | caption/visual fonts in `backend/app/media/assets/fonts` | keep `OFL.txt` |
| Special Elite | Apache-2.0 | caption font | — |
| Natural Earth 1:110m vectors | Public domain | maps and offline geocoding | none (attribution appreciated) |
| Wikipedia content | CC BY-SA 4.0 | short excerpts used for fact-checking; links shown to users | attribute with links (done in the UI) |

Music and sound effects are generated procedurally by ReelForge and are not third-party works.
