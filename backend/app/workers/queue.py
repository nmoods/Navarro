"""Database-backed job queue.

PostgreSQL uses ``FOR UPDATE SKIP LOCKED`` so many workers can claim safely; SQLite serialises writers and
uses a guarded UPDATE. The interface is small enough to swap for Redis/Arq later without touching handlers.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.errors import RateLimitedError
from app.domain.enums import ACTIVE_JOB_STATUSES, JobStatus, JobType
from app.infrastructure.database.models import GenerationJob, GenerationJobLog

logger = logging.getLogger("reelforge.queue")

FIRST_STAGE = {
    JobType.STORY: JobStatus.SCRIPT_GENERATION,
    JobType.PRODUCTION: JobStatus.IMAGE_GENERATION,
    JobType.PREVIEW: JobStatus.IMAGE_GENERATION,
    JobType.SCENE_REGENERATION: JobStatus.STORYBOARD_GENERATION,
    JobType.SERIES_PLAN: JobStatus.SCRIPT_GENERATION,
    JobType.SERIES_PRODUCTION: JobStatus.FINALIZING,
}


def now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)  # SQLite returns naive datetimes
    return value


def enqueue(
    session: Session,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    job_type: JobType,
    payload: dict | None = None,
    project_id: uuid.UUID | None = None,
    series_id: uuid.UUID | None = None,
    scene_id: uuid.UUID | None = None,
    parent_job_id: uuid.UUID | None = None,
    priority: int = 100,
    enforce_limits: bool = True,
) -> GenerationJob:
    if enforce_limits:
        active = session.scalar(
            select(func.count()).select_from(GenerationJob).where(
                GenerationJob.user_id == user_id,
                GenerationJob.status.in_([s.value for s in ACTIVE_JOB_STATUSES]),
                GenerationJob.parent_job_id.is_(None),
            )
        )
        if (active or 0) >= settings.max_active_jobs_per_user:
            raise RateLimitedError(f"You already have {active} generation jobs running. Wait for one to finish.")
        recent = session.scalar(
            select(func.count()).select_from(GenerationJob).where(
                GenerationJob.user_id == user_id, GenerationJob.created_at >= now() - timedelta(hours=1)
            )
        )
        if (recent or 0) >= settings.generation_rate_limit_per_hour:
            raise RateLimitedError("Hourly generation limit reached. Please try again later.")
    job = GenerationJob(
        user_id=user_id, job_type=job_type.value, payload=payload or {}, project_id=project_id, series_id=series_id,
        scene_id=scene_id, parent_job_id=parent_job_id, priority=priority, max_attempts=settings.job_max_attempts,
        timeout_seconds=settings.job_timeout_seconds, run_after=now(),
    )  # fmt: skip
    session.add(job)
    session.flush()
    return job


def claim_next(factory: sessionmaker[Session], worker_id: str) -> uuid.UUID | None:
    with factory() as session:
        dialect = session.bind.dialect.name if session.bind else "sqlite"
        candidates = (
            select(GenerationJob.id, GenerationJob.job_type)
            .where(GenerationJob.status == JobStatus.PENDING.value, GenerationJob.run_after <= now())
            .order_by(GenerationJob.priority, GenerationJob.created_at)
            .limit(1)
        )
        if dialect == "postgresql":
            candidates = candidates.with_for_update(skip_locked=True)
        row = session.execute(candidates).first()
        if row is None:
            return None
        job_id, job_type = row
        stage = FIRST_STAGE.get(JobType(job_type), JobStatus.FINALIZING)
        result = session.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.status == JobStatus.PENDING.value)
            .values(status=stage.value, locked_by=worker_id, locked_at=now(), heartbeat_at=now(),
                    started_at=now(), attempts=GenerationJob.attempts + 1, stage_message="Starting")  # fmt: skip
        )
        session.commit()
        return job_id if result.rowcount == 1 else None


def set_stage(factory: sessionmaker[Session], job_id: uuid.UUID, status: JobStatus | None, progress: float, message: str) -> bool:
    """Persist progress + heartbeat. Returns True if cancellation was requested."""
    with factory() as session:
        values: dict = {"progress": max(0.0, min(100.0, progress)), "stage_message": message[:250], "heartbeat_at": now()}
        if status is not None:
            values["status"] = status.value
        session.execute(update(GenerationJob).where(GenerationJob.id == job_id).values(**values))
        cancelled = session.scalar(select(GenerationJob.cancel_requested).where(GenerationJob.id == job_id))
        session.commit()
        return bool(cancelled)


def is_cancel_requested(factory: sessionmaker[Session], job_id: uuid.UUID) -> bool:
    with factory() as session:
        return bool(session.scalar(select(GenerationJob.cancel_requested).where(GenerationJob.id == job_id)))


def add_log(factory: sessionmaker[Session], job_id: uuid.UUID, level: str, stage: str, message: str, data: dict | None = None) -> None:
    with factory() as session:
        session.add(GenerationJobLog(job_id=job_id, level=level, stage=stage, message=message[:2000], data=data or {}))
        session.commit()


def finish(factory: sessionmaker[Session], job_id: uuid.UUID, status: JobStatus, *, result: dict | None = None,
           error: str | None = None, retry: bool = False) -> JobStatus:  # fmt: skip
    with factory() as session:
        job = session.get(GenerationJob, job_id)
        if job is None:
            return status
        if retry and job.attempts < job.max_attempts and not job.cancel_requested:
            job.status = JobStatus.PENDING.value
            job.run_after = now() + timedelta(seconds=15 * 2 ** (job.attempts - 1))
            job.stage_message = f"Retrying after error: {(error or '')[:150]}"
            job.locked_by = None
            final = JobStatus.PENDING
        else:
            job.status = status.value
            job.finished_at = now()
            job.progress = 100.0 if status is JobStatus.COMPLETED else job.progress
            job.stage_message = {"completed": "Done", "cancelled": "Cancelled"}.get(status.value, (error or "Failed")[:250])
            job.error = error
            job.locked_by = None
            final = status
        if result:
            job.result = {**(job.result or {}), **result}
        session.commit()
        return final


def request_cancel(session: Session, job: GenerationJob) -> None:
    job.cancel_requested = True
    if job.status == JobStatus.PENDING.value:
        job.status = JobStatus.CANCELLED.value
        job.finished_at = now()
        job.stage_message = "Cancelled"
    for child in session.scalars(select(GenerationJob).where(GenerationJob.parent_job_id == job.id)):
        request_cancel(session, child)


def recover_stale(factory: sessionmaker[Session], stale_after: int) -> int:
    """Requeue jobs whose worker died (no heartbeat), or fail them when attempts are exhausted."""
    cutoff = now() - timedelta(seconds=stale_after)
    recovered = 0
    with factory() as session:
        running = [s.value for s in ACTIVE_JOB_STATUSES if s is not JobStatus.PENDING]
        for job in session.scalars(select(GenerationJob).where(GenerationJob.status.in_(running))):
            beat = _aware(job.heartbeat_at) or _aware(job.locked_at)
            if beat and beat < cutoff:
                if job.attempts < job.max_attempts:
                    job.status, job.locked_by, job.run_after = JobStatus.PENDING.value, None, now()
                    job.stage_message = "Recovered after worker interruption"
                else:
                    job.status, job.finished_at = JobStatus.FAILED.value, now()
                    job.error = job.stage_message = "Worker stopped responding"
                recovered += 1
        session.commit()
    if recovered:
        logger.warning("recovered %d stale jobs", recovered)
    return recovered


def vacuum_sqlite(factory: sessionmaker[Session]) -> None:  # pragma: no cover - maintenance helper
    with factory() as session:
        if session.bind and session.bind.dialect.name == "sqlite":
            session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
