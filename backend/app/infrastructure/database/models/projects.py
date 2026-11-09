"""Projects and their story artefacts: settings, script versions, storyboards, scenes, scene assets."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base, JsonType, Timestamps, UTCDateTime, UUIDPrimaryKey, utcnow


class Project(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "projects"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    series_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("content_series.id", ondelete="SET NULL")
    )
    story_dna_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("story_dna_profiles.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    thumbnail_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    last_error: Mapped[str | None] = mapped_column(Text)

    settings: Mapped[ProjectSettings] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False, lazy="joined"
    )

    __table_args__ = (
        Index("ix_projects_user_updated", "user_id", "updated_at"),
        Index("ix_projects_series", "series_id"),
    )


class ProjectSettings(Timestamps, Base):
    __tablename__ = "project_settings"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(8), default="9:16", nullable=False)
    fps: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    platform: Mapped[str] = mapped_column(String(30), default="tiktok", nullable=False)
    visual_style: Mapped[str] = mapped_column(String(40), default="cinematic_documentary", nullable=False)
    story_tone: Mapped[str] = mapped_column(String(30), default="documentary", nullable=False)
    voice_id: Mapped[str] = mapped_column(String(120), default="am_michael", nullable=False)
    voice_speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    caption_style: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    music: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    sfx_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fact_check_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    style_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    brand: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)

    project: Mapped[Project] = relationship(back_populates="settings")


class ScriptVersion(UUIDPrimaryKey, Base):
    __tablename__ = "scripts"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    brief: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    hooks: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    selected_hook_index: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    claims: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    model: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "version", name="uq_scripts_project_version"),)


class Storyboard(UUIDPrimaryKey, Base):
    __tablename__ = "storyboards"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    script_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("scripts.id", ondelete="SET NULL"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    analysis: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    scenes: Mapped[list[Scene]] = relationship(
        back_populates="storyboard", cascade="all, delete-orphan", order_by="Scene.position"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_storyboards_project_version"),
        Index("ix_storyboards_project_current", "project_id", "is_current"),
    )


class Scene(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "scenes"

    storyboard_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    duration_override: Mapped[float | None] = mapped_column(Float)
    visual_type: Mapped[str] = mapped_column(String(30), nullable=False)
    visual_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    characters: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    camera_movement: Mapped[str] = mapped_column(String(30), nullable=False)
    effects: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    transition: Mapped[str] = mapped_column(String(20), nullable=False)
    emphasis_words: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    caption_override: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    sound_effects: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    music_cue: Mapped[str] = mapped_column(String(20), default="steady", nullable=False)
    mood: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    color_palette: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    visual_data: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    image_seed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    storyboard: Mapped[Storyboard] = relationship(back_populates="scenes")
    assets: Mapped[list[SceneAsset]] = relationship(back_populates="scene", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_scenes_storyboard_position", "storyboard_id", "position"),
        Index("ix_scenes_project", "project_id"),
    )


class SceneAsset(UUIDPrimaryKey, Base):
    """Links a generated/uploaded media asset to a scene role. ``input_hash`` drives cache reuse."""

    __tablename__ = "scene_assets"

    scene_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False
    )
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    details: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    scene: Mapped[Scene] = relationship(back_populates="assets")

    __table_args__ = (Index("ix_scene_assets_scene_role_current", "scene_id", "role", "is_current"),)
