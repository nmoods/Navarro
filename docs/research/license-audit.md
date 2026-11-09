# ReelForge AI — License Audit

- Audit date: 2026-11-09. This is an engineering audit, **not legal advice**. Items marked **UNVERIFIED** need confirmation.
- Assumed distribution model: ReelForge source is published as **open source** (proposed: MIT or Apache-2.0) and may be **self-hosted as SaaS** by third parties. Models are **downloaded at install time**, not committed to the repo.
- Verdicts:
  - **APPROVED**: use freely, standard notices.
  - **APPROVED WITH CONDITIONS**: use, with listed obligations enforced in code and docs.
  - **OPT-IN ONLY**: never bundled or default. The user must download it and acknowledge the license.
  - **REJECTED**: do not use. An alternative is given.

## 0. Key flags (explicitly requested)

| Item | Finding | Verdict |
|---|---|---|
| **Remotion** | Remotion License (source-available). Free only for individuals, non-profits and companies of **≤3 employees**. 4+ need a Company License. Automated rendering costs **$0.01/render, $100/month minimum** ("Remotion for Automators", aimed at "prompt-to-video apps"). It is not OSI open source. Sources: https://github.com/remotion-dev/remotion/blob/main/LICENSE.md, https://www.remotion.pro/license | **REJECTED**. Use the Python compositor (or Revideo, MIT). |
| **SDXL-Turbo** | LICENSE.md is now the **Stability AI Community License** (updated 2024-07-05). Commercial use is allowed only if annual revenue is **< US$1M**, with **registration** at stability.ai/community-license. It is revocable, and redistributors must include the "This Stability AI Model is licensed under the Stability AI Community License" notice. The HF tag still says `sai-nc-community`, which is inconsistent. Sources: https://huggingface.co/stabilityai/sdxl-turbo/blob/main/LICENSE.md, https://stability.ai/license | **OPT-IN ONLY**. Not non-commercial as assumed, but the revenue cap and registration fall on each operator. |
| **FLUX.1-dev** | FLUX.1 [dev] **Non-Commercial License** (https://huggingface.co/black-forest-labs/FLUX.1-dev). This also taints derivatives (for example Freepik/flux.1-lite-8B, Hyper-SD FLUX LoRAs). | **REJECTED**. Use FLUX.1-schnell (Apache-2.0, GPU only) or FLUX.2-klein-4B (Apache-2.0). |
| **XTTS-v2** | Coqui Public Model License: "allows only non-commercial use of a machine learning model **and its outputs**" (https://huggingface.co/coqui/XTTS-v2, LICENSE.txt). Licensor defunct, so no commercial license is obtainable. | **REJECTED**. Use Kokoro-82M. |
| **F5-TTS** | Code MIT, but **pre-trained weights CC-BY-NC-4.0** "due to the training data Emilia" (https://github.com/SWivid/F5-TTS, https://huggingface.co/SWivid/F5-TTS) | **REJECTED**. Use Kokoro-82M. |
| **Llama 3.x license** | Llama 3.2 Community License: must show "**Built with Llama**", ship a copy of the agreement, and name derived models "Llama…". A separate license is needed above **700M MAU**. AUP applies, with no trademark rights beyond that. 3.2 vision models carry an EU restriction (**UNVERIFIED** for text models). Source: https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/LICENSE | **OPT-IN ONLY**. Not in the default allow-list. Use Qwen3.5 / Ministral 3 / Gemma 4 (Apache-2.0). |
| **Qwen exceptions** | Qwen3 / Qwen3.5 / Qwen3.6 / Qwen3.8-27B: **Apache-2.0**. Qwen2.5: Apache-2.0 **except 3B** (**Qwen RESEARCH License**, "FOR NON-COMMERCIAL PURPOSES ONLY") **and 72B** (**Qwen License**: request a license above **100M MAU**; "Built with Qwen" if outputs are used to train a distributed model). Also non-Apache: Qwen3.8-Flash-Next and Qwen3.8-2.4T (license "other"), Qwen-Image-2.x ("other"). Sources: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE, https://huggingface.co/Qwen/Qwen2.5-72B-Instruct/blob/main/LICENSE, HF API license tags | Qwen3/3.5 **APPROVED**. **qwen2.5:3b REJECTED**. qwen2.5:72b conditional (irrelevant on CPU). |
| **espeak-ng (GPL-3)** | espeak-ng is **GPL-3.0** (https://github.com/espeak-ng/espeak-ng). It enters the TTS path through `espeakng-loader` (MIT wrapper that **bundles the espeak-ng library**), `phonemizer` / `phonemizer-fork` (**GPL-3.0**, Python library imported in-process), and `misaki[en]` (uses espeak only as an out-of-vocabulary fallback). See §3. | **APPROVED WITH CONDITIONS**: isolate the TTS worker (see §3) |
| **ComfyUI (GPL-3)** | https://github.com/Comfy-Org/ComfyUI is **GPL-3.0** (the frontend is also GPL-3.0). Calling an **unmodified ComfyUI running as a separate process over HTTP/WebSocket** is communication between separate programs ("aggregate"), so the copyleft does not extend to ReelForge. It **would** apply if we import ComfyUI Python modules, ship modified ComfyUI, or write custom nodes (custom nodes load in-process, so they must be GPL-compatible). GPL-3 (not AGPL) has no network-use clause. | **APPROVED WITH CONDITIONS**: optional external backend only. Never vendored. Any ReelForge custom nodes go in a separate GPL-3 repo. |
| **x264 (GPL)** | libx264 is GPL-2.0+. An FFmpeg build with `--enable-libx264` must use `--enable-gpl`, so the binary is GPL (https://ffmpeg.org/legal.html). imageio-ffmpeg 0.8.1 ships **FFmpeg 9.0.2 gyan.dev "essentials" (GPL-3) on Windows** and BtbN `-gpl` builds on Linux (`tools/ffmpeg-sources.json`). Running FFmpeg as a **subprocess** does not make our code a derivative work. Obligations arise only when we **distribute the binary** (GPL text plus corresponding source offer). SaaS use without distribution triggers no GPL obligation. Separately, H.264 is **patent-encumbered** (Via LA AVC pool). Royalty exposure for a free SaaS encoder is **UNVERIFIED** and needs legal review before commercial scale. | **APPROVED WITH CONDITIONS**. Do not commit FFmpeg binaries to git. When bundling (installer), ship the GPL notice and source link. Make the encoder configurable (libx264 / libopenh264 / libvpx-vp9 / libsvtav1). |

---

## 1. Master table: software dependencies

| Dependency | Version | License | Commercial | Redistribution | SaaS | Obligations | Verdict |
|---|---|---|---|---|---|---|---|
| React, React DOM | 19.3.1 | MIT | ✅ | ✅ | ✅ | Keep notice | APPROVED |
| Vite, @vitejs/plugin-react | 8.3.6 / 6.3.0 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| TypeScript | 6.0.3 | Apache-2.0 | ✅ | ✅ | ✅ | Notice, NOTICE file | APPROVED |
| Tailwind CSS | 4.3.5 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| shadcn/ui CLI and components | 4.23.0 | MIT | ✅ | ✅ | ✅ | Notice in copied components | APPROVED |
| motion | 14.10.1 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| zustand, @tanstack/react-query, react-hook-form, @hookform/resolvers, zod | see tech eval | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| vitest | 5.1.0 | MIT | ✅ | ✅ | ✅ | dev only | APPROVED |
| Playwright | 1.65.0 | Apache-2.0 | ✅ | ✅ | ✅ | dev only | APPROVED |
| @supabase/supabase-js | 2.119.0 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| Motion Canvas | 3.17.2 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED (license) but not used (technical: no headless path, stale) |
| Revideo | 0.11.0 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED (optional) |
| **Remotion** | 4.0.541 | Remotion License | ⚠️ ≤3 employees | ❌ no relicensing | ⚠️ paid automators | Company license | **REJECTED**, use Python compositor |
| FastAPI | 0.162.2 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| Uvicorn | 0.54.0 | BSD-3-Clause | ✅ | ✅ | ✅ | Notice | APPROVED |
| Pydantic / pydantic-core | 2.14.3 / 2.50.4 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| SQLAlchemy | 2.1.8 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| Alembic | 1.20.1 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| psycopg / psycopg-binary | 3.3.8 | **LGPL-3.0-only** | ✅ | ✅ (unmodified; binary wheel must keep LGPL notice and allow relinking) | ✅ | Ship LGPL text if bundled. No copyleft on our code when used unmodified. | APPROVED WITH CONDITIONS |
| pytest | 9.2.0 | MIT | ✅ | ✅ | ✅ | dev only | APPROVED |
| Pillow | 13.0.0 | MIT-CMU (HPND-style) | ✅ | ✅ | ✅ | Notice | APPROVED |
| opencv-python-headless | 5.0.0.93 | Apache-2.0 (wheel bundles LGPL FFmpeg) | ✅ | ✅ | ✅ | NOTICE. LGPL notice for bundled FFmpeg libs. | APPROVED |
| NumPy | 2.5.4 | BSD-3-Clause | ✅ | ✅ | ✅ | Notice | APPROVED |
| faster-whisper | 1.2.1 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| CTranslate2 | 4.8.5 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| onnxruntime | 1.31.1 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| PyAV (av) | 19.0.2 | BSD-3-Clause, bundles LGPL FFmpeg | ✅ | ✅ | ✅ | LGPL notice | APPROVED |
| kokoro-onnx | 0.6.1 | MIT | ✅ | ✅ | ✅ | Notice. **Pulls GPL deps (below).** | APPROVED WITH CONDITIONS |
| kokoro (PyTorch) | 0.9.4 | Apache-2.0 | ✅ | ✅ | ✅ | NOTICE | APPROVED |
| misaki | 0.9.4 | Apache-2.0 | ✅ | ✅ | ✅ | NOTICE. `[en]` extra pulls GPL deps. | APPROVED WITH CONDITIONS |
| **phonemizer / phonemizer-fork** | 3.3.x | **GPL-3.0** | ✅ | ✅ under GPL-3 | ✅ (GPL-3 has no network clause) | Combined distributed work must be GPL-3 compatible. Source plus license if distributed. | APPROVED WITH CONDITIONS (§3) |
| espeakng-loader | 0.2.4 | MIT wrapper, **bundles espeak-ng (GPL-3.0)** | ✅ | GPL-3 for bundled lib | ✅ | Same as above | APPROVED WITH CONDITIONS (§3) |
| **espeak-ng** | — | **GPL-3.0** | ✅ | ✅ under GPL-3 | ✅ | Same | APPROVED WITH CONDITIONS (§3) |
| spaCy (+ en_core_web_sm via misaki) | 3.8.18 | MIT (model `en_core_web_sm` MIT, **UNVERIFIED** for the current model version) | ✅ | ✅ | ✅ | Notice | APPROVED |
| piper-tts (OHF-Voice/piper1-gpl) | 1.8.0 | **GPL-3.0-or-later** | ✅ | GPL-3 | ✅ | Run as a separate process/CLI to avoid combining | APPROVED WITH CONDITIONS (fallback, subprocess only) |
| MeloTTS | — | MIT | ✅ | ✅ | ✅ | Notice | APPROVED (not default) |
| imageio-ffmpeg (wrapper) | 0.8.1 | BSD-2-Clause | ✅ | ✅ | ✅ | Notice | APPROVED |
| **FFmpeg binary bundled by imageio-ffmpeg** | 9.0.2 (gyan.dev essentials, Windows) | **GPL-3.0** (includes libx264 and others) | ✅ | Only with GPL compliance | ✅ | Ship license, offer source, never link in-process | APPROVED WITH CONDITIONS |
| FFmpeg, LGPL-only build (no x264) | — | LGPL-2.1+ | ✅ | ✅ | ✅ | LGPL notice. Use libopenh264 (BSD, Cisco binary) or VP9/AV1. | APPROVED (alternative) |
| MoviePy | 2.2.1 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED (prototype only) |
| OpenVINO / OpenVINO GenAI / optimum-intel | 2026.4.1 / 2.2.0 | Apache-2.0 | ✅ | ✅ | ✅ | NOTICE | APPROVED |
| diffusers / transformers / huggingface-hub | 0.42.1 / 5.22.2 / 2.4.0 | Apache-2.0 | ✅ | ✅ | ✅ | NOTICE | APPROVED |
| PyTorch | 2.15.0 | BSD-3-Clause | ✅ | ✅ | ✅ | Notice | APPROVED |
| Ollama | v0.40.15 | MIT (https://github.com/ollama/ollama) | ✅ | ✅ | ✅ | Notice (bundles llama.cpp, MIT) | APPROVED |
| ollama-python | 0.6.3 | MIT | ✅ | ✅ | ✅ | Notice | APPROVED |
| **ComfyUI** (+ frontend) | v0.44.0 | **GPL-3.0** | ✅ | GPL-3 | ✅ | Separate process only. No vendoring, no in-process import. | APPROVED WITH CONDITIONS (optional) |
| comfyui_openvino custom node | — | NOASSERTION on GitHub (**UNVERIFIED**) | ? | ? | ? | — | Not used until clarified |
| FastSD CPU (reference only) | — | MIT | ✅ | ✅ | ✅ | — | APPROVED as reference/benchmark |
| stable-diffusion.cpp | — | MIT | ✅ | ✅ | ✅ | Notice | APPROVED (watch-list) |
| uv (tooling) | 0.13.7 | MIT / Apache-2.0 | ✅ | ✅ | ✅ | dev tool | APPROVED |
| python-build-standalone CPython 3.12.16 | — | PSF-2.0 plus bundled libs (OpenSSL Apache-2.0, etc.) | ✅ | ✅ | ✅ | Notices | APPROVED |

## 2. Master table: AI models, voices, datasets

| Model / asset | License (weights) | Code license | Data provenance | Commercial | Redistribute weights | SaaS hosting | Obligations | Verdict / alternative |
|---|---|---|---|---|---|---|---|---|
| **Qwen3.5 (0.8B–35B-A3B, 122B, 397B)** | Apache-2.0 | Apache-2.0 | Not disclosed | ✅ | ✅ | ✅ | NOTICE | **APPROVED (default LLM `qwen3.5:4b`)** |
| Qwen3 (0.6B–235B) | Apache-2.0 | Apache-2.0 | — | ✅ | ✅ | ✅ | NOTICE | APPROVED |
| Qwen3.6-27B/35B-A3B, Qwen3.8-27B | Apache-2.0 | — | — | ✅ | ✅ | ✅ | NOTICE | APPROVED (too large for CPU) |
| Qwen3.8-Flash-Next, Qwen3.8-2.4T | "other" (**UNVERIFIED** terms) | — | — | ? | ? | ? | — | Not used |
| Qwen2.5 0.5/1.5/7/14/32B | Apache-2.0 | — | — | ✅ | ✅ | ✅ | NOTICE | APPROVED |
| **Qwen2.5-3B** | **Qwen Research License** (non-commercial) | — | — | ❌ | ❌ commercial | ❌ | — | **REJECTED**, use qwen3.5:4b |
| **Qwen2.5-72B** | Qwen License (100M MAU cap) | — | — | ⚠️ | ✅ | ✅ <100M MAU | "Built with Qwen" if training | APPROVED WITH CONDITIONS (not used) |
| **Llama 3.1 / 3.2 / 3.3** | Llama Community License | — | — | ⚠️ (700M MAU) | ✅ with license copy | ✅ | "Built with Llama", AUP, naming | **OPT-IN ONLY** |
| **Gemma 3 / 3n** | Gemma Terms of Use + Prohibited Use Policy | — | — | ✅ | ✅ with Notice file and flow-down of restrictions | ✅ | Must pass §3.2 use restrictions into user ToS. Google reserves the right to restrict usage. | **OPT-IN ONLY**, prefer Gemma 4 |
| Gemma 4 (E2B/E4B/12B/26B/31B) | **Apache-2.0** (https://ai.google.dev/gemma/docs/gemma_4_license) | — | — | ✅ | ✅ | ✅ | NOTICE | APPROVED (fallback LLM) |
| Ministral 3 (3B/8B/14B, 2512) | Apache-2.0 | — | — | ✅ | ✅ | ✅ | NOTICE | APPROVED (fallback LLM) |
| Ministral-8B-Instruct-2410 | **Mistral Research License (MRL)** | — | — | ❌ | ❌ | ❌ | — | **REJECTED**, use ministral-3:8b |
| Mistral-7B v0.3, Mistral-Small-3.2 | Apache-2.0 | — | — | ✅ | ✅ | ✅ | NOTICE | APPROVED |
| Phi-4-mini | MIT | — | — | ✅ | ✅ | ✅ | Notice | APPROVED |
| **Stable Diffusion 1.5** (stable-diffusion-v1-5 mirror) | **CreativeML OpenRAIL-M** | — | LAION-5B (known problematic content found in 2023; reputational risk) | ✅ | ✅ with license copy | ✅ | **Use restrictions (Attachment A) must be included as enforceable terms in our ToS and passed to users. Include a license copy. Derivatives carry the same restrictions.** | **APPROVED WITH CONDITIONS (default image)** |
| LCM-LoRA SD1.5 | OpenRAIL++ | — | — | ✅ | ✅ | ✅ | Same flow-down | APPROVED WITH CONDITIONS |
| LCM_Dreamshaper_v7 (+ OpenVINO int8 variant) | Tagged MIT, but **derivative of OpenRAIL-M weights** | — | — | ✅ | ✅ | ✅ | Treat as OpenRAIL-M | APPROVED WITH CONDITIONS |
| SDXS-512-0.9 | OpenRAIL++ | — | — | ✅ | ✅ | ✅ | Flow-down | APPROVED WITH CONDITIONS |
| SDXL base 1.0 / SDXL-Lightning | OpenRAIL++ | — | — | ✅ | ✅ | ✅ | Flow-down | APPROVED WITH CONDITIONS |
| Segmind SSD-1B / Vega | Tagged Apache-2.0, distilled from SDXL (OpenRAIL++) | — | — | ✅ | ✅ | ✅ | Treat as OpenRAIL++ | APPROVED WITH CONDITIONS |
| **SDXL-Turbo / SD-Turbo** | Stability AI Community License | — | — | ⚠️ <$1M revenue plus registration | ✅ with notice | ⚠️ | Registration, notice, AUP, revenue cap | **OPT-IN ONLY**. Default alternative: SD1.5-LCM / SDXL-Lightning. |
| SD 3.5 Medium / Large | Stability AI Community License | — | — | ⚠️ | ⚠️ | ⚠️ | Same | **OPT-IN ONLY** (also too slow on CPU) |
| **FLUX.1-schnell** | Apache-2.0 | Apache-2.0 | — | ✅ | ✅ | ✅ | NOTICE | APPROVED (GPU-only option) |
| **FLUX.1-dev** (+ derivatives) | FLUX.1-dev Non-Commercial | — | — | ❌ | ❌ | ❌ | — | **REJECTED**, use FLUX.2-klein-4B / FLUX.1-schnell |
| **FLUX.2 [klein] 4B** | Apache-2.0 | — | — | ✅ | ✅ | ✅ | NOTICE. BFL encourages content filters. | **APPROVED ("quality" mode)** |
| FLUX.2 [klein] 9B | Non-commercial ("other") | — | — | ❌ | ❌ | ❌ | — | **REJECTED**, use klein-4B |
| FLUX.3 Image Klein | FLUX Kommunity License (<US$5M revenue, filters/review required) | — | — | ⚠️ | ⚠️ | ⚠️ | Attribution, filters, AI disclosure | **OPT-IN ONLY** |
| Z-Image-Turbo | Apache-2.0 | — | — | ✅ | ✅ | ✅ | NOTICE | APPROVED (GPU option) |
| PixArt-Σ | OpenRAIL++ (+ T5 Apache-2.0) | — | — | ✅ | ✅ | ✅ | Flow-down | APPROVED WITH CONDITIONS (not default) |
| **Sana / Sana-Sprint** | Tagged Apache-2.0, but card says "research purposes only". Text encoder **Gemma-2-2B (Gemma Terms)**. | — | — | ⚠️ contradictory | ⚠️ | ⚠️ | — | **REJECTED until clarified**, use FLUX.2-klein-4B |
| HiDream-I1-Fast | MIT | — | — | ✅ | ✅ | ✅ | Notice. Note: uses Llama-3.1-8B as text encoder (Llama license applies, **UNVERIFIED**). | Not used (GPU-only) |
| TAESD / TAESDXL | MIT | MIT | — | ✅ | ✅ | ✅ | Notice | APPROVED |
| **Kokoro-82M v1.0 (+ 54 voice packs)** | Apache-2.0 (weights and voices in the same repo) | Apache-2.0 / kokoro-onnx MIT | Public domain, Apache/MIT audio, **synthetic audio from closed commercial TTS providers**, Koniwa **CC BY 3.0**, SIWIS **CC BY 4.0** | ✅ | ✅ | ✅ | NOTICE. Credit Koniwa/SIWIS in the attributions page (prudent; required only if those voices or derived data are redistributed, **UNVERIFIED**). **Residual provenance risk:** training on closed-TTS outputs may breach those providers' ToS. That risk sits with the model author, not us, but monitor it. | **APPROVED WITH CONDITIONS (default TTS)** |
| Piper engine (piper1-gpl) | — | GPL-3.0-or-later | — | ✅ | GPL | ✅ | Subprocess only | APPROVED WITH CONDITIONS |
| Piper voice `en_US-ljspeech` | MIT repo tag. Dataset **public domain** (LJ Speech). | — | Public domain | ✅ | ✅ | ✅ | — | **APPROVED (fallback voice)** |
| Piper voice `en_US-lessac` (+ voices fine-tuned from lessac: amy, alan, ryan, hfc_*, libritts_r…) | Dataset **Blizzard 2013 Lessac: research only, "excludes ... any commercial purpose"** | — | — | ❌ | ❌ | ❌ | — | **REJECTED**, use ljspeech / Kokoro |
| Piper `en_US-ryan`, `en_US-hfc_female` | Datasets **CC BY-NC-SA 4.0** | — | — | ❌ | ❌ | ❌ | — | **REJECTED** |
| MeloTTS-English | MIT | MIT | Not disclosed | ✅ | ✅ | ✅ | Notice | APPROVED (secondary fallback) |
| **F5-TTS** | **CC-BY-NC-4.0** | MIT | Emilia (in-the-wild) | ❌ | ❌ | ❌ | — | **REJECTED**, use Kokoro |
| **XTTS-v2** | **Coqui CPML (non-commercial, including outputs)** | MPL-2.0 (TTS lib) | — | ❌ | ❌ | ❌ | — | **REJECTED**, use Kokoro |
| Whisper weights (tiny–large-v3, turbo) | MIT (openai/whisper repo). HF `openai/*` cards tagged apache-2.0. Both permissive. | MIT | 680k h web audio (undisclosed) | ✅ | ✅ | ✅ | Notice | APPROVED |
| Systran faster-whisper CT2 conversions | MIT | — | — | ✅ | ✅ | ✅ | Notice | APPROVED |
| Silero VAD (bundled in faster-whisper) | MIT (**UNVERIFIED**, current version) | — | — | ✅ | ✅ | ✅ | Notice | APPROVED |

## 3. espeak-ng / phonemizer GPL-3: implications and required conditions

1. **SaaS operation (no distribution):** GPL-3 obligations are triggered by *conveying* copies. Running it on our servers to produce audio does **not** require releasing our source. It is GPL-3, not AGPL-3, so there is no network clause. Audio output is not a derivative of espeak-ng.
2. **Open-source distribution of ReelForge:** our Python code *imports* `phonemizer` (GPL-3) in-process. The FSF treats that as one combined work, so any **distributed combination** must be licensable under GPL-3. MIT/Apache-2.0 code is GPL-3-compatible, so we can keep ReelForge MIT/Apache **provided we do not ship a non-GPL-compatible piece in the same combined program**. Downstream users who bundle the TTS worker in a proprietary product inherit the GPL obligation.
3. **Required conditions (adopted):**
   - (a) Put TTS in its **own worker package** (`reelforge-tts`), documented as "contains GPL-3 dependencies; the combined worker is distributed under GPL-3-compatible terms". Core API, frontend and renderer packages must not import it. They talk to it over a queue or HTTP.
   - (b) Prefer **calling `espeak-ng` as a subprocess** (CLI `--ipa`) or using misaki's lexicon-first G2P with espeak as an out-of-vocabulary fallback. Do not link libespeak-ng in the API process.
   - (c) Any installer that bundles espeak-ng / FFmpeg / piper must include `THIRD_PARTY_LICENSES/` with GPL-3 text plus a written source offer or link to the exact upstream tags.
   - (d) Long-term option: an espeak-free English G2P (misaki lexicon plus a permissively licensed OOV model). **UNVERIFIED** that one exists at acceptable quality.

## 4. Media assets: music, SFX, fonts

| Source | License | Commercial | Use inside generated videos | Redistribute in our repo/installer | Obligations | Verdict |
|---|---|---|---|---|---|---|
| **Procedurally generated music/SFX (our NumPy synth: pads, arps, risers, whooshes, clicks, seeded)** | Our own code (MIT) | ✅ | ✅ | ✅ | None | **APPROVED, DEFAULT** (zero licensing risk, deterministic per seed, no Content ID claims) |
| Freesound, **CC0** sounds | CC0 1.0 | ✅ | ✅ | ✅ | None (keep a manifest anyway) | APPROVED |
| Freesound, CC BY 4.0 sounds | CC BY 4.0 | ✅ | ✅ | ✅ | **Attribution per sound** (author, title, link, license) | APPROVED WITH CONDITIONS (auto-credits in video description) |
| Freesound, CC BY-NC sounds | CC BY-NC 4.0 | ❌ | ❌ | ❌ | — | **REJECTED** |
| Pixabay Music/SFX | Pixabay Content License: free, no attribution needed. "You cannot sell or distribute Content ... on a **Standalone** basis." Full terms are in the Pixabay ToS. Automated-use and Content ID details **UNVERIFIED**. (https://pixabay.com/service/license-summary/) | ✅ | ✅ (embedded in a new work) | **❌ bundling a track library in our repo/installer is standalone redistribution** | — | **APPROVED WITH CONDITIONS**: user-supplied only, never bundled |
| Kevin MacLeod (incompetech) | Free tier is Creative Commons (CC BY 4.0, per incompetech, **UNVERIFIED** version on page). "Requires that you credit the music". A paid Standard License removes attribution. (https://incompetech.com/music/royalty-free/licenses/) | ✅ | ✅ | ✅ (CC BY allows it) | **Credit line on every video** | APPROVED WITH CONDITIONS (optional pack; prefer procedural) |
| Fonts (e.g. Inter, Montserrat, Poppins, Bebas Neue from Google Fonts) | SIL OFL 1.1 | ✅ | ✅ (embedding in video is fine) | ✅ (not sold standalone) | Include OFL text | APPROVED |

**Recommendation:** ship **procedural NumPy audio** as the only bundled music/SFX. Allow users to add their own tracks. Store a per-asset `license` field in the asset manifest, and auto-generate credits for CC BY assets.

## 5. Platform / infrastructure terms (summary; details in free-infrastructure.md)

| Service | Commercial use on free tier | Verdict |
|---|---|---|
| Cloudflare Pages / Workers / R2 / D1 | Allowed (standard ToS) | APPROVED |
| Supabase Free | Allowed. Pauses after 7 days inactivity. | APPROVED WITH CONDITIONS |
| Neon Free | Allowed | APPROVED (alternative) |
| **GitHub Pages** | **Not allowed** for "online business ... or commercial software as a service (SaaS)" | **REJECTED for the app frontend** (OK for project docs) |
| Render Free | "Do not use them for production applications" | Dev/demo only |
| Oracle Always Free | Allowed. Idle instances may be reclaimed. | APPROVED WITH CONDITIONS |

## 6. Mandatory compliance actions (to build into the project)

1. `THIRD_PARTY_LICENSES/` folder plus a generated SBOM (`pip-licenses` / `license-checker`) in CI. **Fail the build on GPL/AGPL/NC licenses outside the allow-listed TTS worker and FFmpeg binary.**
2. A model registry (`models.yaml`) with fields `license`, `commercial`, `requires_acceptance`, `attribution`, `flow_down_terms`. The UI refuses to load OPT-IN models until the operator accepts the terms.
3. Terms of Service template includes the OpenRAIL-M Attachment A use restrictions (SD1.5 family) and the Kokoro/ljspeech credits.
4. Never commit model weights, FFmpeg binaries or third-party audio to git. Download at install time with checksum pinning.
5. AI-generated content disclosure in exported video metadata (also required by FLUX Kommunity if opted in, and by the EU AI Act transparency duties, which are a legal obligation, not a license one; **UNVERIFIED** scope for this product).
