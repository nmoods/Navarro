"""Test configuration: isolated SQLite DB + storage per session, deterministic test-double providers."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="reelforge-test-"))
os.environ.update({
    "REELFORGE_APP_ENV": "test",
    "REELFORGE_DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}",
    "REELFORGE_STORAGE_ROOT": str(_TMP / "storage"),
    "REELFORGE_WORK_ROOT": str(_TMP / "work"),
    "REELFORGE_LLM_PROVIDER": "fixture",
    "REELFORGE_IMAGE_PROVIDER": "fixture",
    "REELFORGE_TTS_PROVIDER": "fixture",
    "REELFORGE_STT_PROVIDER": "fixture",
    "REELFORGE_EMBEDDED_WORKER": "false",
    "REELFORGE_JWT_SECRET": "test-secret-0123456789abcdef0123456789abcdef",
    "REELFORGE_RATE_LIMIT_PER_MINUTE": "10000",
    "REELFORGE_GENERATION_RATE_LIMIT_PER_HOUR": "1000",
    "REELFORGE_MAX_ACTIVE_JOBS_PER_USER": "50",
})  # fmt: skip

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.infrastructure.database.base import Base  # noqa: E402
from app.infrastructure.database.session import get_engine, get_session_factory  # noqa: E402
from app.infrastructure.providers import get_providers  # noqa: E402
from app.infrastructure.storage.base import get_storage  # noqa: E402
from app.workers.runner import Worker  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    import app.infrastructure.database.models  # noqa: F401

    Base.metadata.create_all(get_engine())
    yield
    get_engine().dispose()


@pytest.fixture
def db() -> Iterator[Session]:
    with get_session_factory()() as session:
        yield session


@pytest.fixture
def worker() -> Worker:
    settings = get_settings()
    return Worker(settings, get_session_factory(), get_providers(), get_storage(settings))


def drain(worker: Worker, limit: int = 20) -> int:
    count = 0
    while count < limit and worker.run_once():
        count += 1
    return count


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


def register(client: TestClient, email: str, password: str = "Sup3r-secret-pass") -> dict:
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": password, "display_name": "Tester"})
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
