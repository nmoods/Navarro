"""Series Factory and Content Planner tables."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base, JsonType, Timestamps, UUIDPrimaryKey


class ContentSeries(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "content_series"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    story_dna_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("story_dna_profiles.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    theme: Mapped[str] = mapped_column(Text, nullable=False)
    episode_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="planning", nullable=False)
    bible: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    settings: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)

    episodes: Mapped[list[SeriesEpisode]] = relationship(
        back_populates="series", cascade="all, delete-orphan", order_by="SeriesEpisode.position"
    )

    __table_args__ = (Index("ix_content_series_user_created", "user_id", "created_at"),)


class SeriesEpisode(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "series_episodes"

    series_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("content_series.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    premise: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hook: Mapped[str] = mapped_column(Text, default="", nullable=False)
    continuity_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default="planned", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)

    series: Mapped[ContentSeries] = relationship(back_populates="episodes")

    __table_args__ = (UniqueConstraint("series_id", "position", name="uq_series_episodes_position"),)


class ContentIdea(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "content_ideas"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="idea", nullable=False)
    scheduled_for: Mapped[date | None] = mapped_column(Date)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="SET NULL"))
    series_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("content_series.id", ondelete="SET NULL"))

    __table_args__ = (Index("ix_content_ideas_user_scheduled", "user_id", "scheduled_for"),)
