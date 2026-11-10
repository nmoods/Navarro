# Feature Comparison Matrix — NaRRAVO (Phase Zero)

Research date: 2026-11-09. Evidence and URLs are in `competitor-analysis.md`.

**Legend**

| Mark | Meaning |
|---|---|
| ✓ | Confirmed on a public vendor page or README |
| ✗ | Confirmed absent, or out of the product's scope by design |
| partial | Present but limited: by tier, by quality, or only part of the capability |
| unverified | Not stated on fetched pages, only claimed by third parties, or page blocked |

The **NaRRAVO (target)** column is a *plan*, not a shipped capability.

---

## A. Faceless / short-form generators

| Feature | FacelessReels | Revid | AutoShorts | Fliki | Pictory | invideo AI | reelforgeai.io | **NaRRAVO (target)** |
|---|---|---|---|---|---|---|---|---|
| Idea/prompt to full video | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| URL/blog/doc to video | unverified | ✓ | ✗ | ✓ | ✓ | unverified | unverified | ✓ |
| AI script generation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (local LLM) |
| Script lock (no AI rewrite) | unverified | unverified | partial (edit script) | ✗ (reviews: rewrites) | ✓ (line = scene) | unverified | unverified | ✓ |
| Storyboard before render | unverified | unverified | partial (preview) | unverified | partial (setup Qs) | ✓ | partial (Director Mode) | ✓ |
| AI voice / TTS | unverified | ✓ 70+ langs | ✓ | ✓ 2,000+ | ✓ ElevenLabs | ✓ | ✓ 6 voices | ✓ (local TTS) |
| Voice cloning | unverified | partial (Ultra) | ✓ (paid) | partial (1–3) | partial (Pro+) | ✓ | partial (Hustler+) | partial (OSS clone models, opt-in) |
| AI image generation | ✓ (art styles) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (8 styles) | ✓ (local SD-class, optional) |
| Generative AI video | unverified | ✓ | partial (motion credits) | partial (Premium) | ✓ Veo 3.1 | ✓ | unverified | ✗ (by design: CPU-only) |
| 2.5D / parallax motion on stills | unverified | partial ("moving images") | partial | unverified | unverified | unverified | unverified | ✓ (core) |
| Animated subtitles | unverified | ✓ | unverified | ✓ word-level | ✓ | unverified | ✓ | ✓ |
| Subtitle file export (SRT/VTT) | unverified | unverified | unverified | unverified | ✓ | unverified | unverified | ✓ |
| Scene editor | unverified | ✓ | partial | unverified | ✓ | ✓ | unverified | ✓ |
| Single-scene regeneration | unverified | unverified | partial (swap images) | partial (re-render costs credits) | ✓ (variations) | ✓ | unverified | ✓ (free, local) |
| Timeline editor | unverified | unverified | ✗ | unverified | ✓ | ✓ multitrack | unverified | partial (scene timeline) |
| Templates / formats | ✓ | ✓ (viral remix) | ✓ (presets) | ✓ | ✓ | unverified | ✓ (hook styles) | ✓ (open, shareable) |
| Series / batch | ✓ | partial (Auto-Mode) | ✓ (1 series) | unverified | unverified | partial (microdrama claim) | ✓ (Autopilot) | ✓ |
| Story continuity across episodes | unverified | unverified | unverified | unverified | partial (char. consistency in-video) | partial (claim) | unverified | ✓ |
| Brand kit / reusable profile | partial (art style) | unverified | unverified | ✓ | ✓ | partial (claim) | ✓ | ✓ (Story DNA) |
| Hook variants / A-B | unverified | partial (viral analysis) | ✗ | unverified | unverified | unverified | partial (hook styles) | ✓ (Hook Lab) |
| Fact checking / citations | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | unverified | ✓ |
| Auto-post to socials | ✓ | ✓ (TT, IG, YT, X) | ✓ | ✓ | ✗ (Zapier/Make) | unverified | ✓ | ✗ in MVP (export only) |
| API / automation | unverified | ✓ API/MCP/CLI | unverified | partial (Premium) | partial (separate pricing) | partial (agent connectors) | partial (Mogul+) | ✓ (local CLI/API) |
| Multi-aspect export | unverified | unverified | unverified | ✓ | ✓ 16:9/9:16/1:1 | ✓ | ✗ (vertical) | ✓ |
| Offline / local processing | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Open source | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Real free tier, no watermark | unverified | ✗ | ✗ (paused) | ✗ (watermark) | ✗ (14-day trial) | ✗ (no free plan) | ✗ (watermark) | ✓ |

## B. Editors and clipping tools with AI

