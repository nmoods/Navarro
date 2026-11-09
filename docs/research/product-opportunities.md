# Product Opportunities — ReelForge AI (Phase Zero)

- **Research date:** 2026-11-09.
- **Evidence references** point to `competitor-analysis.md`, which holds the full quotes and URLs.

## Rubric

| Field | Meaning |
|---|---|
| **Problem** | The user pain, with evidence |
| **Feature** | What we build |
| **Value** | What the user gains |
| **CPU feasibility** | How well it runs on CPU-only local hardware |
| **Differentiation** | How it stands apart from competitors |
| **Complexity** | S (≤1 dev-week), M (2–4 weeks), L (>1 month) |

## CPU feasibility key

These are planning estimates. They must be benchmarked in Phase 1, and the model and licence choices need confirming by the tech/licence research track.

| Rating | Meaning | Typical workloads |
|---|---|---|
| 🟢 | Comfortable on a 4–8 core laptop | FFmpeg, SVG/Canvas rendering, small TTS (Kokoro/Piper class), whisper.cpp base/small, small depth models, small NLI/embedding models, rule-based logic |
| 🟡 | Feasible but slow; needs a background queue | Quantised 3–8B local LLM via llama.cpp/Ollama, few-step distilled image models at ≤768 px |
| 🔴 | Impractical on CPU | Generative video models, large diffusion models at high resolution |

ReelForge must not depend on 🔴 workloads.

---

## Part 1 — Twenty core opportunities (O1–O20)

### O1. Script Lock and diff view
- **Problem:** Fliki "will sometimes substantially rewrite the script anyway" (Trustpilot, 2026-09-09). Revid "frequently ignores prompts". invideo "never understood my commands".
- **Feature:** Approved script lines are locked. The AI may only propose changes as a visible diff, which the user accepts or rejects per line.
- **Value:** Trust. The narration says exactly what the creator approved.
- **CPU:** 🟢 This is UI and state only.
- **Differentiation:** No competitor verifiably offers an explicit lock or diff contract.
- **Complexity:** S

### O2. Unlimited free re-rolls with a time-based "cost preview"
- **Problem:** Credit drain is the #1 complaint theme across invideo, Revid, Fliki, Kapwing, Descript and CapCut ("paying for mistakes that AI makes"; "charges you more credits every time you try to fix mistakes made by its own AI").
- **Feature:** Every generation is local and free. Before it runs, the UI shows an estimated *time* cost based on a hardware benchmark, borrowing Renderforest's show-cost-before-run pattern.
- **Value:** Users experiment freely, and failed generations cost nothing.
- **CPU:** 🟢 for the estimator. Generation speed varies.
- **Differentiation:** This structurally removes the industry's top complaint.
- **Complexity:** S

### O3. Cinematic 2.5D motion engine (depth-parallax)
- **Problem:** "All the images it makes for videos are just static, nothing dynamic" (AutoShorts review). YouTube's policy demonetises "image slideshows… with minimal… narrative". Ken Burns is the "lowest ceiling" format.
- **Feature:**
  - A monocular depth map per image is split into 2–4 layers, with background inpainting at the edges.
  - A virtual camera adds dolly, orbit, rack-focus, push-in, tilt and parallax drift.
  - Light particles, fog and grain overlays. Motion presets are keyed to scene mood.
- **Value:** Stills feel filmed, at no GPU or credit cost.
- **CPU:** 🟢/🟡 Small depth models run in seconds per image. Layered compositing via FFmpeg or a canvas renderer is fine. Inpainting the edges is the slowest step; start with simple edge-stretch or blur fill.
- **Differentiation:** Competitors either do flat Ken Burns or pay for cloud gen-video. No one verifiably makes 2.5D the core motion vocabulary.
- **Complexity:** L

### O4. Originality guard against YouTube's "inauthentic content" policy
- **Problem:** YouTube's July 2025 policy targets "AI-generated content made with generic or unoriginal templates giving the impression of mass production". Faceless channels report demonetisation risk.
- **Feature:** Before export, ReelForge scores each episode against the creator's own past episodes:
  - Template repetition, structure sameness and caption/visual/motion reuse.
  - Whether the episode has narrative or commentary or is just list filler.
  - It suggests variation, such as a different hook archetype, visual type or pacing.
