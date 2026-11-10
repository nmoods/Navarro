# NaRRAVO — Technology Evaluation (Phase Zero)

- Research date: 2026-11-09
- Baseline hardware: Windows 11, Intel i7-10700 (8C/16T, AVX2, no AVX-512/VNNI), 32 GB DDR4, Intel UHD 630 iGPU, **no CUDA GPU**, no Docker, system Python 3.15.2, Node 24.20.0
- Method: version numbers and wheel availability were pulled live from the PyPI JSON API (`https://pypi.org/pypi/<pkg>/json`) and the npm registry (`https://registry.npmjs.org/<pkg>`) on 2026-11-09. Anything not verified against a primary source is marked **UNVERIFIED**.

Related documents: [ai-model-comparison.md](./ai-model-comparison.md), [license-audit.md](./license-audit.md), [free-infrastructure.md](./free-infrastructure.md).

---

## 1. Python version decision (critical)

### 1.1 What the system interpreter (3.15.2) can and cannot install

Windows x64 wheel tags found on PyPI for the latest release of each package (2026-11-09):

| Package | Latest | Released | win_amd64 wheels | Requires-Python | Works on 3.15? |
|---|---|---|---|---|---|
| ctranslate2 | 4.8.5 | 2026-11-02 | cp39–cp315 | — | Yes |
| **onnxruntime** | 1.31.1 | 2026-10-26 | cp311, cp312, cp313, cp314 | >=3.11 | **No — no cp315 wheel** |
| numpy | 2.5.4 | 2026-10-10 | cp312–cp315 | >=3.12 | Yes |
| opencv-python-headless | 5.0.0.93 | 2026-07-02 | cp37-abi3 | — | Yes (stable ABI) |
| torch | 2.15.0 | 2026-10-28 | cp311–cp315 | — | Yes |
| pydantic-core | 2.50.4 | 2026-11-05 | cp310–cp315 | — | Yes |
| av (PyAV, used by faster-whisper) | 19.0.2 | 2026-10-21 | cp312-abi3 (+cp314t) | >=3.12 | Yes (stable ABI) |
| tokenizers | 0.23.3 | 2026-10-09 | cp310-abi3 | >=3.10 | Yes |
| openvino | 2026.4.1 | 2026-10-01 | cp310–cp314 | >=3.10 | **No** |
| openvino-genai | 2026.4.1.0 | 2026-10-01 | cp310–cp314 | >=3.10 | **No** |
| onnxruntime-openvino | 1.24.1 | 2026-02-26 | cp311–cp313 | >=3.10 | **No** |
| pillow | 13.0.0 | 2026-10-16 | cp311–cp315 | >=3.11 | Yes |
| psycopg-binary | 3.3.8 | 2026-11-04 | cp310–cp315 | >=3.10 | Yes |
| greenlet | 3.5.6 | 2026-09-14 | cp310–cp315 | >=3.10 | Yes |
| spacy (misaki[en] dep) | 3.8.18 | 2026-10-26 | cp310–cp315 | <3.16 | Yes |
| **kokoro-onnx** | 0.6.1 | 2026-08-19 | pure | **>=3.10, <3.14** | **No (metadata blocks it)** |
| **kokoro** (PyTorch) | 0.9.4 | 2025-04-05 | pure | **>=3.10, <3.13** | **No** |
| **misaki** (Kokoro G2P) | 0.9.4 | 2025-04-05 | pure | **>=3.8, <3.13** | **No** |
| faster-whisper | 1.2.1 | 2025-10-31 | pure | >=3.9 | Blocked transitively by `onnxruntime` (hard dependency, used for Silero VAD) |

Sources: PyPI JSON API for each package, e.g. https://pypi.org/project/onnxruntime/#files, https://pypi.org/project/kokoro-onnx/, https://pypi.org/project/kokoro/, https://pypi.org/project/misaki/, https://pypi.org/project/faster-whisper/ (requires_dist lists `onnxruntime<2,>=1.14`, `ctranslate2<5,>=4.0`, `av>=11`).

