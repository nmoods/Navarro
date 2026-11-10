"""Job handlers: one function per JobType. Each receives a fresh DB session and a JobContext."""

from __future__ import annotations

import logging
import random
import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.production import ProductionService
from app.application.projects import ProjectInput, create_project
from app.application.story_director import StoryDirector
from app.application.story_service import creative_context, current_storyboard, generate_story
from app.core.config import Settings
from app.core.errors import NotFoundError
from app.domain.enums import JobStatus, JobType, ProjectStatus, SeriesStatus
from app.infrastructure.database.models import ContentSeries, GenerationJob, Project, Scene, SeriesEpisode
from app.infrastructure.providers import Providers
from app.infrastructure.storage.base import Storage
from app.workers import queue
from app.workers.context import JobContext

logger = logging.getLogger("narravo.handlers")

Handler = Callable[[Session, GenerationJob, JobContext, Settings, Providers, Storage], dict]


def _project(session: Session, job: GenerationJob) -> Project:
    project = session.get(Project, job.project_id) if job.project_id else None
    if project is None or project.user_id != job.user_id:
        raise NotFoundError("Project not found for job")
    return project


def handle_story(session, job, ctx, settings, providers, storage) -> dict:  # type: ignore[no-untyped-def]
    project = _project(session, job)
    director = StoryDirector(providers.llm, providers.research)
    board = generate_story(session, director, project, ctx, hook_style=job.payload.get("hook_style"),
                           hook_text=job.payload.get("hook_text"))  # fmt: skip
    return {"storyboard_id": str(board.id), "scenes": len(board.scenes)}


def handle_production(session, job, ctx, settings, providers, storage) -> dict:  # type: ignore[no-untyped-def]
    project = _project(session, job)
    if current_storyboard(session, project.id) is None:
        generate_story(session, StoryDirector(providers.llm, providers.research), project, ctx)
    quality = "draft" if job.job_type == JobType.PREVIEW.value else job.payload.get("quality", "final")
    service = ProductionService(session, settings, providers, storage, ctx)
    try:
        export = service.produce(project, quality=quality, job_id=job.id)
    finally:
        service.cleanup()
    return {"export_id": str(export.id), "duration": export.duration_seconds, "quality": quality}


def handle_scene_regeneration(session, job, ctx, settings, providers, storage) -> dict:  # type: ignore[no-untyped-def]
    project = _project(session, job)
    scene = session.get(Scene, job.scene_id) if job.scene_id else None
    if scene is None or scene.project_id != project.id:
        raise NotFoundError("Scene not found")
    parts = set(job.payload.get("parts", ["visual_plan", "image"]))
    if "visual_plan" in parts or "narration" in parts:
        ctx.stage(JobStatus.STORYBOARD_GENERATION, 10, "Re-directing this scene")
        siblings = sorted(scene.storyboard.scenes, key=lambda s: s.position)
        idx = next(i for i, s in enumerate(siblings) if s.id == scene.id)
        prev = siblings[idx - 1].narration if idx > 0 else ""
        nxt = siblings[idx + 1].narration if idx + 1 < len(siblings) else ""
        draft = StoryDirector(providers.llm).regenerate_scene(
            creative_context(session, project), scene.narration, prev, nxt, job.payload.get("instruction", ""),
            "narration" in parts,
        )
        scene.title, scene.narration = draft.title, draft.narration
        scene.visual_type, scene.visual_description, scene.image_prompt = draft.visual_type.value, draft.visual_description, draft.image_prompt
        scene.camera_movement, scene.effects = draft.camera_movement.value, [e.value for e in draft.effects]
        if scene.position > 0:
            scene.transition = draft.transition.value
        scene.emphasis_words, scene.sound_effects = draft.emphasis_words, [s.value for s in draft.sound_effects]
        scene.mood, scene.visual_data = draft.mood, draft.visual_data.model_dump(exclude_none=True)
        scene.color_palette = draft.color_palette or scene.color_palette
        session.commit()
    if "image" in parts:
        scene.image_seed = random.randint(1, 2**31 - 1)  # noqa: S311 - new variation, not security
        session.commit()
    service = ProductionService(session, settings, providers, storage, ctx)
    try:
        ctx.stage(JobStatus.IMAGE_GENERATION, 40, "Generating visuals for this scene")
        service.ensure_image(project, scene)
        session.commit()
        ctx.stage(JobStatus.VOICE_GENERATION, 70, "Updating voiceover and caption timing")
        narration = service.ensure_narration(project, scene)
        service.ensure_transcript(project, scene, narration)
        session.commit()
    finally:
        service.cleanup()
    return {"scene_id": str(scene.id)}