- **Value:** Lowers demonetisation risk and pushes quality up.
- **CPU:** 🟢 Embeddings plus heuristics.
- **Differentiation:** No competitor addresses the policy inside the product. Some only blog about it.
- **Complexity:** M

### O5. Source-grounded scripting with citations
- **Problem:** 404 Media and historians document error-filled AI history videos. Lumen5 and Fliki do URL-to-video but do not show where the facts came from.
- **Feature:** The user attaches URLs, PDFs or notes. Each script sentence links to the source passage that supports it. A "Sources" block is generated for the video description.
- **Value:** Credibility, plus defensibility when commenters challenge facts.
- **CPU:** 🟡 for local LLM drafting. Retrieval over the user's sources is 🟢.
- **Differentiation:** No competitor offers this.
- **Complexity:** M

### O6. Open caption-style library plus SRT/VTT/ASS export
- **Problem:** Captions are the core value of Submagic and Captions, and they are paywalled. Only Pictory verifiably exports .srt/.vtt. Kapwing users hit "Failed to transcribe asset".
- **Feature:**
  - 15+ animated presets: word-pop, karaoke highlight, emoji-accent, keyword colour, boxed.
  - Brand-style overrides.
  - Export as burned-in captions plus sidecar SRT, VTT and ASS files.
  - Captions are derived from the script and TTS timings, so they are exact. No transcription error is possible.
- **Value:** Professional captions for free, with accurate text.
- **CPU:** 🟢
- **Differentiation:** Script-derived exact timing, combined with free sidecar export.
- **Complexity:** M

### O7. Never-lose-work local projects and resumable renders
- **Problem:** CapCut "Lost content, 15 hours". OpusClip free "deletes any saved progress". Kapwing "exports are broken".
- **Feature:**
  - The project is a plain folder with a JSON or YAML manifest, an assets directory and a version history.
  - Autosave runs continuously.
  - Renders are cached per scene, so they resume after a crash and only changed scenes re-render.
- **Value:** Reliability and ownership.
- **CPU:** 🟢
- **Differentiation:** Cloud tools cannot promise local ownership.
- **Complexity:** M

### O8. Creative brief by clarifying questions
- **Problem:** Prompt-to-video tools guess intent. invideo "never understood my commands".
- **Feature:** Before the script, ReelForge asks 3–5 quick questions: audience, tone, goal, length, must-include facts. This is the pattern Animaker verifiably uses. The answers are saved into Story DNA.
- **Value:** A better first draft and fewer re-rolls.
- **CPU:** 🟡 for LLM-generated questions. A templated fallback is 🟢.
- **Differentiation:** Animaker does this for explainers. No faceless short tool verifiably does.
- **Complexity:** S

### O9. Voice direction controls
- **Problem:** Category complaints about "robotic narration". Fliki users report "unnatural voiceovers".
- **Feature:**
  - Per-line emphasis, pause and speed controls.
  - Pronunciation dictionary.
  - Multi-voice dialogue.
  - "Breath" and room-tone options.
- **Value:** Narration that sounds directed, not read.
- **CPU:** 🟢 Small local TTS runs faster than real time on CPU (short-video-maker ships Kokoro on CPU).
- **Differentiation:** Most tools offer only voice selection.
- **Complexity:** M

### O10. Kinetic-typography scenes
- **Problem:** Every scene needing an AI image is slow, expensive and repetitive. Steve AI shows that kinetic text is a valued motion vocabulary.
- **Feature:** Text-first scenes: big quotes, numbers, word-by-word reveals and typographic transitions, driven by the script.
- **Value:** Visual variety and emphasis on key lines, with zero image generation.
- **CPU:** 🟢
- **Differentiation:** Treated as a first-class scene type chosen by Visual Intelligence (C2).
- **Complexity:** S–M

