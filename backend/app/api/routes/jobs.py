"""Generation jobs (progress, logs, cancellation) and the cross-project export history."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, SettingsDep, StorageDep, audit, owned
from app.api.presenters import export_out
from app.domain.enums import ACTIVE_JOB_STATUSES
from app.infrastructure.database.models import GenerationJob, GenerationJobLog, Project, VideoExport
from app.schemas.core import ExportOut, JobLogOut, JobOut
from app.workers import queue

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(session: DbSession, user: CurrentUser, active: bool = False,
              limit: Annotated[int, Query(ge=1, le=100)] = 30) -> list[JobOut]:  # fmt: skip
    stmt = select(GenerationJob).where(GenerationJob.user_id == user.id)
    if active:
        stmt = stmt.where(GenerationJob.status.in_([s.value for s in ACTIVE_JOB_STATUSES]))
    return [JobOut.model_validate(j) for j in session.scalars(stmt.order_by(GenerationJob.created_at.desc()).limit(limit))]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, session: DbSession, user: CurrentUser) -> JobOut:
    return JobOut.model_validate(owned(session, GenerationJob, job_id, user))


@router.get("/jobs/{job_id}/logs", response_model=list[JobLogOut])
def job_logs(job_id: uuid.UUID, session: DbSession, user: CurrentUser) -> list[JobLogOut]:
    owned(session, GenerationJob, job_id, user)
    rows = session.scalars(select(GenerationJobLog).where(GenerationJobLog.job_id == job_id).order_by(GenerationJobLog.created_at).limit(500))
    return [JobLogOut.model_validate(r) for r in rows]


@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: uuid.UUID, request: Request, session: DbSession, user: CurrentUser) -> JobOut:
    job = owned(session, GenerationJob, job_id, user)
    if job.status not in [s.value for s in ACTIVE_JOB_STATUSES]:
        return JobOut.model_validate(job)
    queue.request_cancel(session, job)
    audit(session, request, user.id, "job.cancel", "job", job.id)
    session.flush()
    return JobOut.model_validate(job)


@router.get("/exports", response_model=list[ExportOut])
def recent_exports(session: DbSession, settings: SettingsDep, storage: StorageDep, user: CurrentUser,
                   limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[ExportOut]:  # fmt: skip
    rows = session.execute(
        select(VideoExport, Project.title).join(Project, Project.id == VideoExport.project_id)
        .where(VideoExport.user_id == user.id).order_by(VideoExport.created_at.desc()).limit(limit)
    ).all()  # fmt: skip
    return [export_out(session, settings, storage, e, title) for e, title in rows]


@router.delete("/exports/{export_id}", status_code=204)
def delete_export(export_id: uuid.UUID, session: DbSession, user: CurrentUser) -> None:
    session.delete(owned(session, VideoExport, export_id, user))
