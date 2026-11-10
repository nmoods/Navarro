"""Password hashing, access tokens and signed media URLs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings
from app.core.errors import AuthenticationError

_hasher = PasswordHasher()
ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - token type label, not a secret
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "narravo"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    email: str | None


def create_access_token(settings: Settings, user_id: uuid.UUID, email: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "email": email,
        "typ": ACCESS_TOKEN_TYPE,
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM)


def decode_access_token(settings: Settings, token: str) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "sub", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Access token expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid access token") from exc
    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        raise AuthenticationError("Invalid token type")
    try:
        return TokenClaims(user_id=uuid.UUID(payload["sub"]), email=payload.get("email"))
    except ValueError as exc:
        raise AuthenticationError("Invalid token subject") from exc


def new_refresh_token() -> tuple[str, str]:
    """Return (raw token for the client cookie, sha256 hash stored in the database)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _media_key(settings: Settings) -> bytes:
    return hashlib.sha256(b"media-url:" + settings.jwt_secret.get_secret_value().encode()).digest()


def sign_media_path(settings: Settings, asset_id: uuid.UUID, user_id: uuid.UUID, ttl: int | None = None) -> str:
    """Create a short-lived capability URL for <video>/<img> tags, which cannot send bearer headers."""
    expires = int(time.time()) + (ttl or settings.media_url_ttl_seconds)
    message = f"{asset_id}:{user_id}:{expires}".encode()
    sig = base64.urlsafe_b64encode(hmac.new(_media_key(settings), message, hashlib.sha256).digest()).decode()
    return f"/api/v1/media/{asset_id}/content?u={user_id}&exp={expires}&sig={sig.rstrip('=')}"


def verify_media_signature(settings: Settings, asset_id: uuid.UUID, user_id: str, exp: int, sig: str) -> bool:
    if exp < int(time.time()):
        return False
    message = f"{asset_id}:{user_id}:{exp}".encode()
    expected = base64.urlsafe_b64encode(hmac.new(_media_key(settings), message, hashlib.sha256).digest())
    return hmac.compare_digest(expected.decode().rstrip("="), sig)
