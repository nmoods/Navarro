"""Validated structures produced by the AI Story Director.

These models double as JSON schemas sent to the LLM (Ollama structured outputs), so field
descriptions are written as instructions and the shapes are kept flat for small local models.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import (
    CameraMove,
    ClaimConfidence,
    ClaimVerdict,
    Effect,
    HookStyle,
    MusicMood,
    SoundEffect,
    Transition,
    VisualType,
)

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class Claim(StrictModel):
    text: str = Field(description="One factual statement made in the script", max_length=400)
    confidence: ClaimConfidence = Field(
        description="well_established only for facts broadly documented by historians/scientists"
    )
    note: str = Field(default="", description="Why it is uncertain or debated, if applicable", max_length=400)
    verdict: ClaimVerdict = ClaimVerdict.UNVERIFIED
    sources: list[str] = Field(default_factory=list, max_length=5)


class Hook(StrictModel):
    style: HookStyle
    text: str = Field(description="Spoken opening line, under 22 words, no clickbait lies", max_length=220)
    rationale: str = Field(default="", max_length=240)


class Script(StrictModel):
    title: str = Field(description="Short punchy video title, under 70 characters", max_length=90)
    hook: str = Field(max_length=240)
    beginning: str = Field(description="Setup that grounds the viewer", max_length=1500)
    middle: str = Field(description="Escalation and key details", max_length=2500)
    conclusion: str = Field(description="Payoff or open question; no false certainty", max_length=1500)
    claims: list[Claim] = Field(default_factory=list, max_length=15)

    @property
    def full_text(self) -> str:
        return " ".join(p.strip() for p in (self.hook, self.beginning, self.middle, self.conclusion) if p.strip())


class Place(StrictModel):
    name: str = Field(max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class TimelineEvent(StrictModel):
    label: str = Field(max_length=80)
    date: str = Field(description="Year or date text, e.g. '1587' or 'Aug 1590'", max_length=30)


class Statistic(StrictModel):
    label: str = Field(max_length=60)
    value: float
    unit: str = Field(default="", max_length=16)


class ComparisonSide(StrictModel):
    label: str = Field(max_length=40)
    points: list[str] = Field(default_factory=list, max_length=4)


class VisualData(StrictModel):
    """Structured data for procedural visuals. Fill only what the chosen visual_type needs."""

    places: list[Place] = Field(default_factory=list, max_length=6)
    draw_route: bool = False
    events: list[TimelineEvent] = Field(default_factory=list, max_length=6)
    stats: list[Statistic] = Field(default_factory=list, max_length=5)
    left: ComparisonSide | None = None
    right: ComparisonSide | None = None
    headline: str = Field(default="", max_length=90)
    dateline: str = Field(default="", max_length=60)
    kinetic_lines: list[str] = Field(default_factory=list, max_length=4)


VISUAL_TYPE_HELP = (
    "Pick the visual that best explains this moment: historical_map for places/journeys, "
    "timeline for chronology, infographic for numbers, comparison for contrasts, newspaper for "
    "reported events, character_portrait for a person, kinetic_typography for a punchline/quote, "
    "parallax for dramatic landscapes, cinematic_image otherwise"
)


class SceneDraft(StrictModel):
    title: str = Field(max_length=80)
    narration: str = Field(description="Exact words the narrator speaks in this scene", max_length=700)
    visual_type: VisualType = Field(description=VISUAL_TYPE_HELP)
    visual_description: str = Field(max_length=500)
    image_prompt: str = Field(
        description="Stable-Diffusion prompt: subject, setting, lighting, lens, style. No text/letters.",
        max_length=500,
    )
    characters: list[str] = Field(default_factory=list, max_length=4)
    camera_movement: CameraMove
    effects: list[Effect] = Field(default_factory=list, max_length=3)
    transition: Transition = Field(description="Transition INTO this scene from the previous one")
    emphasis_words: list[str] = Field(
        default_factory=list, description="1-3 words from the narration to highlight", max_length=4
    )
    sound_effects: list[SoundEffect] = Field(default_factory=list, max_length=2)
    music_cue: str = Field(default="steady", description="build | steady | drop | tension | resolve", max_length=20)
    mood: str = Field(max_length=40)
    color_palette: list[str] = Field(default_factory=list, description="3 hex colours like #1a1a2e", max_length=4)
    visual_data: VisualData = Field(default_factory=VisualData)

    @field_validator("color_palette")
    @classmethod
    def _valid_hex(cls, value: list[str]) -> list[str]:
        return [c for c in value if _HEX.match(c)]

    @field_validator("emphasis_words")
    @classmethod
    def _clean_words(cls, value: list[str]) -> list[str]:
        return [w.strip(" .,!?;:\"'").lower() for w in value if w.strip(" .,!?;:\"'")]


class StoryboardDraft(StrictModel):
    scenes: list[SceneDraft] = Field(min_length=3, max_length=14)


# -- One-pass story and compact storyboard ---------------------------------------------------------------
# On a CPU a small model writes ~8-10 tokens/s, so every field the model has to emit costs time. The story
# is written in one call (hooks + narration + claims) and the storyboard asks only for direction:
# narration is fixed before that step, so it is never echoed back.


class ClaimDraft(StrictModel):
    text: str = Field(description="One factual statement made in the narration", max_length=300)
    confidence: ClaimConfidence

    def to_claim(self) -> Claim:
        return Claim(text=self.text, confidence=self.confidence)


class HookLine(StrictModel):
    style: HookStyle
    text: str = Field(description="Spoken opening line, under 22 words, truthful", max_length=220)


class StoryDraft(StrictModel):
    title: str = Field(description="Short punchy video title, under 70 characters", max_length=90)
    music_mood: MusicMood
    hooks: list[HookLine] = Field(
        min_length=1, max_length=3,
        description="3 alternative opening lines, each in a different style. The first one opens the video.",
    )  # fmt: skip
    beginning: str = Field(description="Setup that grounds the viewer", max_length=1500)
    middle: str = Field(description="Escalation and key details", max_length=2500)
    conclusion: str = Field(description="Payoff or open question; no false certainty", max_length=1500)
    claims: list[ClaimDraft] = Field(min_length=1, max_length=4)

    def to_script(self) -> Script:
        return Script(title=self.title, hook=self.hooks[0].text, beginning=self.beginning, middle=self.middle,
                      conclusion=self.conclusion, claims=[c.to_claim() for c in self.claims])  # fmt: skip

    def to_hooks(self) -> list[Hook]:
        return [Hook(style=h.style, text=h.text) for h in self.hooks]


class ScenePlan(StrictModel):
    title: str = Field(description="2-5 word scene title", max_length=60)
    visual_type: VisualType = Field(description=VISUAL_TYPE_HELP)
    image_prompt: str = Field(
        description="Stable-Diffusion prompt: subject, setting, era, lighting, composition. No text/letters.",
        max_length=400,
    )
    camera_movement: CameraMove
    effects: list[Effect] = Field(default_factory=list, max_length=2)
    transition: Transition = Field(description="Transition INTO this scene from the previous one")
    emphasis_words: list[str] = Field(default_factory=list, description="1-3 words from the narration to highlight", max_length=3)
    sound_effects: list[SoundEffect] = Field(default_factory=list, max_length=2)
    music_cue: str = Field(default="steady", description="build | steady | drop | tension | resolve", max_length=20)
    characters: list[str] = Field(default_factory=list, max_length=3)
    visual_data: VisualData | None = Field(default=None, description="Only for map, timeline, infographic, comparison, newspaper or kinetic_typography")

    def to_draft(self, narration: str) -> SceneDraft:
        data = self.model_dump(exclude={"visual_data"})
        return SceneDraft.model_validate(data | {
            "narration": narration, "visual_description": self.image_prompt, "mood": self.music_cue,
            "visual_data": (self.visual_data or VisualData()).model_dump(),
        })  # fmt: skip


class StoryboardPlan(StrictModel):
    scenes: list[ScenePlan] = Field(min_length=3, max_length=14)


class EpisodeIdea(StrictModel):
    title: str = Field(max_length=90)
    premise: str = Field(max_length=400)
    hook: str = Field(max_length=220)
    continuity_note: str = Field(default="", description="How it connects to the rest of the series", max_length=300)


class SeriesCharacter(StrictModel):
    name: str = Field(max_length=60)
    visual_description: str = Field(description="Fixed appearance reused in every image prompt", max_length=300)


class SeriesPlan(StrictModel):
    series_title: str = Field(max_length=90)
    logline: str = Field(max_length=300)
    visual_style_notes: str = Field(max_length=300)
    recurring_characters: list[SeriesCharacter] = Field(default_factory=list, max_length=6)
    recurring_locations: list[str] = Field(default_factory=list, max_length=8)
    episodes: list[EpisodeIdea] = Field(min_length=1, max_length=30)


class ClaimCheck(StrictModel):
    verdict: ClaimVerdict
    explanation: str = Field(max_length=400)


class TopicIdeas(StrictModel):
    ideas: list[EpisodeIdea] = Field(min_length=1, max_length=20)


def words_for_duration(seconds: int, words_per_second: float = 2.45) -> int:
    """Narration budget for a target duration at a natural TTS pace."""
    return max(20, int(seconds * words_per_second))


def scene_count_for_duration(seconds: int) -> int:
    return max(4, min(12, round(seconds / 6.5)))