### O11. LLM-readable, git-friendly project format
- **Problem:** Closed formats lock creators in. ShortGPT shows the value of "editing markup" that an LLM can read.
- **Feature:** A documented scene-graph schema covering script, timings, visual type, motion preset, assets and captions. It is editable by hand, by any LLM or by scripts.
- **Value:** Automation, portability and diffable versions.
- **CPU:** 🟢
- **Differentiation:** Open standard versus proprietary projects.
- **Complexity:** S

### O12. Local media library with semantic search
- **Problem:** "it cant choose the match pic" (Fliki). Pictory gets "incorrect image selection".
- **Feature:** Index the user's own images, clips and past generations with CLIP-style embeddings. Each scene gets the best matches ranked, and the user can pin a choice.
- **Value:** Better visual matching that uses the creator's own assets.
- **CPU:** 🟢 Small CLIP models embed images in about a second each.
- **Differentiation:** Private and local, and it compounds with Visual Memory (C12).
- **Complexity:** M

### O13. Platform-safe export presets
- **Problem:** Generic exports clash with platform UI overlays and loudness normalisation.
- **Feature:**
  - Safe-zone overlays for TikTok, Reels and Shorts in the preview.
  - Caption auto-placement outside UI zones.
  - Loudness normalisation to platform targets.
  - Duration and size checks.
  - The exact platform specs must be verified per platform in Phase 1.
- **Value:** A professional, platform-native finish.
- **CPU:** 🟢
- **Differentiation:** Rarely surfaced explicitly by competitors (unverified across them).
- **Complexity:** S

### O14. Draft animatic in seconds
- **Problem:** Waiting for a full render to see whether the story works. Reviewers complain about "laggy output" (VEED) and "slowest premium application" (Lumen5).
- **Feature:** An instant low-resolution animatic: placeholder visuals, TTS and captions, with motion previewed in the browser. The full 1080p render happens only on approval.
- **Value:** Fast iteration on a CPU.
- **CPU:** 🟢
- **Differentiation:** Combines Kapwing and invideo's storyboard-first idea with near-zero latency.
- **Complexity:** M

### O15. Hardware-aware quality profiles
- **Problem:** Local OSS tools fail on low-end machines. MoneyPrinterTurbo documents a 3 GB Whisper download and FFmpeg path failures. short-video-maker warns that Remotion runs out of memory on low resources.
- **Feature:**
  - A first-run benchmark recommends Eco, Balanced or Quality profiles (model sizes, resolution, concurrency).
  - A one-click model downloader with checksums and mirrors.
- **Value:** It works out of the box on modest PCs.
- **CPU:** 🟢
- **Differentiation:** Beats the OSS setup friction that is the main weakness of free alternatives.
- **Complexity:** M

### O16. Provenance and licence ledger with AI-disclosure helper
- **Problem:** MoneyPrinterTurbo bundles music that "should be removed if it infringes". The CapCut licence controversy shows creators care about rights.
- **Feature:**
  - Every asset records its origin, licence and the model used.
  - An export report lists them.
  - A checklist helps with platform AI-content disclosure toggles. The current policies need verifying per platform.
- **Value:** Fewer copyright strikes and transparent AI use.
- **CPU:** 🟢
- **Differentiation:** No competitor surfaces this.
- **Complexity:** S

### O17. Bundled royalty-free music and SFX with beat-aware cuts
- **Problem:** Music rights risk in OSS tools. Generic cut timing.
- **Feature:**
  - A curated CC0 or permissively licensed library, pending licence verification.
  - Local beat detection that snaps scene cuts and caption pops to beats.
  - Mood tags.
- **Value:** Polished rhythm without legal risk.
- **CPU:** 🟢
- **Differentiation:** A local, rights-clean library combined with beat sync.
- **Complexity:** M

### O18. Multilingual versioning
- **Problem:** Language reach is a paid feature everywhere: Fliki dubbing, Kapwing translation minutes, Animaker translation.
- **Feature:** Translate the locked script with a local LLM or local translation model, re-voice with local multilingual TTS, and re-time captions and scenes automatically.
- **Value:** One story in many languages for free.
- **CPU:** 🟡 Translation quality and speed vary, and TTS language coverage depends on the model.
- **Differentiation:** Offline and unlimited.
- **Complexity:** M