| Feature | VEED | Kapwing | Canva | Descript | CapCut | OpusClip | Submagic | Captions/Mirage |
|---|---|---|---|---|---|---|---|---|
| Idea/prompt to full video | unverified | ✓ (Kai) | partial (8 s clips) | partial | ✓ (script-to-video) | ✗ | partial | partial |
| AI script generation | unverified | ✓ | partial (Magic Write) | partial (Underlord) | unverified | ✗ | unverified | unverified |
| Storyboard before render | unverified | ✓ | ✗ | ✗ | unverified | ✗ | ✗ | ✗ |
| TTS | unverified (3rd-party ✓) | ✓ | unverified | ✓ | ✓ | ✓ (20/day) | unverified | unverified |
| Voice cloning | unverified | partial (Business) | unverified | ✓ | unverified | ✗ | unverified | partial (AI twin) |
| AI image generation | unverified | ✓ | ✓ | ✓ | ✓ | partial (B-roll) | ✓ | unverified |
| Generative AI video | unverified | ✓ (multi-model) | ✓ (Veo, paid) | ✓ | ✓ (Seedance Mini) | partial (B-roll) | ✓ | ✓ |
| Animated subtitles | ✓ | ✓ | unverified | ✓ | ✓ | ✓ | ✓ (core) | ✓ (core) |
| Text-based (transcript) editing | unverified | unverified | ✗ | ✓ (core) | unverified | partial | ✗ | unverified |
| Scene editor | unverified | ✓ | ✓ (pages) | ✓ | ✓ | partial | ✗ | unverified |
| Timeline editor | ✓ | ✓ | ✓ | ✓ | ✓ | partial | ✗ | partial |
| Templates | unverified | ✓ | ✓ | ✓ | ✓ | partial (brand templates) | ✓ | ✓ |
| Series / batch | ✗ | ✗ | partial (Bulk Create, designs) | ✗ | ✗ | partial (bulk export) | ✗ | ✗ |
| Brand kit | unverified | ✓ (Pro+) | ✓ (paid) | unverified | partial (Teams) | ✓ | partial (custom templates) | unverified |
| Social publishing | unverified | ✗ | unverified | partial (share link) | unverified | ✓ (9 platforms + scheduler) | ✓ (Pro+) | ✗ |
| Long-to-short repurposing | unverified | unverified | ✗ | partial | unverified | ✓ (core) | ✓ (Magic Clips) | partial |
| Reframe to multiple ratios | unverified | ✓ (9 ratios) | ✓ (resize) | ✓ | unverified | ✓ (Pro) | unverified | unverified |
| Fact checking | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Offline / local | ✗ | ✗ | ✗ | partial (desktop app, cloud AI) | partial (desktop app, cloud AI) | ✗ | ✗ | ✗ |
| Free tier without watermark | ✗ | ✗ | partial | ✗ | partial (free tools; unverified) | ✗ | ✗ | ✗ |

## C. Animation / template / avatar platforms

| Feature | Lumen5 | Steve AI | Animaker | Renderforest | Vidnoz |
|---|---|---|---|---|---|
| Idea/prompt to full video | ✓ | ✓ | ✓ | ✓ | ✓ |
| Blog/doc to video | ✓ (core) | ✓ | unverified | ✗ | unverified |
| AI script generation | ✓ | ✓ | ✓ | partial | ✓ |
| Clarifying questions before generation | unverified | unverified | ✓ | ✗ | unverified |
| TTS | ✓ | ✓ | ✓ 1,800+ | ✓ 50+ langs | ✓ 890–2,660 |
| Character animation | ✗ | ✓ (300+) | ✓ (builder, lip sync) | partial (templates) | ✓ (avatars) |
| Kinetic typography / camera moves | unverified | ✓ | unverified | partial (templates) | unverified |
| Generative AI video | partial (AI clips) | ✓ | ✓ (90–320 s/mo) | ✓ (multi-model) | ✓ |
| Subtitles | unverified | unverified | ✓ 130+ langs | ✓ | unverified |
| Scene editor | ✓ | partial | partial (Advanced Edit) | ✓ (per-shot regen) | ✓ |
| Templates | ✓ | ✓ | ✓ | ✓ (core) | ✓ 3,200+ |
| Series / batch | ✗ | partial ("YouTube automation") | ✗ | ✗ | unverified |
| Recurring custom characters | ✗ | partial (Enterprise custom avatars) | ✓ (custom characters) | ✗ | partial (photo avatars) |
| Brand kit | ✓ | partial (Enterprise) | partial (Enterprise) | unverified | partial (Business) |
| Cost shown before generation | unverified | unverified | unverified | ✓ | unverified |
| Fact checking | ✗ | ✗ | ✗ | ✗ | ✗ |
| Offline / local | ✗ | ✗ | ✗ | ✗ | ✗ |
| Free tier without watermark | ✗ | unverified | ✗ | ✗ | ✗ |

## D. Open-source projects

