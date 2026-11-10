"""Media storage abstraction. Keys are always generated server-side (never from user input)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Protocol

from app.core.config import Settings, StorageBackendKind

_SAFE_KEY = re.compile(r"^[a-z0-9][a-z0-9/_\-.]{0,200}$")


class StorageError(RuntimeError):
    pass


def validate_key(key: str) -> str:
    if not _SAFE_KEY.match(key) or ".." in key or key.startswith("/") or "//" in key:
        raise StorageError(f"Unsafe storage key: {key!r}")
    return key


class Storage(Protocol):
    def put_file(self, key: str, source: Path, content_type: str) -> None: ...

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None: ...

    def local_path(self, key: str) -> Path:
        """A readable local path for the object (downloads to the cache for remote backends)."""
        ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...

    def presigned_url(self, key: str, ttl: int) -> str | None:
        """Direct URL for remote backends; None means 'stream through the API'."""
        ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / validate_key(key)).resolve()
        if not path.is_relative_to(self.root):
            raise StorageError("Path traversal blocked")
        return path

    def put_file(self, key: str, source: Path, content_type: str) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    def local_path(self, key: str) -> Path:
        path = self._path(key)
        if not path.exists():
            raise StorageError(f"Missing object {key}")
        return path

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def presigned_url(self, key: str, ttl: int) -> str | None:
        return None


class R2Storage:
    """Cloudflare R2 via its S3-compatible API (boto3 is imported lazily; optional dependency)."""

    def __init__(self, settings: Settings) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - optional
            raise StorageError("Install boto3 to use the R2 storage backend") from exc
        if not (settings.r2_account_id and settings.r2_bucket and settings.r2_access_key_id and settings.r2_secret_access_key):
            raise StorageError("R2 storage requires NARRAVO_R2_ACCOUNT_ID, _BUCKET, _ACCESS_KEY_ID, _SECRET_ACCESS_KEY")
        self.bucket = settings.r2_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
            aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
            region_name="auto",
        )
        self.cache = LocalStorage(settings.work_root / "r2-cache")

    def put_file(self, key: str, source: Path, content_type: str) -> None:
        self.client.upload_file(str(source), self.bucket, validate_key(key), ExtraArgs={"ContentType": content_type})

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=validate_key(key), Body=data, ContentType=content_type)

    def local_path(self, key: str) -> Path:
        if self.cache.exists(key):
            return self.cache.local_path(key)
        dest = self.cache._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, validate_key(key), str(dest))
        return dest

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=validate_key(key))
        self.cache.delete(key)

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=validate_key(key))
            return True
        except Exception:  # noqa: BLE001 - botocore ClientError
            return False

    def presigned_url(self, key: str, ttl: int) -> str | None:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": validate_key(key)}, ExpiresIn=ttl
        )


_storage: Storage | None = None


def get_storage(settings: Settings) -> Storage:
    global _storage
    if _storage is None:
        _storage = R2Storage(settings) if settings.storage_backend is StorageBackendKind.R2 else LocalStorage(settings.storage_root)
    return _storage


def reset_storage() -> None:
    global _storage
    _storage = None