### O19. Accessibility pack
- **Problem:** Accessibility is not marketed by any short-form competitor (unverified gap).
- **Feature:**
  - High-contrast and dyslexia-friendly caption presets.
  - A colour-blind-safe infographic palette.
  - An audio-description track option.
  - A flashing and strobe check.
- **Value:** Wider audience reach and inclusive content.
- **CPU:** 🟢
- **Differentiation:** An ethical differentiator that suits open source.
- **Complexity:** S

### O20. Optional bring-your-own-provider connectors (off by default)
- **Problem:** Some users have a GPU or API keys and want higher fidelity. MoneyPrinterTurbo shows demand for pluggable providers.
- **Feature:** A provider interface for LLM, TTS and image generation. Local is the default, and cloud is opt-in, user-keyed and clearly labelled "leaves your machine".
- **Value:** It scales up without becoming a SaaS.
- **CPU:** 🟢 This is the interface only.
- **Differentiation:** Privacy-by-default with honest labelling.
- **Complexity:** M

---

## Part 2 — Candidate ideas evaluated (C1–C15)

### C1. Story DNA (reusable brand and creative profile)
- **Problem:**
  - Faceless channels "look inconsistent because they just generate random images per video" (Reddit snapshot).
  - Brand kits are paywalled or Enterprise-only: Steve AI and Animaker on Enterprise, Kapwing on Pro and above.
  - Brand kits store only colours, fonts and logos, not *narrative* identity.
- **Feature:** A profile covering:
  - narrator persona and voice settings
  - tone, vocabulary and banned words
  - hook archetypes, pacing targets and caption style
  - colour, typography and visual style prompt with seeds
  - motion preset palette, music moods, recurring intro and outro
  - audience brief
  
  It is applied to every project and series.
- **Value:** Recognisable channel identity, which is also a defence against "inauthentic" sameness *across* channels.
- **CPU:** 🟢
- **Differentiation:** Extends brand kits from visual identity to creative and narrative identity. Free.
- **Complexity:** M
- **Verdict:** **MVP**

### C2. Visual Intelligence (AI picks the visual type per scene)
- **Problem:**
  - Every competitor defaults to one visual type per scene: a stock clip or AI image.
  - Results are "generic and formulaic" (Steve AI reviews), and there are image mismatches (Fliki, Pictory).
- **Feature:** A per-scene classifier, using an LLM plus rules over entities, dates, numbers and places, chooses among:
  - AI or own image with 2.5D motion
  - kinetic type
  - timeline
  - map
  - infographic or chart
  - quote card
  - split comparison
  
  The user can override the choice.
- **Value:** Varied, information-rich visuals that look edited by a person.
- **CPU:** 🟡 for classification with an LLM. The renderers are 🟢.
- **Differentiation:** No competitor does content-aware visual-type selection.
- **Complexity:** L for all types. Ship in increments.
- **Verdict:** **MVP**, with kinetic type, timeline and image first.

### C3. Story continuity across a series
Merged with C15.
- **Problem:**
  - Visual drift: "characters changing looks between scenes" (Reddit/HN summary).
  - "switches gender mid-scene" (Revid review).
  - invideo only *claims* series consistency.
- **Feature:** A series "bible":
  - characters with reference images, fixed seeds and prompt tokens
  - locations, running facts, timeline of events and open threads
  
  It is injected into every episode's script and image prompts. A continuity checker flags contradictions.
- **Value:** Binge-able serialized storytelling: recurring characters, callbacks and cliffhangers.
- **CPU:** 🟡 Character consistency on CPU is limited. Use seeds, reference-guided prompts and asset reuse rather than heavy adapters.
- **Differentiation:** No competitor verifiably offers this.
- **Complexity:** L
- **Verdict:** **MVP-lite**: bible plus text continuity. Visual consistency comes later.

### C4. Single-scene regeneration
- **Problem:**
  - Fliki users need "2 to 4 generations per video", and re-renders cost credits.
  - Revid has "no redo, refund, or rollback".
  - Only Renderforest and Pictory verifiably offer per-shot regeneration, and they charge credits.