| Feature | MoneyPrinterTurbo | ShortGPT | short-video-maker | **NaRRAVO (target)** |
|---|---|---|---|---|
| License | MIT | MIT | MIT | OSS (TBD by license research) |
| Local LLM (e.g. Ollama) | ✓ | ✗ (OpenAI) | ✗ (scenes supplied) | ✓ |
| Free local TTS | partial (Edge TTS is a free *cloud* service; Kokoro/Chatterbox local) | partial (EdgeTTS) | ✓ Kokoro (English only) | ✓ |
| Word-level captions | ✓ (faster-whisper) | ✓ | ✓ (whisper.cpp) | ✓ |
| Visual source | Stock (Pexels/Pixabay/Coverr) + AI APIs | Pexels + Bing images | Pexels only | Local image gen + user assets + optional stock |
| Per-scene storyboard UI | ✗ | ✗ | ✗ (community UI) | ✓ |
| Single-scene regeneration | ✗ | ✗ | ✗ | ✓ |
| 2.5D / parallax motion | ✗ | ✗ | ✗ | ✓ |
| Infographics / maps / timelines | ✗ | ✗ | ✗ | ✓ (Visual Intelligence) |
| Series / continuity | partial (batch only) | ✗ | ✗ | ✓ |
| Fact checking | ✗ | ✗ | ✗ | ✓ |
| Windows support | ✓ (one-click pack) | partial (Docker) | ✗ | ✓ |
| CPU-only viable | ✓ (4-core / 4 GB min) | unverified | ✓ (2 vCPU / 3 GB) | ✓ (target) |
| Auto-upload | ✓ | ✗ | ✗ | ✗ (MVP) |

## E. Free-plan and pricing snapshot (seen 2026-11-09)

| Product | Free plan | Entry paid | Top self-serve | Model |
|---|---|---|---|---|
| FacelessReels | unverified | ~$19–39 (3rd-party, unverified) | unverified | Subscription |
| Revid | Sign-up credits only, no download (reviews) | $39/mo | $199–2,799/mo | Credits |
| AutoShorts | 1 video (paused) | $19/mo | $69/mo | Posting cadence |
| Fliki | 3 credits/mo, 720p, watermark | unverified (not rendered) | Enterprise | Credits (≈ min) |
| Pictory | 14-day trial, 720p, watermark | $25/mo (annual) | $119/mo (annual) | Credits |
| invideo AI | None | $9/seat/mo | $80/seat/mo | Credits per seat |
| reelforgeai.io | 3 videos/mo, 720p, watermark | $17/mo | $147/mo | Videos/mo |
| VEED | 720p, watermark (3rd-party) | ~$9–19 (unverified) | ~$49 (unverified) | Seats + credits |
| Kapwing | 10 credits, 720p, watermark, 4-min | $16/mo | $50/mo | Credits |
| Canva | Free tier (AI video minimal) | ~$12.99–15 (unverified, 403) | — | Subscription |
| Descript | 1 h, 100 credits, 720p, watermark | $16/mo | $50/mo | Media hours + credits |
| CapCut | Free tools, 7-day Pro trial | $11/mo | $79/mo | Credits |
| OpusClip | Watermark, 3-day expiry | $15/mo | $29/mo | Credits |
| Submagic | None listed | $19/mo | $69/mo | Credits |
| Lumen5 | Watermark (3rd-party) | ~$19–29 (unverified) | ~$149–199 (unverified) | Subscription |
| Steve AI | 1,200 s + 200 credits | $10/mo (conflicting) | $40–80 (conflicting) | Credits |
| Animaker | Watermark | $25/mo (annual) | $79/mo (annual) | Credits |
| Renderforest | 20 credits, 480p, watermark | $15/mo ($9 annual) | $59/mo | Credits (cost shown) |
| Vidnoz | ~60 credits/day, 720p, watermark | unverified | Enterprise | Credits |
| MoneyPrinterTurbo / ShortGPT / short-video-maker | Free (MIT) | — | — | Bring-your-own API keys (optional) |
| **NaRRAVO (target)** | **Everything, no watermark** | — | — | Local compute only |

## F. Feature-gap heatmap (how many of the 22 products verifiably offer each feature)

| Capability | Verified offering (approx.) | Signal |
|---|---|---|
| AI script / prompt to video | ~18 | Commodity |
| TTS voiceover | ~16 | Commodity |
| Animated subtitles | ~14 | Commodity (style is the differentiator) |
| Generative AI video (cloud) | ~14 | Commodity, credit-expensive |
| Templates | ~16 | Commodity / overused |
| Brand kit | ~10 (often top tier) | Common, often paywalled |
| Social auto-posting | ~8 | Common in faceless tools |
| Storyboard-before-render | ~3 (Kapwing, invideo, partial others) | Emerging |
| Per-scene regeneration | ~4 | Underserved, and it costs credits everywhere |
| Series continuity memory | 0 verified (claims only) | **Gap** |
| Hook variant testing | 0 verified (partial analogues) | **Gap** |
| Fact checking / source citations | 0 | **Gap** |
| Data-driven visuals (maps, timelines, infographics) | 0 verified | **Gap** |
| 2.5D parallax as a first-class motion engine | 0 verified | **Gap** |
| Fully offline / local AI | 0 commercial; OSS partial | **Gap** |
| Caption file (SRT/VTT) export | 1 verified (Pictory) | Underserved |
