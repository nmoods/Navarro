"""Turn ORM rows into API responses, attaching short-lived signed media URLs."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import sign_media_path
from app.infrastructure.database.models import MediaAsset, Project, Scene, SceneAsset, VideoExport
from app.infrastructure.storage.base import Storage
from app.schemas.core import ExportOut, MediaOut, ProjectOut, SceneAssetOut, SceneOut


def media_url(settings: Settings, storage: Storage, asset: MediaAsset, *, download: bool = False) -> str:
    direct = None if download else storage.presigned_url(asset.storage_key, settings.media_url_ttl_seconds)
    if direct:
        return direct
    path = sign_media_path(settings, asset.id, asset.user_id)
    if download:
        path = path.replace("/content?", "/download?")
    return settings.public_api_url.rstrip("/") + path


def media_out(settings: Settings, storage: Storage, asset: MediaAsset) -> MediaOut:
    return MediaOut(
        id=asset.id, kind=asset.kind, source=asset.source, mime_type=asset.mime_type, size_bytes=asset.size_bytes,
        original_name=asset.original_name, width=asset.width, height=asset.height,
        duration_seconds=asset.duration_seconds, url=media_url(settings, storage, asset), created_at=asset.created_at,
    )  # fmt: skip


def project_out(session: Session, settings: Settings, storage: Storage, project: Project, with_settings: bool = True) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    if not with_settings:
        out.settings = None
    if project.thumbnail_asset_id and (thumb := session.get(MediaAsset, project.thumbnail_asset_id)):
        out.thumbnail_url = media_url(settings, storage, thumb)
    return out


def _asset_out(settings: Settings, storage: Storage, link: SceneAsset, asset: MediaAsset) -> SceneAssetOut:
    return SceneAssetOut(
        id=link.id, role=link.role, media_asset_id=asset.id, provider=link.provider, source=asset.source,
        url=media_url(settings, storage, asset), is_current=link.is_current, locked=bool(link.details.get("locked")),
        created_at=link.created_at, details={k: v for k, v in link.details.items() if k != "words"},
    )  # fmt: skip


def scenes_out(session: Session, settings: Settings, storage: Storage, scenes: list[Scene]) -> list[SceneOut]:
    ids = [s.id for s in scenes]
    rows = session.execute(
        select(SceneAsset, MediaAsset)
        .join(MediaAsset, MediaAsset.id == SceneAsset.media_asset_id)
        .where(SceneAsset.scene_id.in_(ids), SceneAsset.is_current.is_(True))
    ).all() if ids else []
    current: dict[tuple[uuid.UUID, str], tuple[SceneAsset, MediaAsset]] = {}
    for link, asset in rows:
        key = (link.scene_id, link.role)
        if key not in current or link.created_at > current[key][0].created_at:
            current[key] = (link, asset)
    out = []
    for scene in sorted(scenes, key=lambda s: s.position):
        item = SceneOut.model_validate(scene)
        if img := current.get((scene.id, "image")):
            item.image = _asset_out(settings, storage, *img)
        if audio := current.get((scene.id, "narration")):
            item.narration_audio = _asset_out(settings, storage, *audio)
            item.narration_seconds = audio[1].duration_seconds
        if tr := current.get((scene.id, "transcript")):
            item.caption_timing = tr[0].details.get("method")
        out.append(item)
    return out


def scene_asset_history(session: Session, settings: Settings, storage: Storage, scene: Scene, role: str) -> list[SceneAssetOut]:
    rows = session.execute(
        select(SceneAsset, MediaAsset).join(MediaAsset, MediaAsset.id == SceneAsset.media_asset_id)
        .where(SceneAsset.scene_id == scene.id, SceneAsset.role == role).order_by(SceneAsset.created_at.desc()).limit(20)
    ).all()  # fmt: skip
    return [_asset_out(settings, storage, link, asset) for link, asset in rows]


def export_out(session: Session, settings: Settings, storage: Storage, export: VideoExport, title: str | None = None) -> ExportOut:
    video = session.get(MediaAsset, export.video_asset_id)
    thumb = session.get(MediaAsset, export.thumbnail_asset_id) if export.thumbnail_asset_id else None
    assert video is not None
    return ExportOut(
        id=export.id, project_id=export.project_id, project_title=title, quality=export.quality,
        aspect_ratio=export.aspect_ratio, width=export.width, height=export.height, fps=export.fps,
        duration_seconds=export.duration_seconds, video_url=media_url(settings, storage, video),
        download_url=media_url(settings, storage, video, download=True),
        thumbnail_url=media_url(settings, storage, thumb) if thumb else None, created_at=export.created_at,
        details=export.details,
    )  # fmt: skip