**Conclusion:** Python 3.15 is **not usable** for the AI worker: `onnxruntime`, which both `faster-whisper` and `kokoro-onnx` need, has no cp315 wheel. Kokoro's packages also cap Python below 3.13 or 3.14. Python 3.14 is blocked by `kokoro-onnx` (<3.14). Python 3.13 works for `kokoro-onnx`, but not for `kokoro`/`misaki`, which are needed for the best English G2P.

### 1.2 Recommendation

| Component | Python | Why |
|---|---|---|
| **AI worker** (TTS, STT, image, renderer) | **CPython 3.12.16** | The only minor version where *every* candidate installs: kokoro + misaki (<3.13), kokoro-onnx, onnxruntime, onnxruntime-openvino (cp311–313), openvino/openvino-genai, ctranslate2, torch, numpy 2.5 (>=3.12). |
| **API** (FastAPI) | **CPython 3.12.16** (same) | One interpreter, one lockfile tool, so dev and CI behave the same. The API alone could run 3.13/3.14, but standardising avoids two toolchains. |
| Upgrade target | 3.13 | Move once `misaki`/`kokoro` lift their `<3.13` cap. Track https://github.com/hexgrad/misaki (last push 2025-08-11, so possibly stale). |

- Python 3.12 is in **security-only** status until **2028-10** (https://peps.python.org/api/release-cycle.json; PEP 693). python.org **does not publish Windows installers** for security-only releases. The 3.12.16 FTP directory only contains `Python-3.12.16.tgz` (https://www.python.org/ftp/python/3.12.16/).
- **Install via `uv`** (latest 0.13.7 on PyPI). `uv python install 3.12` uses python-build-standalone, whose release `20261026` ships 3.12.16, 3.13.18, 3.14.10 and 3.15.2 (https://github.com/astral-sh/python-build-standalone/releases). Keep the 3.15.2 system interpreter untouched and pin the project with `.python-version` = `3.12` plus `requires-python = ">=3.12,<3.13"`.
- No Docker is needed. `uv venv` and `uv sync` give a reproducible environment from `uv.lock`.

---

## 2. Version pins (latest stable on 2026-11-09)

### 2.1 Frontend (npm registry, `dist-tags.latest`)

| Package | Pin | Released | License | Notes |
|---|---|---|---|---|
| react / react-dom | **19.3.1** | 2026-10-14 | MIT | |
| vite | **8.3.6** | 2026-11-05 | MIT | Engines: Node `^20.19.0 \|\| >=22.12.0`, so Node 24.20 is OK |
| @vitejs/plugin-react | **6.3.0** | — | MIT | Peer `vite ^8.0.0` |
| typescript | **6.0.3** (not 7.0.2) | 2026-04-16 | Apache-2.0 | `latest` is 7.0.2 (2026-07-08, native Go compiler), but **typescript-eslint 8.72.1 has peer `typescript >=4.8.4 <6.1.0`**. Pin 6.0.3 while using typed ESLint. Re-evaluate when typescript-eslint supports 7.x. |
| tailwindcss / @tailwindcss/vite | **4.3.5** | 2026-11-06 | MIT | v4 CSS-first config |
| shadcn (CLI) | **4.23.0** | 2026-10-27 | MIT | Engines Node >=20.18.1. The CLI generates components for Tailwind v4 and React 19 (uses `tw-animate-css` 1.4.0 instead of `tailwindcss-animate`). Docs: https://ui.shadcn.com/docs/tailwind-v4. shadcn/ui is copy-in source, not a runtime dependency. |
| motion (formerly framer-motion) | **14.10.1** | 2026-11-06 | MIT | `framer-motion` 14.10.1 is published in lockstep. Use the `motion` package, imported as `motion/react`. |
| zustand | **5.1.0** | 2026-11-06 | MIT | |
| @tanstack/react-query | **5.107.1** | 2026-11-06 | MIT | |
| react-hook-form | **7.91.0** | 2026-10-23 | MIT | |
| @hookform/resolvers | **7.0.5** | — | MIT | Peer `zod ^3.25 \|\| ^4` |
| zod | **4.6.7** | 2026-10-12 | MIT | |
| vitest | **5.1.0** | 2026-11-02 | MIT | Peer `vite ^6.4 \|\| ^7 \|\| ^8` |
| @playwright/test | **1.65.0** | 2026-11-05 | Apache-2.0 | |
| @supabase/supabase-js | **2.119.0** | — | MIT | Engines Node >=22 |
| Motion Canvas (`@motion-canvas/core`, `2d`, `ui`, `vite-plugin`, `ffmpeg`) | 3.17.2 (latest), 3.18.0-alpha.0 | **2024-12-14** (alpha 2025-02-16) | MIT | **Not recommended**, see section 3 |
| Revideo (`@revideo/core`, `renderer`, `cli`) | 0.11.0 | 2026-07-10 | MIT | Alternative, see section 3 |
| Remotion (`remotion`, `@remotion/renderer`) | 4.0.541 | 2026-11-05 | Remotion License (source-available) | **Rejected**, see section 3 and the license audit |

### 2.2 Backend / AI worker (PyPI)

| Package | Pin | Released | License | cp312 win_amd64 | Notes |
|---|---|---|---|---|---|
| fastapi | **0.162.2** | 2026-11-07 | MIT | pure | |
| uvicorn | 0.54.0 | 2026-09-25 | BSD-3-Clause | pure | |
| pydantic | **2.14.3** | 2026-11-05 | MIT | pure | pydantic-core **2.50.4** (cp312 wheel ✓) |
| sqlalchemy | **2.1.8** | — | MIT | ✓ | Requires-Python >=3.11 |
| alembic | **1.20.1** | 2026-10-22 | MIT | pure | |
| psycopg + psycopg-binary | **3.3.8** | 2026-11-04 | LGPL-3.0-only | ✓ | LGPL with dynamic use is fine. Unmodified use carries no copyleft on our code. |
| pytest | **9.2.0** | 2026-10-27 | MIT | pure | |
| pillow | **13.0.0** | 2026-10-16 | MIT-CMU | ✓ | Requires-Python >=3.11 |
| opencv-python-headless | **5.0.0.93** | 2026-07-02 | Apache-2.0 (wheel bundles LGPL FFmpeg) | abi3 ✓ | OpenCV 5.x is a major bump, so pin exactly and smoke-test `cv2` APIs used |
| numpy | **2.5.4** | 2026-10-10 | BSD-3-Clause | ✓ | Requires-Python >=3.12 |
| faster-whisper | **1.2.1** | 2025-10-31 | MIT | pure | GitHub repo active (push 2026-11-06), no PyPI release in 12 months |
| ctranslate2 | **4.8.5** | 2026-11-02 | MIT | ✓ | faster-whisper requires `<5` |
| onnxruntime | **1.31.1** | 2026-10-26 | MIT | ✓ | |
| kokoro-onnx | **0.6.1** | 2026-08-19 | MIT | pure | Requires-Python <3.14. Pulls `phonemizer` (**GPL-3.0**) and `espeakng-loader` (MIT wrapper bundling **GPL-3.0** espeak-ng). See the license audit. |
| kokoro (PyTorch, optional) | 0.9.4 | 2025-04-05 | Apache-2.0 | pure | Requires-Python <3.13, needs torch |
| misaki[en] (optional G2P) | 0.9.4 | 2025-04-05 | Apache-2.0 | pure | Requires-Python <3.13. Pulls `phonemizer-fork` (GPL-3.0), espeakng-loader and spacy |
| imageio-ffmpeg | **0.8.1** | 2026-11-03 | BSD-2-Clause (wrapper) | py3 win wheel | Bundled Windows binary = **FFmpeg 9.0.2 gyan.dev "essentials" build (GPL-3)**, per `tools/ffmpeg-sources.json` |
| av (PyAV) | 19.0.2 | 2026-10-21 | BSD-3-Clause (bundles LGPL FFmpeg) | abi3 ✓ | Required by faster-whisper |
| openvino | 2026.4.1 | 2026-10-01 | Apache-2.0 | ✓ | CPU and Intel iGPU inference |
| openvino-genai | 2026.4.1.0 | 2026-10-01 | Apache-2.0 | ✓ | Text2Image, Whisper and Kokoro pipelines |
| optimum-intel | 2.2.0 | 2026-09-17 | Apache-2.0 | pure | Exports HF models to OpenVINO IR |
| diffusers | 0.42.1 | 2026-10-27 | Apache-2.0 | pure | Requires-Python >=3.11 |
| transformers | 5.22.2 | 2026-11-06 | Apache-2.0 | pure | |
| torch (only if needed) | 2.15.0 | 2026-10-28 | BSD-3-Clause | ✓ | CPU wheel. Avoid if the OpenVINO/ONNX path suffices (saves ~1 GB+). |
| ollama (Python client) | 0.6.3 | 2026-09-29 | MIT | pure | |
| huggingface-hub | 2.4.0 | 2026-10-29 | Apache-2.0 | pure | |
| moviepy | 2.2.1 | 2025-05-21 | MIT | pure | Not chosen as renderer, see section 3 |

### 2.3 Native tools / services

| Tool | Version | Source | License | Notes |
|---|---|---|---|---|
| Ollama | **v0.40.15** (2026-11-03) | https://github.com/ollama/ollama/releases | MIT | **Portable `ollama-windows-amd64.zip` is published** alongside rocm, mlx and arm64 zips. It can run without the installer: `ollama serve`. |
| ComfyUI | v0.44.0 (2026-11-04) | https://github.com/Comfy-Org/ComfyUI (moved from comfyanonymous/) | GPL-3.0 | Optional GPU path only, see the AI model comparison |
| CTranslate2 | v4.8.5 (2026-11-02) | https://github.com/OpenNMT/CTranslate2 | MIT | |
| FFmpeg | 9.0.x | https://ffmpeg.org/legal.html | LGPL-2.1+ / GPL with x264 | See the license audit |

---

## 3. Renderer evaluation (section B)

Requirement: a **server-side, deterministic, headless** renderer running in a Python worker on Windows without a GPU. It must take storyboard JSON, images, a TTS WAV and word timestamps, and produce a 1080x1920 MP4 with animated subtitles (Ken Burns/pan-zoom, transitions, karaoke-style word highlights).

### 3.1 Motion Canvas

- **Maintenance:** last stable `@motion-canvas/*` **3.17.2 on 2024-12-14**. Last pre-release 3.18.0-alpha.0 on 2025-02-16. Last commit on `main` was 2026-07-02 (a docs-domain refactor); before that 2025-02-16. Repo not archived, about 19.7k stars, 153 open issues. Sources: npm registry; https://api.github.com/repos/motion-canvas/motion-canvas/releases; https://github.com/motion-canvas/motion-canvas
- **Headless rendering:** the documented render path is the editor's **RENDER button**. It plays the scene in the browser editor and writes `/output` (https://motioncanvas.io/docs/rendering). The README describes the project as "a TypeScript library ... and an editor providing a real-time preview". We found **no official CLI or Node API for headless rendering**. Community tooling still drives a browser with the editor open. Headless use means scripting Puppeteer against the Vite dev server, which is fragile.
- **Verdict:** **Not suitable** as a server-side renderer. It is effectively unmaintained for releases (about 23 months without a stable release) and has no supported headless path.

### 3.2 Revideo (Motion Canvas fork)

- Repo moved: `redotvideo/revideo` now redirects to **https://github.com/midrender/revideo** (MIT, about 4.2k stars, last push 2026-07-15, not archived). npm `@revideo/*` **0.11.0 on 2026-07-10**. Docs moved to https://midrender.com/revideo/docs (renderVideo(), renderPartialVideo(), FFmpegExporterClient and WasmExporter references).
- Headless: the README says scenes are rendered "from the command line with `renderVideo()`", with a rendering endpoint via the CLI, parallel rendering across workers, and deployment on Cloud Run. It renders through headless Chromium plus FFmpeg. Internals were not fully verified on the current docs: **UNVERIFIED**.
- Risks: it is maintained by a commercial company (Midrender, which sells a hosted product). Release cadence is about 4 months since the last release. It adds a Node + Chromium runtime (about 150–300 MB) to the worker, and browser canvas rendering is not bit-exact across Chromium versions.
- **Verdict:** a viable **secondary** option if the team later wants TypeScript-authored motion-graphics templates. License is MIT and **APPROVED**.

### 3.3 Remotion

- License: Remotion License, not OSI (https://github.com/remotion-dev/remotion/blob/main/LICENSE.md). It is free only for individuals, non-profits, evaluation, and for-profit organisations of **up to 3 employees**. A **Company License** is required for 4+ people (https://www.remotion.pro/license).
- Automated/server rendering is priced as "**Remotion for Automators: $0.01 per render, $100/month minimum**" and is explicitly aimed at "prompt-to-video apps" (https://www.remotion.pro/license). The license also says it "will slightly change" in Remotion 5.0.
- **Verdict: REJECTED.** NaRRAVO is open source and will be self-hosted by unknown organisations. Any operator with more than 3 employees would owe Remotion fees, and the project's no-billing/no-paid-API principle is violated. The technology itself is excellent and actively maintained (4.0.541 released 2026-11-05).

### 3.4 MoviePy 2.x

- 2.2.1 (2025-05-21), MIT, repo active (push 2026-08-26). It decodes and encodes through an FFmpeg binary (imageio-ffmpeg) and composites per frame in NumPy.
- Pros: Pythonic, MIT. Cons: v2 broke the v1 API, per-frame Python compositing is slow at 1080x1920, text rendering goes through Pillow with limited typography, and there have been no releases for about 18 months.
- **Verdict:** acceptable for prototyping. Not chosen as the core renderer, because we would end up bypassing most of it.

### 3.5 Python-native compositor (NumPy + OpenCV + Pillow, piped to FFmpeg) — **RECOMMENDED**

Design (no code here, only the approach):
1. A pure-function frame model, `frame(t) -> RGB ndarray`, computed from the storyboard JSON, the timestamps and a fixed seed. No wall-clock time and no randomness without a seed.
2. Images are pre-scaled once. Ken Burns, crop and transform use `cv2.warpAffine` with fixed interpolation. Transitions are alpha blends in float32, then quantised.
3. Subtitles are rendered with **Pillow `ImageFont`/`ImageDraw` using bundled OFL fonts** (for example Inter or Montserrat). Glyph rasters are cached per word or state, and word-level highlight timing comes from faster-whisper `word_timestamps` (or Kokoro token durations).
4. Raw frames are streamed to the FFmpeg stdin pipe (`-f rawvideo -pix_fmt rgb24`). Audio is muxed from the TTS WAV plus music. The FFmpeg binary path is configurable: the imageio-ffmpeg bundled binary or a system FFmpeg.
5. Determinism: pin FFmpeg, Pillow, OpenCV and font versions. Use `-threads` plus a fixed encoder preset, `-x264-params` deterministic settings, and `-fflags +bitexact`. Snapshot tests hash selected PNG frames rather than the MP4 (encoder output can vary across builds).

Why: everything stays in the Python worker. There is no browser, no Node runtime in the worker and no license fees. It is CPU-efficient: a 1080x1920 frame composite is a few ms in OpenCV, and libx264 `veryfast` on 8 cores encodes faster than real time (**estimate**). It is testable frame by frame and works identically on Windows and Linux. Licenses: OpenCV Apache-2.0, Pillow MIT-CMU, NumPy BSD-3. FFmpeg is invoked as a **separate process**, which keeps GPL/LGPL obligations limited to distributing the binary.

| Criterion | Python compositor | Revideo | Motion Canvas | Remotion | MoviePy 2.x |
|---|---|---|---|---|---|
| Headless on server | ✅ native | ✅ `renderVideo()` (headless Chromium) | ❌ editor button only | ✅ | ✅ |
| Deterministic | ✅ (pinned libs) | ⚠️ browser canvas varies | ⚠️ | ⚠️ | ✅ |
| Extra runtime | none | Node + Chromium | Node + browser | Node + Chromium | none |
| Last release | n/a (our code) | 2026-07-10 | 2024-12-14 | 2026-11-05 | 2025-05-21 |
| License | Apache/MIT/BSD | MIT | MIT | **Company license for 4+ employees, $0.01/render automators** | MIT |
| Verdict | **Primary** | Optional later | Rejected (tech) | **Rejected (license)** | Prototype only |

**Recommendation:** build a **Python-native compositor** (NumPy/OpenCV/Pillow to the FFmpeg pipe) as the single production renderer. Keep a `Renderer` interface so a Revideo adapter could be added later for TypeScript-authored templates.

---

## 4. Other architecture-relevant findings

- **Ollama structured output:** `format` accepts `"json"` or a **JSON Schema** object. Python examples pass `Model.model_json_schema()` (Pydantic), and JS examples use `z.toJSONSchema()` (Zod). Docs advise also putting the schema in the prompt and using `temperature: 0`. **Ollama Cloud does not support structured outputs** (local only), which suits us. Source: https://docs.ollama.com/capabilities/structured-outputs. Behaviour of `format` combined with "thinking" models: **UNVERIFIED**. Disable thinking (`think: false`) for storyboard calls.
- **OpenVINO GenAI** (Apache-2.0) has native pipelines for Stable Diffusion/LCM/SDXL/SD3/Flux/FLUX.2 [klein]/Z-Image (images), Whisper (STT) and **Kokoro-82M** (TTS). These can run on the i7 CPU **and the UHD 630 iGPU** (https://openvinotoolkit.github.io/openvino.genai/docs/supported-models/). This is the best CPU-acceleration path for our hardware and avoids ComfyUI's GPL and PyTorch CPU slowness.
- **Supabase JWTs:** verify with the asymmetric JWKS at `https://<project>.supabase.co/auth/v1/.well-known/jwks.json` (ES256 recommended). The legacy HS256 secret is "no longer recommended". Details are in [free-infrastructure.md §6](./free-infrastructure.md#6-supabase-auth-jwt-verification-from-fastapi-and-rls-coexistence-section-f).

---

## 5. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Kokoro/misaki stay capped below 3.13 and drift from upstream (misaki last push 2025-08) | High | Medium | Pin 3.12. Run Kokoro via kokoro-onnx or OpenVINO GenAI (Kokoro supported). Vendor a lexicon. |
| R2 | GPL-3 espeak-ng/phonemizer imported in-process in the TTS worker | Certain (if used) | Medium (distribution obligations) | Isolate the TTS worker as a separately licensed component, or call the `espeak-ng` CLI as a subprocess. See the license audit. |
| R3 | Bundled FFmpeg is a GPL build (x264) | Certain | Low for SaaS, Medium for binary redistribution | Ship as a separate executable with GPL notice and source link, or let users supply FFmpeg. |
| R4 | CPU-only image generation too slow or low quality | Medium | High (UX) | Default to SD1.5-LCM on OpenVINO at 512x896, with optional FLUX.2-klein-4B "quality" mode and an optional GPU/ComfyUI adapter. |
| R5 | Python 3.12 is security-only (no python.org Windows installers) | Certain | Low | Use uv / python-build-standalone. Plan the 3.13 migration. |
| R6 | TypeScript 7 incompatible with typescript-eslint | Certain today | Low | Pin TS 6.0.3. Revisit quarterly. |
| R7 | OpenCV 5.0 is a new major version | Medium | Low | Pin 5.0.0.93 and keep cv2 usage to stable APIs (warpAffine, resize, cvtColor). |
| R8 | RAM contention: LLM (3–7 GB) + image model (2–8 GB) + Whisper + Kokoro on 32 GB | Medium | Medium | Run pipeline stages **sequentially** in one worker. Unload Ollama models (`keep_alive: 0`) before image generation. |
| R9 | faster-whisper PyPI release stale (1.2.1, 2025-10) | Low | Low | Repo active. Pin and watch. Alternative: OpenVINO GenAI WhisperPipeline. |
| R10 | Revideo/Midrender commercial pivot | Medium | Low (not on critical path) | Not a dependency in v1. |
