"""Series Factory and Content Planner (ideas, calendar, AI topic discovery)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, ProvidersDep, SettingsDep, owned
from app.application.projects import ProjectInput, create_project
from app.application.story_director import StoryDirector
from app.core.errors import ConflictError, ValidationFailedError
from app.domain.enums import ACTIVE_JOB_STATUSES, JobType, SeriesStatus
from app.infrastructure.database.models import (
    ContentIdea,
    ContentSeries,
    GenerationJob,
    SeriesEpisode,
    StoryDnaProfile,
)
from app.schemas.core import (
    EpisodeOut,
    EpisodeUpdate,
    IdeaIn,
    IdeaOut,
    IdeaUpdate,
    JobOut,
    ProjectOut,
    SeriesCreate,
    SeriesOut,
    SeriesProduceIn,
    SuggestIn,
)
from app.workers import queue

router = APIRouter(tags=["planning"])


def _busy(session, series_id: uuid.UUID) -> bool:  # type: ignore[no-untyped-def]
    return bool(session.scalar(select(GenerationJob.id).where(
        GenerationJob.series_id == series_id, GenerationJob.parent_job_id.is_(None),
        GenerationJob.status.in_([s.value for s in ACTIVE_JOB_STATUSES])).limit(1)))  # fmt: skip


@router.get("/series", response_model=list[SeriesOut])
def list_series(session: DbSession, user: CurrentUser) -> list[SeriesOut]:
    rows = session.scalars(select(ContentSeries).where(ContentSeries.user_id == user.id).order_by(ContentSeries.created_at.desc()))
    return [SeriesOut.model_validate(s) for s in rows]


@router.post("/series", response_model=SeriesOut, status_code=status.HTTP_201_CREATED)
def create_series(body: SeriesCreate, session: DbSession, settings: SettingsDep, user: CurrentUser) -> SeriesOut:
    if body.story_dna_id:
        owned(session, StoryDnaProfile, body.story_dna_id, user)
    series = ContentSeries(user_id=user.id, title=body.theme[:120], theme=body.theme, episode_count=body.episode_count,
                           story_dna_id=body.story_dna_id, status=SeriesStatus.PLANNING.value,
                           settings=body.model_dump(mode="json", exclude={"theme", "episode_count", "story_dna_id"}))  # fmt: skip
    session.add(series)
    session.flush()
    queue.enqueue(session, settings, user_id=user.id, job_type=JobType.SERIES_PLAN, series_id=series.id)
    session.flush()
    return SeriesOut.model_validate(series)


@router.get("/series/{series_id}", response_model=SeriesOut)
def get_series(series_id: uuid.UUID, session: DbSession, user: CurrentUser) -> SeriesOut:
    return SeriesOut.model_validate(owned(session, ContentSeries, series_id, user))


@router.delete("/series/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_series(series_id: uuid.UUID, session: DbSession, user: CurrentUser) -> None:
    series = owned(session, ContentSeries, series_id, user)
    for job in session.scalars(select(GenerationJob).where(GenerationJob.series_id == series.id)):
        queue.request_cancel(session, job)
    session.delete(series)


@router.post("/series/{series_id}/replan", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def replan(series_id: uuid.UUID, session: DbSession, settings: SettingsDep, user: CurrentUser) -> JobOut:
    series = owned(session, ContentSeries, series_id, user)
    if _busy(session, series.id):
        raise ConflictError("This series already has a job running")
    for ep in list(series.episodes):
        if ep.project_id is None and ep.status == "planned":
            session.delete(ep)
    session.flush()
    series.status = SeriesStatus.PLANNING.value
    job = queue.enqueue(session, settings, user_id=user.id, job_type=JobType.SERIES_PLAN, series_id=series.id)
    session.flush()
    return JobOut.model_validate(job)


@router.post("/series/{series_id}/produce", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def produce_series(series_id: uuid.UUID, body: SeriesProduceIn, session: DbSession, settings: SettingsDep, user: CurrentUser) -> JobOut:
    series = owned(session, ContentSeries, series_id, user)
    if not series.episodes:
        raise ValidationFailedError("Plan episodes first")
    if _busy(session, series.id):
        raise ConflictError("This series already has a job running")
    job = queue.enqueue(session, settings, user_id=user.id, job_type=JobType.SERIES_PRODUCTION, series_id=series.id,
                        payload={"episode_ids": [str(i) for i in body.episode_ids] if body.episode_ids else None,
                                 "quality": body.quality})  # fmt: skip
    session.flush()
    return JobOut.model_validate(job)


@router.patch("/series/{series_id}/episodes/{episode_id}", response_model=EpisodeOut)
def update_episode(series_id: uuid.UUID, episode_id: uuid.UUID, body: EpisodeUpdate, session: DbSession, user: CurrentUser) -> EpisodeOut:
    series = owned(session, ContentSeries, series_id, user)
    ep = session.get(SeriesEpisode, episode_id)
    if ep is None or ep.series_id != series.id:
        raise ValidationFailedError("Episode not in series")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(ep, key, value)
    session.flush()
    return EpisodeOut.model_validate(ep)


# ---- Content planner ----------------------------------------------------------------------------------------
@router.get("/ideas", response_model=list[IdeaOut])
def list_ideas(session: DbSession, user: CurrentUser, start: date | None = None, end: date | None = None,
               status_: Annotated[str | None, Query(alias="status")] = None) -> list[IdeaOut]:  # fmt: skip
    stmt = select(ContentIdea).where(ContentIdea.user_id == user.id)
    if start:
        stmt = stmt.where(ContentIdea.scheduled_for >= start)
    if end:
        stmt = stmt.where(ContentIdea.scheduled_for <= end)
    if status_:
        stmt = stmt.where(ContentIdea.status == status_)
    return [IdeaOut.model_validate(i) for i in session.scalars(stmt.order_by(ContentIdea.created_at.desc()).limit(500))]


@router.post("/ideas", response_model=IdeaOut, status_code=status.HTTP_201_CREATED)
def create_idea(body: IdeaIn, session: DbSession, user: CurrentUser) -> IdeaOut:
    idea = ContentIdea(user_id=user.id, **body.model_dump(mode="python"))
    session.add(idea)
    session.flush()
    return IdeaOut.model_validate(idea)


@router.patch("/ideas/{idea_id}", response_model=IdeaOut)
def update_idea(idea_id: uuid.UUID, body: IdeaUpdate, session: DbSession, user: CurrentUser) -> IdeaOut:
    idea = owned(session, ContentIdea, idea_id, user)
    data = body.model_dump(exclude_unset=True, exclude={"clear_schedule"})
    for key, value in data.items():
        setattr(idea, key, value)
    if body.clear_schedule:
        idea.scheduled_for = None
    session.flush()
    return IdeaOut.model_validate(idea)


@router.delete("/ideas/{idea_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_idea(idea_id: uuid.UUID, session: DbSession, user: CurrentUser) -> None:
    session.delete(owned(session, ContentIdea, idea_id, user))


@router.post("/ideas/{idea_id}/create-project", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def idea_to_project(idea_id: uuid.UUID, session: DbSession, settings: SettingsDep, user: CurrentUser) -> ProjectOut:
    idea = owned(session, ContentIdea, idea_id, user)
    dna_id = user.profile.default_story_dna_id if user.profile else None
    project = create_project(session, user.id, ProjectInput(topic=f"{idea.title}. {idea.notes}".strip(". "), title=idea.title,
                                                            story_dna_id=dna_id))  # fmt: skip
    idea.project_id, idea.status = project.id, "in_production"
    queue.enqueue(session, settings, user_id=user.id, job_type=JobType.STORY, project_id=project.id)
    session.flush()
    return ProjectOut.model_validate(project)


@router.post("/ideas/suggest", response_model=list[IdeaIn])
def suggest(body: SuggestIn, providers: ProvidersDep, user: CurrentUser) -> list[IdeaIn]:
    """Topic discovery with the local LLM (synchronous; typically 20-60 s on CPU)."""
    ideas = StoryDirector(providers.llm).suggest_topics(body.theme, body.count)
    return [IdeaIn(title=i.title[:160], notes=f"{i.premise}\nHook: {i.hook}"[:2000], tags=[]) for i in ideas.ideas]
