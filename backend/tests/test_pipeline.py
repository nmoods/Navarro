"""End-to-end pipeline through the real queue, handlers, render engine and FFmpeg (test-double AI)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.application.projects import ProjectInput, create_project
from app.core.config import get_settings
from app.domain.enums import JobStatus, JobType
from app.infrastructure.database.models import GenerationJob, MediaAsset, Scene, SceneAsset, User, VideoExport
from app.infrastructure.storage.base import get_storage
from app.media.ffmpeg import media_duration
from app.workers import queue
from tests.conftest import drain

pytestmark = pytest.mark.slow


def _user(db) -> User:  # type: ignore[no-untyped-def]
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com", password_hash="x")
    db.add(user)
    db.flush()
    return user


def test_story_then_production_then_scene_edit_reuses_assets(db, worker) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings()
    user = _user(db)
    project = create_project(db, user.id, ProjectInput(topic="The Roanoke colony", duration_seconds=30))
    job = queue.enqueue(db, settings, user_id=user.id, job_type=JobType.STORY, project_id=project.id)
    db.commit()
    drain(worker)
    db.refresh(job)
    assert job.status == JobStatus.COMPLETED.value, job.error
    scenes = db.scalars(select(Scene).where(Scene.project_id == project.id).order_by(Scene.position)).all()
    assert 3 <= len(scenes) <= 12
    assert " ".join(s.narration for s in scenes).split()[:3]  # narration persisted

    prod = queue.enqueue(db, settings, user_id=user.id, job_type=JobType.PREVIEW, project_id=project.id)
    db.commit()
    drain(worker)
    db.refresh(prod)
    assert prod.status == JobStatus.COMPLETED.value, prod.error
    export = db.scalar(select(VideoExport).where(VideoExport.project_id == project.id))
    assert export is not None
    video = get_storage(settings).local_path(db.get(MediaAsset, export.video_asset_id).storage_key)
    assert abs(media_duration(video) - export.duration_seconds) < 0.5

    assets_before = db.scalars(select(SceneAsset).where(SceneAsset.scene_id.in_([s.id for s in scenes]))).all()
    # Edit only the captions of one scene: no new narration/image assets should be generated
    scenes[1].caption_override = {"offset_ms": 120}
    db.commit()
    again = queue.enqueue(db, settings, user_id=user.id, job_type=JobType.PREVIEW, project_id=project.id)
    db.commit()
    drain(worker)
    db.refresh(again)
    assert again.status == JobStatus.COMPLETED.value, again.error
    assets_after = db.scalars(select(SceneAsset).where(SceneAsset.scene_id.in_([s.id for s in scenes]))).all()
    assert len(assets_after) == len(assets_before)

    # Edit narration of one scene: exactly that scene gets new narration + transcript assets
    scenes[0].narration = scenes[0].narration + " Nobody knows why."
    db.commit()
    queue.enqueue(db, settings, user_id=user.id, job_type=JobType.PREVIEW, project_id=project.id)
    db.commit()
    drain(worker)
    new_assets = db.scalars(select(SceneAsset).where(SceneAsset.scene_id.in_([s.id for s in scenes]))).all()
    added = [a for a in new_assets if a.id not in {b.id for b in assets_after}]
    assert {a.scene_id for a in added} == {scenes[0].id}
    assert {a.role for a in added} == {"narration", "transcript"}


def test_cancel_pending_job(db) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings()
    user = _user(db)
    project = create_project(db, user.id, ProjectInput(topic="Atlantis"))
    job = queue.enqueue(db, settings, user_id=user.id, job_type=JobType.STORY, project_id=project.id)
    queue.request_cancel(db, job)
    db.commit()
    assert db.get(GenerationJob, job.id).status == JobStatus.CANCELLED.value