- **Feature:** Regenerate the text, image, motion, voice or caption of any one scene, with history and A/B comparison. Only that scene re-renders.
- **Value:** Precision editing, and fixes cost nothing.
- **CPU:** 🟢 This is orchestration. It reuses the cache from O7.
- **Differentiation:** Free and granular.
- **Complexity:** M
- **Verdict:** **MVP**

### C5. Hook Lab (multiple hook variants)
- **Problem:**
  - Retention lives or dies in the first seconds.
  - Revid sells "viral analysis". reelforgeai.io offers "hook styles".
  - No competitor verifiably generates and compares rendered hook variants.
- **Feature:**
  - Generate 3–5 hook variants by archetype: question, shock stat, contrarian, story cold-open, POV.
  - Score them with a heuristic hook-strength rubric.
  - Render short preview variants.
  - Export multiple versions for the user's own platform A/B testing.
- **Value:** Better retention with no guesswork.
- **CPU:** 🟡 LLM. Renders of the first 3 seconds are 🟢.
- **Differentiation:** Rendered variants, not just text suggestions.
- **Complexity:** M
- **Verdict:** **MVP**

### C6. Series Factory (batch episodes)
- **Problem:**
  - Series automation is the core of FacelessReels and AutoShorts, but AutoShorts allows only 1 series per plan.
  - Paid tiers are priced by posting cadence ($19–69/mo).
- **Feature:**
  - Plan N episodes from one premise, inheriting Story DNA and the series bible.
  - Queue overnight local renders.
  - A review board approves each episode.
  - No auto-posting in the MVP; export folders are named per platform.
- **Value:** Volume without paying for each post, while staying under creator control.
- **CPU:** 🟡 Throughput is bounded by the local LLM and image generation. Use an overnight queue.
- **Differentiation:** Unlimited series and quality gates (O4) instead of blind autopilot.
- **Complexity:** M
- **Verdict:** **MVP**, combined with C3.

### C7. Story fact checker
- **Problem:**
  - AI history videos are full of errors (404 Media, historians).
  - Zero of the 22 products offer fact checking.
- **Feature:**
  - Extract checkable claims (dates, numbers, names, superlatives).
  - Verify them against the user's sources (O5), an optional offline reference corpus, or opt-in web search.
  - Mark each claim as supported, contradicted or unverifiable.
  - Suggest hedged rewrites.
  - Add on-screen source cards.
- **Value:** Credibility and less misinformation. It also differentiates the channel in "AI slop" debates.
- **CPU:** 🟡 for claim extraction with the LLM. NLI and entailment with small models is 🟢.
- **Differentiation:** Unique. It is the core of the "fact-aware" positioning.
- **Complexity:** L
- **Verdict:** **MVP**, scoped to user sources plus optional offline corpus.

### C8. Automatic animated maps
- **Problem:** History, geography and news niches need maps. No competitor offers data-driven maps (unverified gap). Stock and AI images of maps are often inaccurate.
- **Feature:** Detect places and routes in the script, then render an animated map:
  - fly-to and zoom
  - route lines drawn over time
  - pulsing markers and region highlights
  
  It uses offline vector or raster geodata. The data licence is to be confirmed, for example a Natural Earth-class public domain dataset.
- **Value:** Accurate, cinematic geography.
- **CPU:** 🟢 Vector rendering to frames. Geocoding uses a bundled gazetteer.
- **Differentiation:** Unique among competitors.
- **Complexity:** M–L
- **Verdict:** Post-MVP v1.1. A basic static-to-zoom map could make the MVP if time allows.

### C9. Intelligent infographics
- **Problem:** Numbers spoken over unrelated stock footage. "Generic" visuals. YouTube's policy wants "educational value".
- **Feature:** Detect numbers, comparisons, rankings and processes in the script. Render animated bar, line or pie charts, stat counters, comparisons and step diagrams using the Story DNA palette.
- **Value:** Explainer-grade clarity.
- **CPU:** 🟢
- **Differentiation:** Unique as an automatic feature.
- **Complexity:** M
- **Verdict:** **MVP** (stat counter, bar chart, timeline). The rest post-MVP.

