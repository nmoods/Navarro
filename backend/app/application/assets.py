"""Persist files as user-owned ``MediaAsset`` rows (server-generated storage keys only)."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.infrastructure.database.models import MediaAsset
from app.infrastructure.storage.base import Storage

EXTENSIONS = {
    "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "audio/wav": "wav", "audio/mpeg": "mp3",
    "audio/ogg": "ogg", "audio/flac": "flac", "video/mp4": "mp4", "application/json": "json",
}  # fmt: skip


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_inputs(*parts: object) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def _key(user_id: uuid.UUID, kind: str, mime: str) -> tuple[uuid.UUID, str]:
    asset_id = uuid.uuid4()
    return asset_id, f"u/{user_id.hex}/{kind}/{asset_id.hex}.{EXTENSIONS.get(mime, 'bin')}"


def store_file(
    session: Session,
    storage: Storage,
    *,
    user_id: uuid.UUID,
    kind: str,
    source: str,
    path: Path,
    mime: str,
    original_name: str | None = None,
    width: int | None = None,
    height: int | None = None,
    duration: float | None = None,
    details: dict | None = None,
) -> MediaAsset:
    asset_id, key = _key(user_id, kind, mime)
    storage.put_file(key, path, mime)
    asset = MediaAsset(
        id=asset_id, user_id=user_id, kind=kind, source=source, storage_key=key, mime_type=mime,
        size_bytes=path.stat().st_size, sha256=sha256_file(path), original_name=original_name, width=width,
        height=height, duration_seconds=duration, details=details or {},
    )  # fmt: skip
    session.add(asset)
    session.flush()
    return asset


def store_bytes(session: Session, storage: Storage, *, user_id: uuid.UUID, kind: str, source: str, data: bytes, mime: str,
                width: int | None = None, height: int | None = None, details: dict | None = None) -> MediaAsset:  # fmt: skip
    asset_id, key = _key(user_id, kind, mime)
    storage.put_bytes(key, data, mime)
    asset = MediaAsset(
        id=asset_id, user_id=user_id, kind=kind, source=source, storage_key=key, mime_type=mime, size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(), width=width, height=height, details=details or {},
    )  # fmt: skip
    session.add(asset)
    session.flush()
    return asset
