"""Scene editor: edit, add, delete, reorder, regenerate one scene, replace/restore images."""

from __future__ import annotations

import random
import uuid
from typing import Literal

from fastapi import APIRouter, File, Request, UploadFile, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, SettingsDep, StorageDep, audit, owned
from app.api.presenters import scene_asset_history, scenes_out
from app.application.assets import hash_inputs, store_bytes
from app.application.production import attach
from app.application.story_service import current_storyboard
from app.application.uploads import read_limited, validate_image
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.domain.enums import ACTIVE_JOB_STATUSES, JobType
from app.infrastructure.database.models import GenerationJob, MediaAsset, Project, Scene, SceneAsset
from app.schemas.core import (
    JobOut,
    RegenerateSceneIn,
    ReorderIn,
    SceneAssetOut,
    SceneCreate,
    SceneOut,
    SceneUpdate,
)
from app.workers import queue

router = APIRouter(tags=["scenes"])


def _scene(session, scene_id: uuid.UUID, user) -> tuple[Scene, Project]:  # type: ignore[no-untyped-def]
    scene = session.get(Scene, scene_id)
    project = session.get(Project, scene.project_id) if scene else None
    if scene is None or project is None or project.user_id != user.id:
        raise NotFoundError("Scene not found")
    return scene, project


def _apply(scene: Scene, body: SceneUpdate) -> None:
    data = body.model_dump(exclude_unset=True, mode="json")
    if "caption_override" in data:
        scene.caption_override = body.caption_override.clean() if body.caption_override else {}  # type: ignore[union-attr]
        data.pop("caption_override")
    if "visual_data" in data and len(str(data["visual_data"])) > 4000:
        raise ValidationFailedError("visual_data too large")
    for key, value in data.items():
        setattr(scene, key, value)
    if scene.position == 0:
        scene.transition = "cut"


@router.patch("/scenes/{scene_id}", response_model=SceneOut)
def update_scene(scene_id: uuid.UUID, body: SceneUpdate, session: DbSession, settings: SettingsDep, storage: StorageDep,
                 user: CurrentUser) -> SceneOut:  # fmt: skip
    scene, _ = _scene(session, scene_id, user)
    _apply(scene, body)
    session.flush()
    return scenes_out(session, settings, storage, [scene])[0]


@router.post("/projects/{project_id}/scenes", response_model=SceneOut, status_code=status.HTTP_201_CREATED)
def add_scene(project_id: uuid.UUID, body: SceneCreate, session: DbSession, settings: SettingsDep, storage: StorageDep,
              user: CurrentUser) -> SceneOut:  # fmt: skip
    project = owned(session, Project, project_id, user)
    board = current_storyboard(session, project.id)
    if board is None:
        raise ConflictError("Generate or create a storyboard first")
    scenes = sorted(board.scenes, key=lambda s: s.position)
    if len(scenes) >= 30:
        raise ValidationFailedError("A video can have at most 30 scenes")
    position = min(body.position if body.position is not None else len(scenes), len(scenes))
    for s in scenes[position:]:
        s.position += 1
    scene = Scene(storyboard_id=board.id, project_id=project.id, position=position, title=body.title or f"Scene {position + 1}",
                  narration=body.narration, visual_type="cinematic_image", camera_movement="ken_burns", transition="crossfade",
                  image_seed=random.randint(1, 2**31 - 1))  # noqa: S311  # fmt: skip
    session.add(scene)
    _apply(scene, body)
    session.flush()
    return scenes_out(session, settings, storage, [scene])[0]


