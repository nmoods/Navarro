"""Project creation and Story DNA application (shared by the API and the Series Factory)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.domain.enums import ProjectStatus
from app.infrastructure.database.models import Project, ProjectSettings, StoryDnaProfile


@dataclass
class ProjectInput:
    topic: str
    title: str | None = None
    language: str = "en"
    duration_seconds: int = 60
    aspect_ratio: str = "9:16"
    fps: int = 30
    platform: str = "tiktok"
    visual_style: str | None = None
    story_tone: str | None = None
    voice_id: str | None = None
    voice_speed: float | None = None
    caption_style: dict = field(default_factory=dict)
    music: dict = field(default_factory=dict)
    sfx_enabled: bool = True
    fact_check_enabled: bool = True
    story_dna_id: uuid.UUID | None = None
    series_id: uuid.UUID | None = None


def create_project(session: Session, user_id: uuid.UUID, data: ProjectInput) -> Project:
    dna = None
    if data.story_dna_id:
        dna = session.get(StoryDnaProfile, data.story_dna_id)
        if dna is None or dna.user_id != user_id:
            raise NotFoundError("Story DNA profile not found")
    project = Project(user_id=user_id, title=(data.title or data.topic)[:120], topic=data.topic, status=ProjectStatus.DRAFT.value,
                      story_dna_id=dna.id if dna else None, series_id=data.series_id)  # fmt: skip
    project.settings = ProjectSettings(
        language=data.language, duration_seconds=data.duration_seconds, aspect_ratio=data.aspect_ratio, fps=data.fps,
        platform=data.platform,
        visual_style=data.visual_style or (dna.visual_style if dna else "cinematic_documentary"),
        story_tone=data.story_tone or (dna.tone if dna else "documentary"),
        voice_id=data.voice_id or (dna.voice_id if dna else "am_michael"),
        voice_speed=data.voice_speed or (dna.voice_speed if dna else 1.0),
        caption_style={**(dna.caption_style if dna else {}), **data.caption_style},
        music={**(dna.music_preferences if dna else {}), **data.music},
        sfx_enabled=data.sfx_enabled, fact_check_enabled=data.fact_check_enabled,
        style_prompt=dna.style_prompt if dna else "", brand=dict(dna.brand) if dna else {},
    )  # fmt: skip
    session.add(project)
    session.flush()
    return project