def handle_series_plan(session, job, ctx, settings, providers, storage) -> dict:  # type: ignore[no-untyped-def]
    series = session.get(ContentSeries, job.series_id)
    if series is None or series.user_id != job.user_id:
        raise NotFoundError("Series not found")
    ctx.stage(JobStatus.SCRIPT_GENERATION, 10, f"Planning {series.episode_count} episodes")
    existing = [e.title for e in series.episodes]
    plan = StoryDirector(providers.llm).plan_series(series.theme, series.episode_count, series.settings.get("story_tone", "documentary"), existing)
    series.title = plan.series_title[:120]
    series.bible = plan.model_dump(mode="json", exclude={"episodes"})
    start = len(series.episodes)
    for i, ep in enumerate(plan.episodes[: series.episode_count - start]):
        session.add(SeriesEpisode(series_id=series.id, position=start + i, title=ep.title[:120], premise=ep.premise,
                                  hook=ep.hook, continuity_note=ep.continuity_note))  # fmt: skip
    series.status = SeriesStatus.PLANNED.value
    session.commit()
    return {"episodes": len(plan.episodes)}


def handle_series_production(session, job, ctx, settings, providers, storage) -> dict:  # type: ignore[no-untyped-def]
    series = session.get(ContentSeries, job.series_id)
    if series is None or series.user_id != job.user_id:
        raise NotFoundError("Series not found")
    wanted = set(job.payload.get("episode_ids") or [str(e.id) for e in series.episodes])
    children = []
    for ep in series.episodes:
        if str(ep.id) not in wanted or ep.status in ("producing", "completed"):
            continue
        if ep.project_id is None:
            opts = series.settings or {}
            project = create_project(session, series.user_id, ProjectInput(
                topic=f"{ep.title}. {ep.premise}", title=ep.title, duration_seconds=opts.get("duration_seconds", 60),
                aspect_ratio=opts.get("aspect_ratio", "9:16"), platform=opts.get("platform", "tiktok"),
                visual_style=opts.get("visual_style"), story_tone=opts.get("story_tone"), voice_id=opts.get("voice_id"),
                language=opts.get("language", "en"), story_dna_id=series.story_dna_id, series_id=series.id,
            ))  # fmt: skip
            ep.project_id = project.id
        ep.status, ep.error = "producing", None
        child = queue.enqueue(session, settings, user_id=series.user_id, job_type=JobType.PRODUCTION, project_id=ep.project_id,
                              series_id=series.id, parent_job_id=job.id, priority=200, enforce_limits=False,
                              payload={"quality": job.payload.get("quality", "final")})  # fmt: skip
        children.append(str(child.id))
    series.status = SeriesStatus.PRODUCING.value
    session.commit()
    return {"queued_episodes": len(children), "child_jobs": children}


def on_job_finished(session: Session, job: GenerationJob, status: JobStatus, error: str | None) -> None:
    """Bookkeeping after any job ends: project status, and series episode/series status roll-up."""
    if job.project_id and (project := session.get(Project, job.project_id)) and status is not JobStatus.COMPLETED:
        if job.job_type in (JobType.STORY.value, JobType.PRODUCTION.value, JobType.PREVIEW.value):
            project.status = ProjectStatus.FAILED.value if status is JobStatus.FAILED else (
                ProjectStatus.STORYBOARD_READY.value if current_storyboard(session, project.id) else ProjectStatus.DRAFT.value)
            project.last_error = error
    if job.series_id and job.job_type == JobType.PRODUCTION.value:
        ep = session.scalar(select(SeriesEpisode).where(SeriesEpisode.project_id == job.project_id))
        if ep:
            ep.status = {"completed": "completed", "cancelled": "planned"}.get(status.value, "failed")
            ep.error = error
        series = session.get(ContentSeries, job.series_id)
        if series:
            states = [e.status for e in series.episodes]
            if all(s == "completed" for s in states):
                series.status = SeriesStatus.COMPLETED.value
            elif "producing" not in states:
                series.status = SeriesStatus.PARTIAL.value if "completed" in states else SeriesStatus.FAILED.value
    if job.job_type == JobType.SERIES_PLAN.value and status is JobStatus.FAILED and job.series_id:
        series = session.get(ContentSeries, job.series_id)
        if series:
            series.status = SeriesStatus.FAILED.value
    session.commit()


HANDLERS: dict[str, Handler] = {
    JobType.STORY.value: handle_story,
    JobType.PRODUCTION.value: handle_production,
    JobType.PREVIEW.value: handle_production,
    JobType.SCENE_REGENERATION.value: handle_scene_regeneration,
    JobType.SERIES_PLAN.value: handle_series_plan,
    JobType.SERIES_PRODUCTION.value: handle_series_production,
}


def job_id_str(job_id: uuid.UUID) -> str:
    return str(job_id)
