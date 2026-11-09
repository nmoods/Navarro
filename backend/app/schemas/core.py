"""API request/response schemas (validation at the HTTP boundary)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.domain.enums import (
    AspectRatio,
    CameraMove,
    CaptionAnimation,
    CaptionPosition,
    Effect,
    IdeaStatus,
    MusicMood,
    Platform,
    SoundEffect,
    StoryTone,
    Transition,
    VisualStyle,
    VisualType,
)
from app.media.fonts import AVAILABLE_FONTS

Hex = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


# ---- auth -----------------------------------------------------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: ShortText

    @field_validator("password")
    @classmethod
    def _strength(cls, v: str) -> str:
        classes = sum(any(f(c) for c in v) for f in (str.islower, str.isupper, str.isdigit, lambda c: not c.isalnum()))
        if classes < 3:
            raise ValueError("Use at least three of: lowercase, uppercase, digits, symbols")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type label
    expires_in: int


class UserOut(Out):
    id: uuid.UUID
    email: str
    display_name: str
    auth_provider: str
    default_story_dna_id: uuid.UUID | None = None
    created_at: datetime


class ProfileUpdate(BaseModel):
    display_name: ShortText | None = None
    default_story_dna_id: uuid.UUID | None = None
    preferences: dict | None = None


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


# ---- captions & project settings -------------------------------------------------------------------------
class CaptionStyleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    animation: CaptionAnimation | None = None
    font: str | None = None
    font_weight: int | None = Field(default=None, ge=100, le=900)
    size: float | None = Field(default=None, ge=0.03, le=0.12)
    color: Hex | None = None
    highlight_color: Hex | None = None
    emphasis_color: Hex | None = None
    stroke_color: Hex | None = None
    stroke_width: float | None = Field(default=None, ge=0, le=0.3)
    background: Literal["none", "box", "shadow"] | None = None
    background_color: Hex | None = None
    position: CaptionPosition | None = None
    vertical_offset: float | None = Field(default=None, ge=-0.3, le=0.3)
    uppercase: bool | None = None
    max_words: int | None = Field(default=None, ge=1, le=8)
    enabled: bool | None = None
    offset_ms: int | None = Field(default=None, ge=-2000, le=2000)

    @field_validator("font")
    @classmethod
    def _font(cls, v: str | None) -> str | None:
        if v is not None and v not in AVAILABLE_FONTS:
            raise ValueError(f"Unknown font; choose one of {', '.join(AVAILABLE_FONTS)}")
        return v

    def clean(self) -> dict:
        return self.model_dump(exclude_none=True, mode="json")


class MusicSettings(BaseModel):
    enabled: bool = True
    mood: MusicMood | None = None
    volume_db: float = Field(default=-20, ge=-40, le=-6)
    track_id: uuid.UUID | None = None


class ProjectCreate(BaseModel):
    topic: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    title: ShortText | None = None
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")] = "en"
    duration_seconds: Literal[30, 45, 60, 90] = 60
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    fps: Literal[24, 25, 30, 60] = 30
    platform: Platform = Platform.TIKTOK
    visual_style: VisualStyle | None = None
    story_tone: StoryTone | None = None
    voice_id: Annotated[str, StringConstraints(pattern=r"^[a-z_:.,0-9]{2,120}$")] | None = None
    voice_speed: float | None = Field(default=None, ge=0.5, le=2.0)
    caption_style: CaptionStyleIn = Field(default_factory=CaptionStyleIn)
    music: MusicSettings = Field(default_factory=MusicSettings)
    sfx_enabled: bool = True
    fact_check_enabled: bool = True
    story_dna_id: uuid.UUID | None = None
    auto_produce: bool = False
    hook_style: str | None = None


class ProjectSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: ShortText | None = None
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")] | None = None
    duration_seconds: Literal[30, 45, 60, 90] | None = None
    aspect_ratio: AspectRatio | None = None
    fps: Literal[24, 25, 30, 60] | None = None
    platform: Platform | None = None
    visual_style: VisualStyle | None = None
    story_tone: StoryTone | None = None
    voice_id: Annotated[str, StringConstraints(pattern=r"^[a-z_:.,0-9]{2,120}$")] | None = None
    voice_speed: float | None = Field(default=None, ge=0.5, le=2.0)
    caption_style: CaptionStyleIn | None = None
    music: MusicSettings | None = None
    sfx_enabled: bool | None = None
    fact_check_enabled: bool | None = None
    story_dna_id: uuid.UUID | None = None
    brand_handle: Annotated[str, StringConstraints(max_length=40)] | None = None


class ProjectSettingsOut(Out):
    language: str
    duration_seconds: int
    aspect_ratio: str
    fps: int
    platform: str
    visual_style: str
    story_tone: str
    voice_id: str
    voice_speed: float
    caption_style: dict
    music: dict
    sfx_enabled: bool
    fact_check_enabled: bool
    brand: dict


class ProjectOut(Out):
    id: uuid.UUID
    title: str
    topic: str
    status: str
    series_id: uuid.UUID | None
    story_dna_id: uuid.UUID | None
    thumbnail_url: str | None = None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    settings: ProjectSettingsOut | None = None


# ---- scenes ----------------------------------------------------------------------------------------------
class SceneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: ShortText | None = None
    narration: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)] | None = None
    duration_override: float | None = Field(default=None, ge=0, le=30)
    visual_type: VisualType | None = None
    visual_description: Annotated[str, StringConstraints(max_length=600)] | None = None
    image_prompt: Annotated[str, StringConstraints(max_length=600)] | None = None
    characters: list[Annotated[str, StringConstraints(max_length=60)]] | None = Field(default=None, max_length=4)
    camera_movement: CameraMove | None = None
    effects: list[Effect] | None = Field(default=None, max_length=3)
    transition: Transition | None = None
    emphasis_words: list[Annotated[str, StringConstraints(max_length=40)]] | None = Field(default=None, max_length=6)
    caption_override: CaptionStyleIn | None = None
    sound_effects: list[SoundEffect] | None = Field(default=None, max_length=3)
    music_cue: Literal["build", "steady", "tension", "drop", "resolve", "calm"] | None = None
    mood: Annotated[str, StringConstraints(max_length=40)] | None = None
    color_palette: list[Hex] | None = Field(default=None, max_length=4)
    visual_data: dict | None = None


class SceneCreate(SceneUpdate):
    narration: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]
    position: int | None = Field(default=None, ge=0)


class SceneAssetOut(BaseModel):
    id: uuid.UUID
    role: str
    media_asset_id: uuid.UUID
    provider: str
    source: str
    url: str
    is_current: bool
    locked: bool = False
    created_at: datetime
    details: dict = {}


class SceneOut(Out):
    id: uuid.UUID
    position: int
    title: str
    narration: str
    duration_override: float | None
    visual_type: str
    visual_description: str
    image_prompt: str
    characters: list
    camera_movement: str
    effects: list
    transition: str
    emphasis_words: list
    caption_override: dict
    sound_effects: list
    music_cue: str
    mood: str
    color_palette: list
    visual_data: dict
    updated_at: datetime
    image: SceneAssetOut | None = None
    narration_audio: SceneAssetOut | None = None
    narration_seconds: float | None = None
    caption_timing: str | None = None


class StoryboardOut(BaseModel):
    id: uuid.UUID
    version: int
    analysis: dict
    scenes: list[SceneOut]


class ScriptOut(Out):
    id: uuid.UUID
    version: int
    title: str
    brief: dict
    hooks: list
    selected_hook_index: int | None
    content: dict
    full_text: str
    claims: list
    model: str | None
    created_at: datetime


class ReorderIn(BaseModel):
    scene_ids: list[uuid.UUID] = Field(min_length=1, max_length=40)


class RegenerateSceneIn(BaseModel):
    parts: list[Literal["visual_plan", "narration", "image"]] = Field(default_factory=lambda: ["image"], min_length=1)
    instruction: Annotated[str, StringConstraints(max_length=400)] = ""


class SelectHookIn(BaseModel):
    hook_index: int = Field(ge=0, le=10)


class ProduceIn(BaseModel):
    quality: Literal["draft", "final"] = "final"


# ---- jobs & exports ---------------------------------------------------------------------------------------
class JobOut(Out):
    id: uuid.UUID
    job_type: str
    status: str
    progress: float
    stage_message: str
    project_id: uuid.UUID | None
    series_id: uuid.UUID | None
    scene_id: uuid.UUID | None
    parent_job_id: uuid.UUID | None
    error: str | None
    attempts: int
    result: dict
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobLogOut(Out):
    level: str
    stage: str
    message: str
    created_at: datetime


class ExportOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_title: str | None = None
    quality: str
    aspect_ratio: str
    width: int
    height: int
    fps: int
    duration_seconds: float
    video_url: str
    download_url: str
    thumbnail_url: str | None
    created_at: datetime
    details: dict


class MediaOut(BaseModel):
    id: uuid.UUID
    kind: str
    source: str
    mime_type: str
    size_bytes: int
    original_name: str | None
    width: int | None
    height: int | None
    duration_seconds: float | None
    url: str
    created_at: datetime


# ---- creative ----------------------------------------------------------------------------------------------
class StoryDnaIn(BaseModel):
    name: ShortText
    description: Annotated[str, StringConstraints(max_length=600)] = ""
    visual_style: VisualStyle = VisualStyle.CINEMATIC_DOCUMENTARY
    style_prompt: Annotated[str, StringConstraints(max_length=400)] = ""
    color_palette: list[Hex] = Field(default_factory=list, max_length=5)
    typography: dict = Field(default_factory=dict)
    voice_id: Annotated[str, StringConstraints(pattern=r"^[a-z_:.,0-9]{2,120}$")] = "am_michael"
    voice_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    caption_style: CaptionStyleIn = Field(default_factory=CaptionStyleIn)
    animation_preferences: dict = Field(default_factory=dict)
    music_preferences: MusicSettings = Field(default_factory=MusicSettings)
    brand: dict = Field(default_factory=dict)
    visual_references: list[uuid.UUID] = Field(default_factory=list, max_length=8)
    tone: StoryTone = StoryTone.DOCUMENTARY

    @field_validator("brand", "typography", "animation_preferences")
    @classmethod
    def _small(cls, v: dict) -> dict:
        if len(str(v)) > 2000:
            raise ValueError("too large")
        return v


class StoryDnaOut(Out):
    id: uuid.UUID
    name: str
    description: str
    visual_style: str
    style_prompt: str
    color_palette: list
    typography: dict
    voice_id: str
    voice_speed: float
    caption_style: dict
    animation_preferences: dict
    music_preferences: dict
    brand: dict
    visual_references: list
    tone: str
    created_at: datetime
    updated_at: datetime


class VoiceOut(BaseModel):
    id: str
    name: str
    language: str
    gender: str
    accent: str


class VoicePreviewIn(BaseModel):
    voice_id: Annotated[str, StringConstraints(pattern=r"^[a-z_:.,0-9]{2,120}$")]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")] = "en"


class VoiceProfileIn(BaseModel):
    name: ShortText
    voice_id: Annotated[str, StringConstraints(pattern=r"^[a-z_:.,0-9]{2,120}$")]
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    settings: dict = Field(default_factory=dict)


class VoiceProfileOut(Out):
    id: uuid.UUID
    name: str
    provider: str
    voice_id: str
    speed: float
    settings: dict
    created_at: datetime


class TemplateIn(BaseModel):
    name: ShortText
    description: Annotated[str, StringConstraints(max_length=600)] = ""
    category: Annotated[str, StringConstraints(max_length=40)] = "general"
    is_public: bool = False
    project_id: uuid.UUID | None = None
    config: dict = Field(default_factory=dict)


class TemplateOut(Out):
    id: uuid.UUID
    name: str
    description: str
    category: str
    is_public: bool
    is_builtin: bool
    version: str
    config: dict
    owned: bool = False
    created_at: datetime


class MusicTrackOut(BaseModel):
    id: uuid.UUID | None
    name: str
    mood: str
    source: str
    license_note: str
    preview_url: str | None


# ---- planning ----------------------------------------------------------------------------------------------
class SeriesCreate(BaseModel):
    theme: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    episode_count: int = Field(ge=1, le=20)
    duration_seconds: Literal[30, 45, 60, 90] = 60
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL
    platform: Platform = Platform.TIKTOK
    visual_style: VisualStyle | None = None
    story_tone: StoryTone = StoryTone.DOCUMENTARY
    voice_id: Annotated[str, StringConstraints(pattern=r"^[a-z_:.,0-9]{2,120}$")] | None = None
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")] = "en"
    story_dna_id: uuid.UUID | None = None


class EpisodeOut(Out):
    id: uuid.UUID
    position: int
    title: str
    premise: str
    hook: str
    continuity_note: str
    project_id: uuid.UUID | None
    status: str
    error: str | None


class EpisodeUpdate(BaseModel):
    title: ShortText | None = None
    premise: Annotated[str, StringConstraints(max_length=600)] | None = None
    hook: Annotated[str, StringConstraints(max_length=300)] | None = None


class SeriesOut(Out):
    id: uuid.UUID
    title: str
    theme: str
    episode_count: int
    status: str
    bible: dict
    settings: dict
    story_dna_id: uuid.UUID | None
    created_at: datetime
    episodes: list[EpisodeOut] = []


class SeriesProduceIn(BaseModel):
    episode_ids: list[uuid.UUID] | None = None
    quality: Literal["draft", "final"] = "final"


class IdeaIn(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    notes: Annotated[str, StringConstraints(max_length=2000)] = ""
    tags: list[Annotated[str, StringConstraints(max_length=30)]] = Field(default_factory=list, max_length=10)
    status: IdeaStatus = IdeaStatus.IDEA
    scheduled_for: date | None = None


class IdeaUpdate(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)] | None = None
    notes: Annotated[str, StringConstraints(max_length=2000)] | None = None
    tags: list[Annotated[str, StringConstraints(max_length=30)]] | None = Field(default=None, max_length=10)
    status: IdeaStatus | None = None
    scheduled_for: date | None = None
    clear_schedule: bool = False


class IdeaOut(Out):
    id: uuid.UUID
    title: str
    notes: str
    tags: list
    status: str
    scheduled_for: date | None
    project_id: uuid.UUID | None
    series_id: uuid.UUID | None
    created_at: datetime


class SuggestIn(BaseModel):
    theme: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)]
    count: int = Field(default=6, ge=1, le=12)
