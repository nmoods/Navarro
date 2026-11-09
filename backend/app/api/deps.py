"""FastAPI dependencies: DB session, settings, providers, storage, authenticated user, ownership checks."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated, TypeVar

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import AuthMode, Settings, get_settings
from app.core.errors import AuthenticationError, NotFoundError
from app.core.security import decode_access_token
from app.infrastructure.database.models import AuditLog, Profile, User
from app.infrastructure.database.session import get_session_factory
from app.infrastructure.providers import Providers, get_providers
from app.infrastructure.storage.base import Storage, get_storage

logger = logging.getLogger("reelforge.auth")
_bearer = HTTPBearer(auto_error=False)
M = TypeVar("M")


def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def providers_dep() -> Providers:
    return get_providers()


def storage_dep(settings: SettingsDep) -> Storage:
    return get_storage(settings)


ProvidersDep = Annotated[Providers, Depends(providers_dep)]
StorageDep = Annotated[Storage, Depends(storage_dep)]


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{url.rstrip('/')}/auth/v1/.well-known/jwks.json", cache_keys=True, lifespan=3600)


def _supabase_user(session: Session, settings: Settings, token: str) -> User:
    assert settings.supabase_url
    try:
        key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=["RS256", "ES256"], audience=settings.supabase_jwt_audience,
                            issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1")  # fmt: skip
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid Supabase session") from exc
    sub, email = claims.get("sub"), (claims.get("email") or "").lower()
    user = session.scalar(select(User).where(User.external_id == sub))
    if user is None:
        user = User(email=email or f"{sub}@supabase.local", auth_provider="supabase", external_id=sub)
        user.profile = Profile(display_name=(email.split("@")[0] if email else "Creator")[:80])
        session.add(user)
        session.flush()
    return user


def get_current_user(
    session: DbSession,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authentication required")
    if settings.auth_mode is AuthMode.SUPABASE:
        user = _supabase_user(session, settings, credentials.credentials)
    else:
        claims = decode_access_token(settings, credentials.credentials)
        user = session.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Account not found or disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def owned(session: Session, model: type[M], obj_id: uuid.UUID, user: User) -> M:
    """Fetch a row the user owns. Returns 404 (not 403) for other users' rows to avoid id enumeration."""
    obj = session.get(model, obj_id)
    if obj is None or getattr(obj, "user_id", None) != user.id:
        raise NotFoundError(f"{model.__name__} not found")
    return obj


def audit(session: Session, request: Request | None, user_id: uuid.UUID | None, action: str,
          resource_type: str | None = None, resource_id: object = None, **details: object) -> None:  # fmt: skip
    ip = request.client.host if request and request.client else None
    session.add(AuditLog(user_id=user_id, action=action, resource_type=resource_type,
                         resource_id=str(resource_id) if resource_id else None, ip_address=ip, details=details))  # fmt: skip
