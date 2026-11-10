"""Media library, secure uploads and signed media delivery (no filesystem paths ever reach clients)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, SettingsDep, StorageDep, audit, owned
from app.api.presenters import media_out
from app.application.assets import store_bytes, store_file
from app.application.uploads import read_limited, validate_audio, validate_image
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.core.security import verify_media_signature
from app.infrastructure.database.models import MediaAsset, MusicTrack, Project, SceneAsset, VideoExport
from app.schemas.core import MediaOut, Page

router = APIRouter(prefix="/media", tags=["media"])


@router.get("", response_model=Page[MediaOut])
def library(session: DbSession, settings: SettingsDep, storage: StorageDep, user: CurrentUser,
            kind: Literal["image", "audio", "video", "thumbnail"] | None = None, source: str | None = None,
            limit: Annotated[int, Query(ge=1, le=100)] = 40, offset: Annotated[int, Query(ge=0)] = 0) -> Page[MediaOut]:  # fmt: skip
    stmt = select(MediaAsset).where(MediaAsset.user_id == user.id, MediaAsset.kind != "transcript")
    if kind:
        stmt = stmt.where(MediaAsset.kind == kind)
    if source:
        stmt = stmt.where(MediaAsset.source == source)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.scalars(stmt.order_by(MediaAsset.created_at.desc()).limit(limit).offset(offset))
    return Page(items=[media_out(settings, storage, a) for a in rows], total=total, limit=limit, offset=offset)


@router.post("/upload", response_model=MediaOut, status_code=status.HTTP_201_CREATED)
async def upload(request: Request, session: DbSession, settings: SettingsDep, storage: StorageDep, user: CurrentUser,
                 file: UploadFile = File(...), purpose: Literal["image", "music"] = Form("image"),
                 name: Annotated[str, Form(max_length=80)] = "") -> MediaOut:  # fmt: skip
    data = await read_limited(file, settings.max_upload_bytes)
    if purpose == "image":
        clean = validate_image(data, file.filename)
        asset = store_bytes(session, storage, user_id=user.id, kind="image", source="uploaded", data=clean.data, mime=clean.mime,
                            width=clean.width, height=clean.height)  # fmt: skip
        asset.original_name = (file.filename or "")[:255]
    else:
        path, duration, mime = validate_audio(data, file.filename, settings.work_root / "uploads")
        try:
            asset = store_file(session, storage, user_id=user.id, kind="audio", source="uploaded", path=path, mime=mime,
                               duration=duration, original_name=(file.filename or "")[:255])  # fmt: skip
        finally:
            path.unlink(missing_ok=True)
        session.add(MusicTrack(user_id=user.id, name=(name or file.filename or "Uploaded track")[:80], mood="custom",
                               source="upload", media_asset_id=asset.id,
                               license_note="Uploaded by the user, who confirmed they hold the rights"))  # fmt: skip
    audit(session, request, user.id, "media.upload", "media", asset.id, purpose=purpose, size=asset.size_bytes)
    session.flush()
    return media_out(settings, storage, asset)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(asset_id: uuid.UUID, session: DbSession, storage: StorageDep, user: CurrentUser) -> None:
    asset = owned(session, MediaAsset, asset_id, user)
    in_use = (
        session.scalar(select(SceneAsset.id).where(SceneAsset.media_asset_id == asset.id, SceneAsset.is_current.is_(True)).limit(1))
        or session.scalar(select(VideoExport.id).where(VideoExport.video_asset_id == asset.id).limit(1))
        or session.scalar(select(Project.id).where(Project.thumbnail_asset_id == asset.id).limit(1))
    )
    if in_use:
        raise ConflictError("This file is used by a project; remove it there first")
    storage.delete(asset.storage_key)
    session.delete(asset)


def _signed_asset(session, settings, asset_id: uuid.UUID, u: str, exp: int, sig: str) -> MediaAsset:  # type: ignore[no-untyped-def]
    if not verify_media_signature(settings, asset_id, u, exp, sig):
        raise PermissionDeniedError("Link expired or invalid")
    asset = session.get(MediaAsset, asset_id)
    if asset is None or str(asset.user_id) != u:
        raise NotFoundError("Media not found")
    return asset


@router.get("/{asset_id}/content")
def content(asset_id: uuid.UUID, session: DbSession, settings: SettingsDep, storage: StorageDep, u: str, exp: int, sig: str):  # type: ignore[no-untyped-def]
    """Capability URL (HMAC, expiring) so <img>/<video> tags work without exposing bearer tokens."""
    asset = _signed_asset(session, settings, asset_id, u, exp, sig)
    if direct := storage.presigned_url(asset.storage_key, 300):
        return RedirectResponse(direct)
    return FileResponse(storage.local_path(asset.storage_key), media_type=asset.mime_type,
                        headers={"Cache-Control": "private, max-age=3600", "Content-Security-Policy": "default-src 'none'; sandbox"})  # fmt: skip


@router.get("/{asset_id}/download")
def download(asset_id: uuid.UUID, session: DbSession, settings: SettingsDep, storage: StorageDep, u: str, exp: int, sig: str):  # type: ignore[no-untyped-def]
    asset = _signed_asset(session, settings, asset_id, u, exp, sig)
    name = asset.original_name or f"narravo-{asset.id.hex[:8]}.{asset.mime_type.split('/')[-1]}"
    safe = "".join(c for c in name if c.isalnum() or c in "-_.")[:100] or "download.mp4"
    return FileResponse(storage.local_path(asset.storage_key), media_type=asset.mime_type, filename=safe)
