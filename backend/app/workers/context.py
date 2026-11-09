"""Per-job context handed to pipeline code: progress reporting, logging, cancellation and timeouts."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import JobCancelledError
from app.domain.enums import JobStatus
from app.workers import queue


class JobTimeoutError(RuntimeError):
    pass


@dataclass
class JobContext:
    job_id: uuid.UUID
    factory: sessionmaker[Session]
    timeout_seconds: int
    started: float = field(default_factory=time.monotonic)
    status: JobStatus = JobStatus.PENDING
    _last_beat: float = 0.0
    _cancelled: bool = False

    def stage(self, status: JobStatus, progress: float, message: str) -> None:
        self.status = status
        self._cancelled = queue.set_stage(self.factory, self.job_id, status, progress, message) or self._cancelled
        self._last_beat = time.monotonic()
        self.log("info", message)
        self.check()

    def progress(self, progress: float, message: str) -> None:
        if time.monotonic() - self._last_beat < 1.5:
            return
        self._cancelled = queue.set_stage(self.factory, self.job_id, None, progress, message) or self._cancelled
        self._last_beat = time.monotonic()
        self.check()

    def log(self, level: str, message: str, data: dict | None = None) -> None:
        queue.add_log(self.factory, self.job_id, level, self.status.value, message, data)

    def cancelled(self) -> bool:
        if not self._cancelled and time.monotonic() - self._last_beat > 2.0:
            self._cancelled = queue.is_cancel_requested(self.factory, self.job_id)
            self._last_beat = time.monotonic()
        return self._cancelled

    def check(self) -> None:
        if self.cancelled():
            raise JobCancelledError()
        if time.monotonic() - self.started > self.timeout_seconds:
            raise JobTimeoutError(f"Job exceeded its {self.timeout_seconds}s time limit")
