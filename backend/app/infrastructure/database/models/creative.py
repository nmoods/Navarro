"""Reusable creative identity: Story DNA, voice profiles, templates, music and sound effects."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, JsonType, Timestamps, UUIDPrimaryKey


class StoryDnaProfile(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "story_dna_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    visual_style: Mapped[str] = mapped_column(String(40), nullable=False)
    style_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    color_palette: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    typography: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    voice_id: Mapped[str] = mapped_column(String(60), nullable=False)
    voice_speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    caption_style: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    animation_preferences: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    music_preferences: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    brand: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    visual_references: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    tone: Mapped[str] = mapped_column(String(30), default="documentary", nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_story_dna_user_name"),)


class VoiceProfile(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "voice_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    voice_id: Mapped[str] = mapped_column(String(120), nullable=False)
    speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    settings: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_voice_profile_user_name"),)


class Template(UUIDPrimaryKey, Timestamps, Base):
    """Foundation for community templates. No payments: templates are free to share or keep private."""

    __tablename__ = "templates"

    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    config: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)

    __table_args__ = (Index("ix_templates_public_category", "is_public", "category"),)


class MusicTrack(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "music_tracks"

    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    mood: Mapped[str] = mapped_column(String(30), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    generator_params: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    license_note: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class SoundEffectAsset(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "sound_effects"

    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    license_note: Mapped[str] = mapped_column(String(255), default="", nullable=False)
