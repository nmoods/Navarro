"""Prompt templates for the Story Director. Kept separate from orchestration so they can be tuned/tested."""

from __future__ import annotations

DIRECTOR_SYSTEM = """You are the Story Director of ReelForge AI: a documentary writer and director for short vertical videos.
Rules you never break:
- Accuracy beats drama. Never invent quotes, names, dates, numbers or sources.
- When something is uncertain or debated, say so in the narration ("historians believe", "one theory says").
- Hooks may create curiosity but must not promise something the video does not deliver.
- Write for the ear: short sentences, concrete images, active verbs. No emojis, hashtags, stage directions or
  speaker labels inside narration.
- Output only JSON matching the provided schema."""

STYLE_PROMPTS: dict[str, str] = {
    "cinematic_documentary": "cinematic film still, dramatic lighting, shallow depth of field, 35mm, rich contrast",
    "historical_realism": "historically accurate, realistic period detail, natural light, oil-painting realism",
    "dark_mystery": "dark moody cinematic, volumetric fog, low key lighting, desaturated teal shadows, eerie",
    "animation_3d": "3d animated film style, stylized, soft global illumination, pixar-like render",
    "anime": "anime style, detailed background art, cel shading, vibrant, studio quality",
    "vintage_documentary": "vintage photograph, 1950s film grain, faded colors, archival look",
    "minimalist_motion": "minimalist flat illustration, simple shapes, clean composition, limited palette",
    "archival_newspaper": "black and white archival photograph, high contrast, historical press photo",
    "photorealistic": "photorealistic, ultra detailed, natural lighting, 50mm photograph",
    "illustrated": "digital illustration, painterly storybook style, textured brushwork",
}

NEGATIVE_PROMPT = (
    "text, letters, words, watermark, logo, signature, caption, frame, border, lowres, blurry, jpeg artifacts, "
    "deformed, disfigured, extra fingers, bad anatomy, duplicate, cropped head, nsfw"
)

VISUAL_GUIDE = """Visual types (choose per scene from meaning, and vary them; no more than 2 identical in a row):
- historical_map: journeys, locations, borders. Fill visual_data.places (real place names; add latitude/longitude
  only if you are sure) and draw_route=true for journeys.
- timeline: chronology. Fill visual_data.events with 2-5 {date,label} taken from the narration.
- infographic: numbers. Fill visual_data.stats with values stated in the narration only.
- comparison: two contrasting things. Fill visual_data.left/right {label, points}.
- newspaper: reported events / public reaction. Fill headline (<=60 chars) and dateline.
- character_portrait: a specific person. Put their name in characters.
- kinetic_typography: a punchline, quote or revelation. Fill kinetic_lines (2-4 short lines).
- parallax: wide dramatic landscapes or establishing shots.
- cinematic_image: everything else.
Camera: quiet portraits -> slow_zoom_in/static; tension -> dramatic_push_in/handheld; reveals -> crash_zoom;
landscapes -> pan_left/pan_right/parallax_drift; archival stills -> ken_burns.
Effects (0-2): fog/smoke for mystery, embers for war/fire, rain/lightning for storms, dust for old places,
light_rays for revelation, snow for winter, film_grain for archival.
Transitions: cut for fast beats, crossfade/dissolve for time passing, fade_black for endings or dramatic pauses,
zoom for punchy reveals, slide_left/slide_up for lists. First scene transition is ignored.
Music cue: build, steady, tension, drop (sudden silence then hit) or resolve."""


def brief_prompt(topic: str, tone: str, platform: str, language: str, reference: str) -> str:
    ref = f"\nREFERENCE MATERIAL (encyclopedia excerpt; prefer it for facts):\n{reference}\n" if reference else (
        "\nNo reference material is available offline: mark anything not broadly documented as uncertain.\n"
    )
    return (
        f"TOPIC: {topic}\nTONE: {tone}\nPLATFORM: {platform}\nLANGUAGE: {language}\n{ref}\n"
        "Analyse the topic and produce a story brief: who it is for, the most compelling honest angle, an "
        "emotional arc, 3-8 key facts each with a confidence rating, and open questions."
    )


