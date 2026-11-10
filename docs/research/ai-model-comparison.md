# NaRRAVO — AI Model Comparison (CPU-first)

- Research date: 2026-11-09
- Target: i7-10700 (8C/16T, AVX2, **no AVX-512/VNNI**), 32 GB DDR4-2933 dual channel (about 47 GB/s theoretical), UHD 630 iGPU, no CUDA
- Timing labels: **[M:source]** means measured by others on the stated hardware. **[E]** means our estimate, extrapolated to the i7-10700. All [E] values need a benchmark spike in Phase 1.
- Scaling rule used for [E]: the i7-10700 is roughly **1.3–1.8x slower** than the i7-12700/12700K used in most published CPU benchmarks. It has fewer cores (8 vs 12), lower IPC, and no VNNI, which hurts int8 the most. LLM decode speed is memory-bandwidth bound, so tok/s ≈ 0.6 × 47 GB/s ÷ model bytes.

License details and verdicts for every item are in [license-audit.md](./license-audit.md).

---

## 1. LLM (script + storyboard JSON) via Ollama

Runtime: **Ollama v0.40.15** (MIT), with a portable `ollama-windows-amd64.zip` on GitHub releases. Structured output: `format: <JSON Schema>` is supported locally (https://docs.ollama.com/capabilities/structured-outputs).

Typical job: about 1.5k prompt tokens plus about 1.2k output tokens (script plus storyboard for a 30–60 s reel).

| Model (Ollama tag) | Params | Q4 size (Ollama) | Weights license | Commercial SaaS? | Decode tok/s [E] | Job time [E] | Notes |
|---|---|---|---|---|---|---|---|
| **qwen3.5:4b** | 4.66B (multimodal) | **3.3 GB** | Apache-2.0 | ✅ | 8–11 | ~2–3 min | Newest small Qwen (Feb 2026). Has vision and tools. Thinking capable, so **set `think:false`**. |
| qwen3.5:9b (`latest`) | ~9B | 6.6 GB | Apache-2.0 | ✅ | 4–5 | ~4–6 min | Quality option |
| qwen3.5:2b | ~2B | 2.7 GB | Apache-2.0 | ✅ | 10–14 | ~1.5–2 min | Low-RAM fallback |
| qwen3:4b / qwen3:8b | 4B / 8B | 2.5 / 5.2 GB | Apache-2.0 | ✅ | 10–13 / 5–6 | ~2 / ~4–5 min | Mature, widely tested with `format` |
| qwen3:30b-a3b (MoE) | 30B total, 3B active | 19 GB | Apache-2.0 | ✅ | 8–12 (MoE reads only ~3B/token) | ~2–3 min | Best quality per second on CPU, but **19 GB RAM** blocks running image or TTS alongside it |
| qwen3.5:35b-a3b (MoE) | 35B, 3B active | 22 GB | Apache-2.0 | ✅ | 7–10 | ~3 min | Too RAM-hungry for a 32 GB shared box |
| qwen2.5:7b / 14b / 32b | — | 4.7 / 9.0 / 20 GB | Apache-2.0 | ✅ | — | — | Superseded by Qwen3/3.5 |
| **qwen2.5:3b** | 3B | 1.9 GB | **Qwen RESEARCH License, non-commercial** | ❌ | — | — | **REJECTED** |
| **qwen2.5:72b** | 72B | 47 GB | **Qwen License**: commercial OK up to **100M MAU**, "Built with Qwen" if used to train | ⚠️ | — | — | Too big anyway |
| llama3.2:3b / llama3.1:8b | 3B / 8B | 2.0 / 4.9 GB | Llama 3.x Community License | ⚠️ (700M MAU cap, "Built with Llama", AUP) | 11–14 / 5–6 | — | Not chosen (license friction, older) |
| gemma3:4b / 12b | 4B / 12B | 3.3 / 8.1 GB | Gemma Terms of Use | ⚠️ (Prohibited Use Policy flow-down, Google may restrict usage) | — | — | Superseded by Gemma 4 |
| **gemma4:e4b / e2b / 12b** | E4B / E2B / 12B | 6.6–9.5 / 4.6–7.5 / 7.7–8.0 GB | **Apache-2.0** (Gemma 4 moved to Apache; https://ai.google.dev/gemma/docs/gemma_4_license) | ✅ | 4–7 [E] | ~3–5 min | Good alternative, multilingual |
| ministral-3:3b / 8b / 14b | 3B / 8B / 14B | 3.0 / 6.0 / 9.1 GB | **Apache-2.0** (Ministral 3, Dec 2025) | ✅ | 9–12 / 4–6 / 3 | — | Good fallback. **Old Ministral-8B-2410 is MRL (research only), so use `ministral-3`.** |
| mistral:7b (v0.3) | 7B | ~4.1 GB | Apache-2.0 | ✅ | 6–7 | — | Older |
| phi4-mini | 3.8B | 2.5 GB | MIT | ✅ | 11–14 | ~2 min | Weaker creative writing (**UNVERIFIED**, subjective), strong at JSON |

Sources: Ollama library tags and sizes (https://ollama.com/library/qwen3.5/tags, https://ollama.com/library/qwen3/tags, https://ollama.com/library/gemma4, https://ollama.com/library/ministral-3, https://ollama.com/library/phi4-mini, https://ollama.com/library/qwen2.5). Licenses from the HF model APIs and LICENSE files: https://huggingface.co/Qwen/Qwen3.5-4B, https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE, https://huggingface.co/Qwen/Qwen2.5-72B-Instruct/blob/main/LICENSE, https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/LICENSE, https://ai.google.dev/gemma/terms, https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512, https://mistral.ai/licenses/MRL-0.1.md, https://huggingface.co/microsoft/Phi-4-mini-instruct.

**Recommendation (32 GB, CPU-only, JSON output):**
- **Default: `qwen3.5:4b`** (Apache-2.0, 3.3 GB) with `format` = Pydantic JSON Schema, `think:false`, `temperature` 0–0.4 and `keep_alive:0` before image generation.
- **Quality preset:** `qwen3.5:9b`. **Fallbacks:** `qwen3:4b` (most battle-tested with `format`), then `ministral-3:8b` or `gemma4:e4b` (Apache-2.0).
- Hard block in the model allow-list: `qwen2.5:3b`, any Llama/Gemma 3 by default (not illegal, but extra obligations), and any `-cloud` tags (remote inference).

---

## 2. Image generation

Target: 512–768 px (portrait, for example 512x896 upscaled to 1080x1920), **< ~60 s per image on CPU**.

### 2.1 CPU timings measured by FastSD CPU (i7-12700, per image) [M:fastsdcpu]

Source: https://github.com/rupeshs/fastsdcpu (MIT)

| Model | Res | Steps | PyTorch | OpenVINO | OpenVINO + TAESD | Our i7-10700 [E] (OV+TAESD) |
|---|---|---|---|---|---|---|
| SDXS-512-0.9 | 512² | 1 | 4.8 s | 3.8 s | 0.82 s | ~1–2 s |
| SD-Turbo | 512² | 1 | 7.8 s | 5 s | 1.7 s | ~2.5–3.5 s |
| SDXL-Turbo | 512² | 1 | 10 s | 5.6 s | 2.5 s | ~4–5 s |
| Hyper-SD SDXL | 768² | 1 | 19 s | 13 s | 6.3 s | ~10–12 s |
| SDXL-Lightning | 768² | 2 | 18 s | 12 s | 10 s | ~15–18 s |
| FLUX.1-schnell int4 | 512² | 3 | — | 4 min 30 s (~30 GB RAM) | — | **> 6 min, not viable** |
| FLUX.3 Image Klein int4 | 512² | 4 | — | ~36 s | — | ~55–65 s |

Not in the FastSD table, so estimated: **SD1.5 LCM / LCM-LoRA, 4 steps, 512x512, OpenVINO int8 + TAESD: about 4–8 s [E]**, and about 8–15 s at 512x896 [E]. Each LCM step costs roughly one SD-Turbo step plus CFG-free overhead. **FLUX.2-klein-4B int4 (OpenVINO), 4 steps, 512²: about 45–120 s [E]**. FastSD lists it as supported but gives no timing, and it needs at least 8 GB RAM.

### 2.2 Model matrix

| Model | Params | License (weights) | Commercial SaaS | CPU-feasible <60 s? | Quality notes | Verdict |
|---|---|---|---|---|---|---|
| **SD 1.5 + LCM-LoRA** / LCM_Dreamshaper_v7 (OpenVINO int8) | 0.86B UNet | CreativeML **OpenRAIL-M** (SD1.5). LCM-LoRA is OpenRAIL++. LCM_Dreamshaper_v7 is tagged MIT but derives from OpenRAIL-M weights, so **treat as OpenRAIL-M**. | ✅ with use-restriction flow-down | ✅ ~8–15 s at 512x896 [E] | Dated anatomy and text. Fine for stylised B-roll. Huge LoRA ecosystem. | **DEFAULT (APPROVED WITH CONDITIONS)** |
| SDXS-512-0.9 | ~0.3B | OpenRAIL++ | ✅ with conditions | ✅ ~1–2 s | Lower quality, 512 only | Fast "draft/preview" mode |
| SDXL base 1.0 | 3.5B | OpenRAIL++ | ✅ with conditions | ⚠️ 25–30 steps take many minutes. Needs Lightning/Hyper/LCM distillation. | Good | Via SDXL-Lightning (OpenRAIL++) only |
| SDXL-Lightning (ByteDance) | 3.5B | OpenRAIL++ | ✅ with conditions | ✅ ~15–18 s @768² [E] | Good quality at 2–4 steps | **Quality alternative (APPROVED WITH CONDITIONS)** |
| Segmind SSD-1B / Vega | 1.3B / 0.75B | Tagged Apache-2.0, but distilled from SDXL (OpenRAIL++) | ⚠️ provenance | ✅ with LCM | OK | Conditional. Treat as OpenRAIL++. |
| **SDXL-Turbo** | 3.5B | **Stability AI Community License** (LICENSE.md updated 2024-07-05; HF tag still says `sai-nc-community`) | ⚠️ only if operator revenue **< US$1M/yr** and they **register** with Stability; revocable | ✅ ~4–5 s | Very good at 512 | **Opt-in only, never bundled/default** |
| **SD-Turbo** | 0.86B | Stability terms ("For commercial use, please refer to stability.ai/license"), i.e. Community License | ⚠️ same as above | ✅ ~3 s | Good | **Opt-in only** |
| SD 3.5 Medium / Large | 2.5B / 8B | Stability Community License (<$1M, registration) | ⚠️ | ❌ minutes on CPU | Good text rendering | Rejected (license plus speed) |
| **FLUX.1-schnell** | 12B | **Apache-2.0** | ✅ | ❌ ~4.5 min on i7-12700, ~30 GB RAM | Excellent | License OK, **rejected on hardware** (GPU-only option) |
| **FLUX.1-dev** | 12B | **FLUX.1 [dev] Non-Commercial License** | ❌ | ❌ | Excellent | **REJECTED** (including derivatives like Freepik flux.1-lite-8B and Hyper-SD FLUX LoRAs) |
| **FLUX.2 [klein] 4B** | 4B | **Apache-2.0** (card: "available for commercial use"). Klein **9B is non-commercial**. | ✅ | ⚠️ ~45–120 s [E] | Modern quality, good prompt adherence | **"Quality" mode (APPROVED)**. Benchmark in Phase 1. |
| FLUX.3 Image Klein | — | **FLUX Kommunity License**: commercial only below **US$5M revenue**, content filters required | ⚠️ | ⚠️ ~55–65 s [E] | — | Opt-in only |
| Z-Image-Turbo (Tongyi) | 6B | Apache-2.0 | ✅ | ❌/⚠️ (6B, 8 steps, likely >2 min) [E] | Strong photoreal | GPU option |
| PixArt-Σ (512/1024) | 0.6B DiT + **T5-XXL (4.7B)** encoder | OpenRAIL++ | ✅ with conditions | ⚠️ T5-XXL encoding dominates CPU time | Good | Not default |
| Sana 600M / Sana-Sprint 0.6B | 0.6B + **Gemma-2-2B** encoder | Weights tagged Apache-2.0, but the card says "**intended for research purposes only**", and the encoder is under **Gemma Terms** | ⚠️ contradictory | ⚠️ | Good | **REJECTED until terms are clarified** |
| HiDream-I1-Fast | 17B | MIT | ✅ | ❌ | Excellent | GPU-only |
| Lumina-Image-2.0 | 2.6B (+Gemma-2 encoder) | Apache-2.0 (encoder under Gemma terms, **UNVERIFIED**) | ⚠️ | ⚠️ | — | Not evaluated further |

Sources: HF model APIs and cards: https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5, https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0, https://huggingface.co/stabilityai/sdxl-turbo/blob/main/LICENSE.md, https://huggingface.co/stabilityai/sd-turbo, https://stability.ai/license, https://huggingface.co/black-forest-labs/FLUX.1-schnell, https://huggingface.co/black-forest-labs/FLUX.1-dev, https://huggingface.co/black-forest-labs/FLUX.2-klein-4B, https://huggingface.co/black-forest-labs/flux-3-image-klein/blob/main/LICENSE.md, https://huggingface.co/Efficient-Large-Model/Sana_Sprint_0.6B_1024px_diffusers, https://huggingface.co/latent-consistency/lcm-lora-sdv1-5, https://huggingface.co/segmind/SSD-1B, https://huggingface.co/IDKiro/sdxs-512-0.9, https://huggingface.co/ByteDance/SDXL-Lightning, https://huggingface.co/Tongyi-MAI/Z-Image-Turbo, https://huggingface.co/OpenVINO/LCM_Dreamshaper_v7-int8-ov.

### 2.3 Runtime choice for images

| Runtime | License | CPU path | iGPU (UHD 630) | Verdict |
|---|---|---|---|---|
| **OpenVINO GenAI `Text2ImagePipeline`** (+ optimum-intel for export) | Apache-2.0 | ✅ int8/int4, fastest on Intel | ✅ `device="GPU"` (OpenCL). UHD 630 gains over the 8-core CPU are modest and **UNVERIFIED**. | **Default** |
| diffusers + PyTorch CPU | Apache-2.0 / BSD | ✅ but 1.5–3x slower than OpenVINO (FastSD table) | ❌ | Fallback |
| ComfyUI `--cpu` | **GPL-3.0** | Works (PyTorch fp32) but slow. CPU mode is a compatibility mode. | via the `openvino-dev-samples/comfyui_openvino` custom node (license NOASSERTION, **UNVERIFIED**) | **Optional adapter for users with NVIDIA/AMD GPUs**, run as an unmodified separate HTTP service |
| stable-diffusion.cpp (+ python bindings) | MIT | ✅ GGUF (FLUX.2 klein supported per FastSD) | Vulkan, **UNVERIFIED** on UHD 630 | Watch-list |

**Recommendation:** default **SD1.5-LCM (OpenVINO int8 + TAESD), 4 steps, 512x896**, about 8–15 s/image [E]. Optional **FLUX.2-klein-4B (Apache-2.0) "quality" mode** on OpenVINO int4, about 1–2 min/image [E]. "Draft" mode uses SDXS-512. **SDXL-Turbo/SD-Turbo and FLUX.3 Klein are never bundled**, only as user-supplied opt-ins with a license acknowledgement. ComfyUI is supported only as an external GPU backend.

---

## 3. TTS

| Model | Size | License (code / weights / voices / data) | Commercial SaaS | CPU speed | Quality | Verdict |
|---|---|---|---|---|---|---|
| **Kokoro-82M v1.0** | 82M params. ONNX ~300 MB fp32, ~80–92 MB int8 | Weights **Apache-2.0**. Code `hexgrad/kokoro` Apache-2.0. `kokoro-onnx` **MIT**. Voices are distributed in the same Apache-2.0 repo (54 voices, 8 languages). Training data is "permissive/non-copyrighted": public domain, Apache/MIT audio, **synthetic audio from closed TTS models**, Koniwa (CC BY 3.0) and SIWIS (CC BY 4.0). | ✅ (card: "can be deployed anywhere from production environments to personal projects") | RTF 0.2–0.5 reported on 4–8-core CPUs [M:community, see sources]. i7-10700 [E]: about 0.25–0.4, so 60 s of narration takes about 15–25 s. | Best-in-class for size, 24 kHz | **DEFAULT (APPROVED WITH CONDITIONS)**: G2P GPL caveat and CC-BY attribution, see the audit |
| Piper (OHF-Voice/piper1-gpl 1.8.0) | 15–75 MB per voice (VITS ONNX) | Engine now **GPL-3.0-or-later** (`piper-tts` on PyPI). The old `rhasspy/piper` (MIT) is **archived**. **Voices vary per dataset**: `ljspeech` = public domain ✅, `libritts_r` = CC BY 4.0 ✅ (attribution), **`lessac` = Blizzard 2013 research-only license ❌**, **`ryan` = CC BY-NC-SA ❌**, **`hfc_female` = CC BY-NC-SA ❌**. Many voices are **fine-tuned from lessac** (amy, alan, ryan…), which carries the lessac taint. | ⚠️ voice by voice | Very fast: RTF about 0.05–0.1 on CPU [E] | Robotic compared with Kokoro | **Fallback, allow-listed voices only** (ljspeech; libritts_r with attribution, but note libritts_r was fine-tuned from lessac, so ❌ to be safe). Effectively **ljspeech only**, unless the voice was trained from scratch on permissive data. |
| MeloTTS | ~200 MB | Code **MIT**, weights **MIT** (HF card) | ✅ | Real-time on CPU (per README, **UNVERIFIED** numbers) | Good | Secondary fallback. Repo inactive since 2024-12. Old dependency pins (Python ≤3.10 era), so packaging risk. |
| **F5-TTS** | ~1.3 GB | Code MIT, **weights CC-BY-NC-4.0** ("due to the training data Emilia") | ❌ | Slow on CPU | Excellent cloning | **REJECTED** |
| **XTTS-v2 (Coqui)** | ~1.8 GB | **Coqui Public Model License**: "allows only non-commercial use of a machine learning model **and its outputs**". Coqui (company) shut down. | ❌ | Slow on CPU | Excellent | **REJECTED** |

Sources: https://huggingface.co/hexgrad/Kokoro-82M (and VOICES.md), https://github.com/thewh1teagle/kokoro-onnx, https://github.com/hexgrad/misaki, https://github.com/OHF-Voice/piper1-gpl, https://pypi.org/project/piper-tts/, https://github.com/rhasspy/piper (archived), Piper voice MODEL_CARDs at https://huggingface.co/rhasspy/piper-voices (for example `en/en_US/lessac/medium/MODEL_CARD`), https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html, https://huggingface.co/myshell-ai/MeloTTS-English, https://github.com/SWivid/F5-TTS, https://huggingface.co/coqui/XTTS-v2 (LICENSE.txt). Community CPU RTFs: https://bittide.aicompass.dev/article/213f0a6c-be96-402b-8672-c2d9d3cb6029, https://localaimaster.com/blog/best-tts-without-gpu (secondary sources, treat as indicative).

**Recommendation:** **Kokoro-82M via `kokoro-onnx` (int8) or OpenVINO GenAI's Kokoro pipeline** as default, using English voices (`af_*`, `am_*`, `bf_*`, `bm_*`). **Fallback: Piper with the `en_US-ljspeech` voice only** (public domain). Phonemization uses espeak-ng (GPL-3), which needs process isolation; see the license audit.

---

## 4. Transcription / word timestamps

| Model (faster-whisper, CTranslate2) | Size (int8) | Weights license | CPU timing |
|---|---|---|---|
| tiny / tiny.en | ~40 MB | MIT (openai/whisper). HF CT2 conversions (Systran) are tagged MIT. | 60 s of narration ≈ 2–4 s [E] |
| **base / base.en** | ~75 MB | MIT | ≈ 4–7 s [E] |
| **small / small.en** | ~250 MB | MIT | **13 min audio in 1m42s int8 (beam 5, 8 threads, i7-12700K); batch 8: 51 s** [M:faster-whisper README]. Our 60 s clip ≈ 10–15 s [E]. |
| large-v3-turbo (deepdml CT2 conversion) | ~800 MB | MIT | ≈ 60–120 s [E], usually unnecessary |

- `word_timestamps=True` returns per-word `start` and `end` in `segment.words` (https://github.com/SYSTRAN/faster-whisper). Silero VAD (`vad_filter=True`) runs through onnxruntime.
- **Optimisation:** we already know the exact script text, so this is really **alignment**. Pass the script as `initial_prompt` and use `small.en`, then snap recognised words back to the script tokens (edit-distance alignment). Kokoro's PyTorch `KPipeline` also exposes per-token durations, which could skip STT entirely. Exposure through `kokoro-onnx` is **UNVERIFIED**.
- Alternative runtime: OpenVINO GenAI `WhisperPipeline` (Apache-2.0) and `Qwen3-ForcedAligner-0.6B` (Apache-2.0, released 2026-06). Forced alignment would be more accurate than ASR timestamps, but it is **UNVERIFIED** on CPU.

**Recommendation:** **faster-whisper `small.en`, int8, `word_timestamps=True`, VAD on**, with `base.en` as the fast preset. Total for a 60 s reel is about 10–15 s [E].

---

## 5. End-to-end CPU budget for one 45 s reel (8 scenes) [E]

| Stage | Default choice | Time [E] |
|---|---|---|
| Script + storyboard JSON | qwen3.5:4b, `format` schema | 2–3 min |
| 8 images 512x896 | SD1.5-LCM OpenVINO int8, 4 steps | 1–2 min (FLUX.2-klein quality mode: 8–15 min) |
| TTS | Kokoro int8 | 10–20 s |
| Word timestamps | faster-whisper small.en int8 | 8–12 s |
| Compose + encode 1080x1920 30 fps | NumPy/OpenCV/Pillow to x264 `veryfast` | 30–90 s |
| **Total** | | **≈ 4–7 min** (default), ≈ 12–20 min (quality mode) |

Run the stages sequentially and unload models between them (RAM budget about 8–10 GB peak in the default preset).