### C10. Content repurposing (multiple lengths and aspect ratios)
- **Problem:**
  - OpusClip is built entirely on long-to-short repurposing, and multi-ratio reframe is gated to Pro.
  - Pictory and Kapwing offer ratios, but length variants require manual work.
- **Feature:** From one project, produce 15s, 30s and 60s cuts using script compression that keeps locked lines. Export 9:16, 1:1, 16:9 and 4:5 with layout-aware recomposition of the 2.5D layers, captions and infographics.
- **Value:** One story feeds every channel.
- **CPU:** 🟡 for LLM condensation. Re-layout is 🟢.
- **Differentiation:** Layer-aware recomposition. Graphics are redrawn, not cropped.
- **Complexity:** M
- **Verdict:** Post-MVP v1.1. Multi-ratio export is in the MVP.

### C11. Narrative pacing analysis
- **Problem:** "Scripts pretty weak and repetitive" (AutoShorts). Retention depends on pacing. No competitor surfaces pacing metrics (Opus's virality score applies to clips only).
- **Feature:** A visual pacing graph showing:
  - words per second and scene length
  - visual-change frequency
  - hook timing and payoff placement
  - open loops and dead zones
  
  It suggests specific fixes, such as "scene 4 is 9 s with no visual change".
- **Value:** Teaches craft and raises retention.
- **CPU:** 🟢 Mostly heuristics. An optional LLM critique is 🟡.
- **Differentiation:** Craft tooling, not a black-box score.
- **Complexity:** M
- **Verdict:** Post-MVP. Simple heuristics are in the MVP as warnings.

### C12. Visual memory / asset reuse
- **Problem:** Regenerating similar images is slow on CPU. Channels look inconsistent.
- **Feature:** Every generated or imported asset is embedded and tagged with prompt, seed, style and characters. New scenes first look for reusable assets. Users can mark "canonical" assets (character sheets, locations).
- **Value:** Speed, consistency and a growing channel library.
- **CPU:** 🟢 This is a large CPU *saving*.
- **Differentiation:** Turns local storage into an advantage.
- **Complexity:** M
- **Verdict:** **MVP-lite**, together with O12.

### C13. Creator workspace
- **Problem:** Cloud tools lose projects (OpusClip free deletes progress after 3 days, Kapwing has 3-day storage), and work is scattered.
- **Feature:** A local dashboard covering projects, series, Story DNA profiles, asset library, render queue and export history, with search and tags.
- **Value:** An organised production studio.
- **CPU:** 🟢
- **Differentiation:** Local and permanent.
- **Complexity:** M
- **Verdict:** **MVP** (basic).

### C14. Template marketplace foundation (no payments)
- **Problem:** Templates are overused and paywalled ("premium templates" on CapCut Pro and others). Users want community styles.
- **Feature:** An import/export format for Story DNA, caption styles, motion presets and visual-type themes, with a manifest and licence field. A Git-based or static community index comes later. No payments.
- **Value:** A community ecosystem and network effects for open source.
- **CPU:** 🟢
- **Differentiation:** Open and forkable. Licences are explicit.
- **Complexity:** S for the format, M for the index.
- **Verdict:** The format is in the MVP. The index is post-MVP.

### C15. Multi-episode continuity
Merged with C3. It differs from C3 in scope: narrative arcs across a season.
- **Problem:** Microdrama and serialized formats are rising (invideo markets "binge-worthy series"), but no tool tracks arcs.
- **Feature:**
  - Season planner: arc beats, per-episode cliffhangers and "previously on" recap generation.
  - Episode-to-episode callbacks drawn from the series bible.
- **Value:** Serialized storytelling at faceless scale.
- **CPU:** 🟡 LLM.
- **Differentiation:** Unique.
- **Complexity:** L
- **Verdict:** Post-MVP v1.2, building on the C3 bible.

---

## Part 3 — Prioritisation

Scoring: Evidence strength (E), Differentiation (D) and CPU fit (F) are each rated 1–3. Cost (K) runs from S=3 to L=1. Total = E+D+F+K, maximum 12.

| # | Opportunity | E | D | F | K | Total | Phase |
|---|---|---|---|---|---|---|---|
| O3 | Cinematic 2.5D motion | 3 | 3 | 2 | 1 | 9 | **MVP** (core identity) |
| C4 + O1 | Scene regen + Script Lock | 3 | 2 | 3 | 2 | 10 | **MVP** |
| O2 / O14 | Free re-rolls + draft animatic | 3 | 2 | 3 | 2 | 10 | **MVP** |
| C1 | Story DNA | 2 | 3 | 3 | 2 | 10 | **MVP** |
| C2 + O10 + C9 | Visual Intelligence (image, kinetic type, timeline, stat/bar) | 2 | 3 | 3 | 1 | 9 | **MVP** (incremental) |
| C7 + O5 | Fact checker + source-grounded script | 3 | 3 | 2 | 1 | 9 | **MVP** (user sources) |
| C5 | Hook Lab | 2 | 3 | 2 | 2 | 9 | **MVP** |
| C6 + C3 | Series Factory + series bible | 3 | 2 | 2 | 2 | 9 | **MVP** |
| O6 | Caption presets + SRT/VTT/ASS | 3 | 1 | 3 | 2 | 9 | MVP (table stakes) |
| O7 / C13 | Local projects, resumable renders, workspace | 3 | 2 | 3 | 2 | 10 | MVP (foundation) |
| O15 | Hardware profiles + model downloader | 2 | 2 | 3 | 2 | 9 | MVP (foundation) |
| O4 | Originality guard | 3 | 3 | 3 | 2 | 11 | v1.1 (needs a series history to score against) |
| C12 / O12 | Visual memory + semantic library | 2 | 2 | 3 | 2 | 9 | v1.1 |
| C8 | Animated maps | 2 | 3 | 3 | 1 | 9 | v1.1 |
| C10 | Repurposing (lengths and ratios) | 2 | 2 | 2 | 2 | 8 | v1.1 |
| C11 | Pacing analysis | 2 | 2 | 3 | 2 | 9 | v1.1 |
| O9 | Voice direction | 2 | 2 | 3 | 2 | 9 | v1.1 |
| O13 | Platform-safe presets | 1 | 1 | 3 | 3 | 8 | v1.1 |
| O16 / O17 | Provenance ledger, rights-clean music | 2 | 2 | 3 | 2 | 9 | v1.1 |
| O18 | Multilingual versioning | 2 | 1 | 2 | 2 | 7 | v1.2 |
| C15 | Multi-episode arcs | 1 | 3 | 2 | 1 | 7 | v1.2 |
| C14 | Template marketplace foundation | 1 | 2 | 3 | 3 | 9 | Format in MVP, index v1.2 |
| O8 | Clarifying-question brief | 2 | 1 | 3 | 3 | 9 | MVP (cheap) |
| O11 | Open project schema | 1 | 2 | 3 | 3 | 9 | MVP (architecture) |
| O19 | Accessibility pack | 1 | 2 | 3 | 3 | 9 | v1.1 |
| O20 | BYO-provider connectors | 2 | 1 | 3 | 2 | 8 | v1.2 |

## Recommended eight MVP opportunities

1. **Cinematic 2.5D motion engine (O3).** This is the visual identity and the direct answer to "static slideshow" complaints and YouTube policy.
2. **Storyboard with single-scene regeneration and Script Lock (C4 + O1).** These answer the "AI ignores me" and "pay for its mistakes" complaints.
3. **Free local re-rolls with a draft animatic (O2 + O14).** This turns the credit-drain complaint into a selling point.
4. **Story DNA (C1).** A reusable creative identity per channel.
5. **Visual Intelligence, MVP set (C2 + O10 + C9).** Image-with-motion, kinetic type, timeline and stat or bar infographics, chosen per scene.
6. **Story fact checker with source-grounded scripting (C7 + O5).** The unique "fact-aware" pillar.
7. **Hook Lab (C5).** Rendered hook variants.
8. **Series Factory with a series bible (C6 + C3-lite).** Serialized output without autopilot sameness.

**Foundations that ship alongside them:**
- local project format with resumable renders (O7, O11)
- caption presets with SRT export (O6)
- hardware profiles (O15)
- basic workspace (C13)