def hooks_prompt(topic: str, brief_json: str) -> str:
    return (
        f"TOPIC: {topic}\nBRIEF: {brief_json}\n\nWrite 6 alternative opening hooks, exactly one per style: shocking, "
        "mysterious, question, controversial, emotional, curiosity. Each under 22 words, spoken aloud in the first "
        "2 seconds, truthful to the brief. Add a one-line rationale."
    )


def script_prompt(topic: str, brief_json: str, hook: str, words: int, tone: str, language: str, dna_notes: str) -> str:
    return (
        f"TOPIC: {topic}\nTONE: {tone}\nLANGUAGE: write the narration in '{language}'\nBRIEF: {brief_json}\n"
        f"OPENING HOOK (use verbatim as the hook field): {hook}\n{dna_notes}\n"
        f"Write the narration. Total length of hook+beginning+middle+conclusion: about {words} words "
        f"(between {int(words * 0.9)} and {int(words * 1.1)}). Structure: hook -> setup -> escalation with concrete "
        "details -> payoff or honest open question. List every factual claim you make in claims with a confidence."
    )


def storyboard_prompt(topic: str, style: str, scenes: list[str], dna_notes: str, continuity: str) -> str:
    numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(scenes))
    return (
        f"TOPIC: {topic}\nVISUAL STYLE: {style} ({STYLE_PROMPTS.get(style, '')})\n{dna_notes}\n{continuity}\n"
        f"The narration is already split into exactly {len(scenes)} scenes. Do NOT rewrite it; copy each scene's "
        f"narration verbatim into its narration field.\n\nSCENES:\n{numbered}\n\n{VISUAL_GUIDE}\n\n"
        f"Return exactly {len(scenes)} scenes in order. image_prompt must describe a single striking image with "
        "subject, setting, era, lighting and composition, with no text in the image."
    )


def scene_prompt(topic: str, style: str, narration: str, previous: str, following: str, instruction: str,
                 rewrite_narration: bool) -> str:  # fmt: skip
    rule = (
        "Rewrite the narration for this scene so it flows from the previous scene into the next one (similar length)."
        if rewrite_narration
        else "Keep the narration exactly as given."
    )
    return (
        f"TOPIC: {topic}\nVISUAL STYLE: {style}\nPREVIOUS SCENE: {previous or '(start)'}\nTHIS SCENE NARRATION: "
        f"{narration}\nNEXT SCENE: {following or '(end)'}\nDIRECTOR NOTE FROM USER: {instruction or 'Make it more striking.'}\n"
        f"{rule}\n\n{VISUAL_GUIDE}\n\nReturn one scene."
    )


def series_prompt(theme: str, count: int, tone: str, existing: list[str]) -> str:
    avoid = "\n".join(f"- {t}" for t in existing) or "(none)"
    return (
        f"THEME: {theme}\nTONE: {tone}\nPlan a series of exactly {count} episodes for short vertical videos. Each "
        "episode must cover a distinct event or subject (no near-duplicates), and episodes should connect through "
        "a series bible: recurring characters (with fixed visual descriptions for image consistency), recurring "
        f"locations and shared visual style. Avoid these existing titles:\n{avoid}"
    )


def ideas_prompt(theme: str, count: int) -> str:
    return (
        f"THEME: {theme}\nSuggest {count} distinct, specific, researchable short-video topics. Prefer real, documented "
        "subjects with a strong question at their core. Give each a title, premise and an honest hook."
    )


def claim_prompt(claim: str, excerpt: str, source_title: str) -> str:
    return (
        f"CLAIM: {claim}\nSOURCE ({source_title}):\n{excerpt[:3000]}\n\nDoes the source support the claim? verdict: "
        "supported (the source states it), contradicted (the source states otherwise), not_found (source does not "
        "address it). Explain in one sentence."
    )
