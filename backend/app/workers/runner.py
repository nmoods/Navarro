"""Worker loop: claims jobs, runs handlers with bounded concurrency, applies retry/cancel/timeout policy.

Run standalone with ``python -m app.workers.runner`` or embedded in the API process (dev default).
"""

from __future__ import annotations

import logging
import os
import socket
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.errors import AppError, JobCancelledError, ProviderError, ProviderUnavailableError
from app.core.logging import configure_logging
from app.domain.enums import JobStatus
from app.infrastructure.database.models import GenerationJob
from app.infrastructure.database.session import get_session_factory
from app.infrastructure.providers import Providers, get_providers
from app.infrastructure.storage.base import Storage, get_storage
from app.workers import queue
from app.workers.context import JobContext, JobTimeoutError
from app.workers.handlers import HANDLERS, on_job_finished

logger = logging.getLogger("narravo.worker")


class Worker:
    def __init__(self, settings: Settings, factory: sessionmaker[Session], providers: Providers, storage: Storage) -> None:
        self.settings, self.factory, self.providers, self.storage = settings, factory, providers, storage
        self.worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self._stop = threading.Event()
        self._slots = threading.Semaphore(max(1, settings.worker_concurrency))
        self._pool = ThreadPoolExecutor(max_workers=max(1, settings.worker_concurrency), thread_name_prefix="job")
        self._thread: threading.Thread | None = None

    def start_background(self) -> None:
        self._thread = threading.Thread(target=self.run_forever, name="narravo-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._pool.shutdown(wait=False, cancel_futures=True)

    def run_forever(self, poll_seconds: float = 1.0) -> None:
        logger.info("worker %s started (concurrency=%d)", self.worker_id, self.settings.worker_concurrency)
        last_maintenance = 0.0
        while not self._stop.is_set():
            if time.monotonic() - last_maintenance > 60:
                self.maintenance()
                last_maintenance = time.monotonic()
            if not self._slots.acquire(timeout=poll_seconds):
                continue
            try:
                job_id = queue.claim_next(self.factory, self.worker_id)
            except Exception:
                logger.exception("claim failed")
                job_id = None
            if job_id is None:
                self._slots.release()
                self._stop.wait(poll_seconds)
                continue
            self._pool.submit(self._run_and_release, job_id)

    def run_once(self) -> bool:
        """Process at most one job synchronously (used by tests and CLI)."""
        job_id = queue.claim_next(self.factory, self.worker_id)
        if job_id is None:
            return False
        self.execute(job_id)
        return True

    def _run_and_release(self, job_id: uuid.UUID) -> None:
        try:
            self.execute(job_id)
        finally:
            self._slots.release()

    def execute(self, job_id: uuid.UUID) -> JobStatus:
        with self.factory() as session:
            job = session.get(GenerationJob, job_id)
            assert job is not None
            ctx = JobContext(job_id, self.factory, job.timeout_seconds, status=JobStatus(job.status))
            handler = HANDLERS.get(job.job_type)
            status, error, retry, result = JobStatus.FAILED, None, False, {}
            try:
                if handler is None:
                    raise AppError(f"No handler for job type {job.job_type}")
                result = handler(session, job, ctx, self.settings, self.providers, self.storage)
                status = JobStatus.COMPLETED
            except JobCancelledError:
                session.rollback()
                status = JobStatus.CANCELLED
            except ProviderUnavailableError as exc:
                session.rollback()
                error = f"{exc.provider} unavailable: {exc.message}"
            except ProviderError as exc:
                session.rollback()
                error, retry = f"{exc.provider}: {exc.message}", exc.retryable
            except JobTimeoutError as exc:
                session.rollback()
                error = str(exc)
            except AppError as exc:
                session.rollback()
                error = exc.message
            except Exception as exc:
                session.rollback()
                logger.exception("job %s crashed", job_id)
                error, retry = f"Unexpected error: {type(exc).__name__}: {str(exc)[:300]}", True
            if error:
                ctx.log("error", error)
            final = queue.finish(self.factory, job_id, status, result=result, error=error, retry=retry)
            if final is not JobStatus.PENDING:
                session.expire_all()
                job = session.get(GenerationJob, job_id)
                if job is not None:
                    on_job_finished(session, job, final, error)
            logger.info("job %s -> %s", job_id, final.value)
            return final

    def maintenance(self) -> None:
        try:
            queue.recover_stale(self.factory, self.settings.job_stale_after_seconds)
            cleanup_work_dir(self.settings.work_root)
        except Exception:
            logger.exception("maintenance failed")


def cleanup_work_dir(root: Path, max_age_hours: float = 24, clip_cache_max_gb: float = 5.0) -> None:
    """Delete stale temp job folders and trim the clip cache (oldest first)."""
    import shutil

    cutoff = time.time() - max_age_hours * 3600
    jobs = root / "jobs"
    if jobs.exists():
        for d in jobs.iterdir():
            if d.is_dir() and d.stat().st_mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)
    clips = root / "clips"
    if clips.exists():
        files = sorted(clips.glob("*.mp4"), key=lambda p: p.stat().st_atime)
        total = sum(f.stat().st_size for f in files)
        for f in files:
            if total <= clip_cache_max_gb * 1e9:
                break
            total -= f.stat().st_size
            f.unlink(missing_ok=True)


def main() -> None:  # pragma: no cover - process entrypoint
    settings = get_settings()
    configure_logging(settings.log_level)
    worker = Worker(settings, get_session_factory(), get_providers(), get_storage(settings))
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":  # pragma: no cover
    main()
