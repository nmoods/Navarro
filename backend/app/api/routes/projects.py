"""Projects: CRUD, story generation, Hook Lab selection, production/preview, exports."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession, SettingsDep, StorageDep, audit, owned
from app.api.presenters import export_out, project_out, scenes_out
from app.application.projects import ProjectInput, create_project
from app.application.story_service import current_storyboard, latest_script
from app.application.subtitles import build_cues, to_srt, to_vtt
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.domain.enums import ACTIVE_JOB_STATUSES, JobType
from app.infrastructure.database.models import GenerationJob, Project, StoryDnaProfile, VideoExport
from app.schemas.core import (
    ExportOut,
    JobOut,
    Page,
    ProduceIn,
    ProjectCreate,
    ProjectOut,
    ProjectSettingsUpdate,
    ScriptOut,
    SelectHookIn,
    StoryboardOut,
)
from app.workers import queue

router = APIRouter(prefix="/projects", tags=["projects"])


def _active_job(session, project_id: uuid.UUID) -> GenerationJob | None:  # type: ignore[no-untyped-def]
    return session.scalar(select(GenerationJob).where(
        GenerationJob.project_id == project_id, GenerationJob.status.in_([s.value for s in ACTIVE_JOB_STATUSES])
    ).limit(1))  # fmt: skip


@router.get("", response_model=Page[ProjectOut])
def list_projects(session: DbSession, settings: SettingsDep, storage: StorageDep, user: CurrentUser,
                  q: Annotated[str | None, Query(max_length=100)] = None, status_: Annotated[str | None, Query(alias="status")] = None,
                  limit: Annotated[int, Query(ge=1, le=100)] = 24, offset: Annotated[int, Query(ge=0)] = 0) -> Page[ProjectOut]:  # fmt: skip
    stmt = select(Project).where(Project.user_id == user.id)
    if q:
        like = f"%{q.replace('%', '').replace('_', '')}%"
        stmt = stmt.where(or_(Project.title.ilike(like), Project.topic.ilike(like)))
    if status_:
        stmt = stmt.where(Project.status == status_)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.scalars(stmt.order_by(Project.updated_at.desc()).limit(limit).offset(offset)).unique().all()
    return Page(items=[project_out(session, settings, storage, p, with_settings=False) for p in rows], total=total, limit=limit, offset=offset)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create(body: ProjectCreate, request: Request, session: DbSession, settings: SettingsDep, storage: StorageDep,
           user: CurrentUser) -> ProjectOut:  # fmt: skip
    data = body.model_dump(exclude={"auto_produce", "hook_style", "caption_style", "music"})
    project = create_project(session, user.id, ProjectInput(**data, caption_style=body.caption_style.clean(),
                                                            music=body.music.model_dump(mode="json", exclude_none=True)))  # fmt: skip
    job_type = JobType.PRODUCTION if body.auto_produce else JobType.STORY
    queue.enqueue(session, settings, user_id=user.id, job_type=job_type, project_id=project.id,
                  payload={"hook_style": body.hook_style} if body.hook_style else {})  # fmt: skip
    audit(session, request, user.id, "project.create", "project", project.id)
    session.flush()
    return project_out(session, settings, storage, project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: uuid.UUID, session: DbSession, settings: SettingsDep, storage: StorageDep, user: CurrentUser) -> ProjectOut:
    return project_out(session, settings, storage, owned(session, Project, project_id, user))


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: uuid.UUID, body: ProjectSettingsUpdate, session: DbSession, settings: SettingsDep,
                   storage: StorageDep, user: CurrentUser) -> ProjectOut:  # fmt: skip
    project = owned(session, Project, project_id, user)
    data = body.model_dump(exclude_unset=True, mode="json")
    if "title" in data:
        project.title = data.pop("title")
    if "story_dna_id" in data:
        dna_id = data.pop("story_dna_id")
        if dna_id:
            owned(session, StoryDnaProfile, uuid.UUID(dna_id), user)
        project.story_dna_id = uuid.UUID(dna_id) if dna_id else None
    if "caption_style" in data:
        project.settings.caption_style = {**project.settings.caption_style, **body.caption_style.clean()}  # type: ignore[union-attr]
        data.pop("caption_style")
    if "music" in data:
        project.settings.music = {**project.settings.music, **data.pop("music")}
    if "brand_handle" in data:
        handle = (data.pop("brand_handle") or "").strip()
        project.settings.brand = {**project.settings.brand, "handle": handle}
    for key, value in data.items():
        setattr(project.settings, key, value)
    session.flush()
    return project_out(session, settings, storage, project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: uuid.UUID, request: Request, session: DbSession, user: CurrentUser) -> None:
    project = owned(session, Project, project_id, user)
    for job in session.scalars(select(GenerationJob).where(GenerationJob.project_id == project.id)):
        queue.request_cancel(session, job)
    session.delete(project)
    audit(session, request, user.id, "project.delete", "project", project_id)


@router.get("/{project_id}/script", response_model=ScriptOut)
def get_script(project_id: uuid.UUID, session: DbSession, user: CurrentUser) -> ScriptOut:
    owned(session, Project, project_id, user)
    script = latest_script(session, project_id)
    if script is None:
        raise NotFoundError("No script generated yet")
    return ScriptOut.model_validate(script)


@router.get("/{project_id}/storyboard", response_model=StoryboardOut)
def get_storyboard(project_id: uuid.UUID, session: DbSession, settings: SettingsDep, storage: StorageDep, user: CurrentUser) -> StoryboardOut:
    owned(session, Project, project_id, user)
    board = current_storyboard(session, project_id)
    if board is None:
        raise NotFoundError("No storyboard yet")
    return StoryboardOut(id=board.id, version=board.version, analysis=board.analysis,
                         scenes=scenes_out(session, settings, storage, list(board.scenes)))  # fmt: skip


def _enqueue(session, settings, user, project: Project, job_type: JobType, payload: dict | None = None) -> JobOut:  # type: ignore[no-untyped-def]
    if _active_job(session, project.id):
        raise ConflictError("This project already has a job running. Cancel it or wait for it to finish.")
    job = queue.enqueue(session, settings, user_id=user.id, job_type=job_type, project_id=project.id, payload=payload or {})
    session.flush()
    return JobOut.model_validate(job)


@router.post("/{project_id}/generate-story", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def generate_story(project_id: uuid.UUID, session: DbSession, settings: SettingsDep, user: CurrentUser) -> JobOut:
    return _enqueue(session, settings, user, owned(session, Project, project_id, user), JobType.STORY)


@router.post("/{project_id}/hooks/select", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def select_hook(project_id: uuid.UUID, body: SelectHookIn, session: DbSession, settings: SettingsDep, user: CurrentUser) -> JobOut:
    """Hook Lab: rebuild script + storyboard around the chosen hook."""
    project = owned(session, Project, project_id, user)
    script = latest_script(session, project_id)
    if script is None or body.hook_index >= len(script.hooks):
        raise ValidationFailedError("Unknown hook")
    style = script.hooks[body.hook_index].get("style")
    return _enqueue(session, settings, user, project, JobType.STORY, {"hook_style": style})


@router.post("/{project_id}/produce", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def produce(project_id: uuid.UUID, body: ProduceIn, session: DbSession, settings: SettingsDep, user: CurrentUser) -> JobOut:
    project = owned(session, Project, project_id, user)
    job_type = JobType.PREVIEW if body.quality == "draft" else JobType.PRODUCTION
    return _enqueue(session, settings, user, project, job_type, {"quality": body.quality})


@router.get("/{project_id}/exports", response_model=list[ExportOut])
def project_exports(project_id: uuid.UUID, session: DbSession, settings: SettingsDep, storage: StorageDep, user: CurrentUser) -> list[ExportOut]:
    project = owned(session, Project, project_id, user)
    rows = session.scalars(select(VideoExport).where(VideoExport.project_id == project.id).order_by(VideoExport.created_at.desc()).limit(20))
    return [export_out(session, settings, storage, e, project.title) for e in rows]


@router.get("/{project_id}/jobs", response_model=list[JobOut])
def project_jobs(project_id: uuid.UUID, session: DbSession, user: CurrentUser) -> list[JobOut]:
    owned(session, Project, project_id, user)
    rows = session.scalars(select(GenerationJob).where(GenerationJob.project_id == project_id).order_by(GenerationJob.created_at.desc()).limit(20))
    return [JobOut.model_validate(j) for j in rows]


@router.get("/{project_id}/subtitles.{fmt}")
def subtitles(project_id: uuid.UUID, fmt: str, session: DbSession, user: CurrentUser) -> Response:
    """Subtitle file (SRT or WebVTT) for uploading to platforms that support separate captions."""
    if fmt not in ("srt", "vtt"):
        raise NotFoundError("Use .srt or .vtt")
    project = owned(session, Project, project_id, user)
    cues = build_cues(session, project)
    body = to_srt(cues) if fmt == "srt" else to_vtt(cues)
    name = "".join(c if c.isalnum() else "-" for c in project.title.lower()).strip("-")[:60] or "subtitles"
    return Response(body, media_type="application/x-subrip" if fmt == "srt" else "text/vtt",
                    headers={"Content-Disposition": f'attachment; filename="{name}.{fmt}"'})