@router.delete("/scenes/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scene(scene_id: uuid.UUID, session: DbSession, user: CurrentUser) -> None:
    scene, _ = _scene(session, scene_id, user)
    siblings = sorted(scene.storyboard.scenes, key=lambda s: s.position)
    if len(siblings) <= 1:
        raise ValidationFailedError("A video needs at least one scene")
    session.delete(scene)
    session.flush()
    for i, s in enumerate(x for x in siblings if x.id != scene.id):
        s.position = i
        if i == 0:
            s.transition = "cut"


@router.post("/projects/{project_id}/scenes/reorder", response_model=list[SceneOut])
def reorder(project_id: uuid.UUID, body: ReorderIn, session: DbSession, settings: SettingsDep, storage: StorageDep,
            user: CurrentUser) -> list[SceneOut]:  # fmt: skip
    project = owned(session, Project, project_id, user)
    board = current_storyboard(session, project.id)
    if board is None:
        raise NotFoundError("No storyboard")
    by_id = {s.id: s for s in board.scenes}
    if set(body.scene_ids) != set(by_id) or len(body.scene_ids) != len(by_id):
        raise ValidationFailedError("scene_ids must list every scene exactly once")
    for i, sid in enumerate(body.scene_ids):
        by_id[sid].position = i
    by_id[body.scene_ids[0]].transition = "cut"
    session.flush()
    return scenes_out(session, settings, storage, list(by_id.values()))


@router.post("/scenes/{scene_id}/regenerate", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def regenerate(scene_id: uuid.UUID, body: RegenerateSceneIn, session: DbSession, settings: SettingsDep, user: CurrentUser) -> JobOut:
    scene, project = _scene(session, scene_id, user)
    busy = session.scalar(select(GenerationJob.id).where(
        GenerationJob.project_id == project.id, GenerationJob.status.in_([s.value for s in ACTIVE_JOB_STATUSES])))  # fmt: skip
    if busy:
        raise ConflictError("This project already has a job running")
    if "image" in body.parts:
        link = session.scalar(select(SceneAsset).where(SceneAsset.scene_id == scene.id, SceneAsset.role == "image",
                                                       SceneAsset.is_current.is_(True)))  # fmt: skip
        if link and link.details.get("locked"):
            link.details = {**link.details, "locked": False}  # explicit regenerate unlocks an uploaded image
    job = queue.enqueue(session, settings, user_id=user.id, job_type=JobType.SCENE_REGENERATION, project_id=project.id,
                        scene_id=scene.id, payload=body.model_dump())  # fmt: skip
    session.flush()
    return JobOut.model_validate(job)


@router.post("/scenes/{scene_id}/image", response_model=SceneOut)
async def upload_scene_image(scene_id: uuid.UUID, request: Request, session: DbSession, settings: SettingsDep,
                             storage: StorageDep, user: CurrentUser, file: UploadFile = File(...)) -> SceneOut:  # fmt: skip
    scene, project = _scene(session, scene_id, user)
    clean = validate_image(await read_limited(file, settings.max_upload_bytes), file.filename)
    asset = store_bytes(session, storage, user_id=user.id, kind="image", source="uploaded", data=clean.data, mime=clean.mime,
                        width=clean.width, height=clean.height, details={"original_name": (file.filename or "")[:120]})  # fmt: skip
    attach(session, scene, "image", asset, hash_inputs("upload", asset.sha256), "upload", {"locked": True})
    if scene.visual_type not in ("cinematic_image", "parallax", "character_portrait", "newspaper", "comparison"):
        scene.visual_type = "cinematic_image"
    audit(session, request, user.id, "scene.image_upload", "scene", scene.id)
    session.flush()
    return scenes_out(session, settings, storage, [scene])[0]


@router.get("/scenes/{scene_id}/assets", response_model=list[SceneAssetOut])
def asset_history(scene_id: uuid.UUID, session: DbSession, settings: SettingsDep, storage: StorageDep, user: CurrentUser,
                  role: Literal["image", "narration"] = "image") -> list[SceneAssetOut]:  # fmt: skip
    scene, _ = _scene(session, scene_id, user)
    return scene_asset_history(session, settings, storage, scene, role)


@router.post("/scenes/{scene_id}/assets/{link_id}/restore", response_model=SceneOut)
def restore_asset(scene_id: uuid.UUID, link_id: uuid.UUID, session: DbSession, settings: SettingsDep, storage: StorageDep,
                  user: CurrentUser) -> SceneOut:  # fmt: skip
    """Make a previous image variant current again and pin it so production will not replace it."""
    scene, _ = _scene(session, scene_id, user)
    link = session.get(SceneAsset, link_id)
    if link is None or link.scene_id != scene.id or link.role != "image":
        raise NotFoundError("Asset not found")
    asset = session.get(MediaAsset, link.media_asset_id)
    assert asset is not None
    attach(session, scene, "image", asset, link.input_hash, link.provider, {**link.details, "locked": True})
    session.flush()
    return scenes_out(session, settings, storage, [scene])[0]
