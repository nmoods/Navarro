"""Local authentication: Argon2id passwords, short-lived JWT access tokens, rotating refresh-token cookie.

In ``auth_mode=supabase`` the frontend signs in with Supabase Auth and these endpoints are disabled; the
API verifies Supabase JWTs via JWKS instead (see api/deps.py).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Header, Request, Response, status
from sqlalchemy import select, update

from app.api.deps import CurrentUser, DbSession, SettingsDep, audit
from app.core.config import AppEnv, AuthMode, Settings
from app.core.errors import AuthenticationError, ConflictError, PermissionDeniedError
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    password_needs_rehash,
    verify_password,
)
from app.infrastructure.database.models import Profile, RefreshToken, User
from app.schemas.core import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "nv_refresh"
COOKIE_PATH = "/api/v1/auth"
REUSE_GRACE_SECONDS = 20
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")


def _local_only(settings: Settings) -> None:
    if settings.auth_mode is not AuthMode.LOCAL:
        raise PermissionDeniedError("Local authentication is disabled; sign in with Supabase")


def _csrf_guard(x_requested_with: str | None) -> None:
    # Cookie-authenticated endpoints require a custom header, which cross-site forms cannot send.
    if x_requested_with != "narravo":
        raise PermissionDeniedError("Missing X-Requested-With header")


def _issue(session, settings: Settings, response: Response, user: User, request: Request,  # type: ignore[no-untyped-def]
           family: uuid.UUID | None = None) -> TokenOut:  # fmt: skip
    raw, digest = new_refresh_token()
    session.add(RefreshToken(user_id=user.id, token_hash=digest, family_id=family or uuid.uuid4(),
                             expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
                             user_agent=(request.headers.get("user-agent") or "")[:255]))  # fmt: skip
    response.set_cookie(COOKIE, raw, max_age=settings.refresh_token_days * 86400, httponly=True,
                        secure=settings.app_env is AppEnv.PRODUCTION, samesite="strict", path=COOKIE_PATH)  # fmt: skip
    return TokenOut(access_token=create_access_token(settings, user.id, user.email), expires_in=settings.access_token_minutes * 60)


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, display_name=user.profile.display_name if user.profile else user.email,
                   auth_provider=user.auth_provider, created_at=user.created_at,
                   default_story_dna_id=user.profile.default_story_dna_id if user.profile else None)  # fmt: skip


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request, response: Response, session: DbSession, settings: SettingsDep) -> TokenOut:
    _local_only(settings)
    email = body.email.lower()
    if session.scalar(select(User.id).where(User.email == email)):
        raise ConflictError("An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password), auth_provider="local")
    user.profile = Profile(display_name=body.display_name)
    session.add(user)
    session.flush()
    audit(session, request, user.id, "auth.register")
    return _issue(session, settings, response, user, request)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, response: Response, session: DbSession, settings: SettingsDep) -> TokenOut:
    _local_only(settings)
    user = session.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not user.password_hash:
        verify_password(_DUMMY_HASH, body.password)  # equalise timing to avoid account enumeration
        audit(session, request, None, "auth.login_failed", email_domain=body.email.split("@")[-1])
        raise AuthenticationError("Invalid email or password")
    if not verify_password(user.password_hash, body.password) or not user.is_active:
        audit(session, request, user.id, "auth.login_failed")
        raise AuthenticationError("Invalid email or password")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    user.last_login_at = datetime.now(UTC)
    audit(session, request, user.id, "auth.login")
    return _issue(session, settings, response, user, request)


@router.post("/refresh", response_model=TokenOut)
def refresh(request: Request, response: Response, session: DbSession, settings: SettingsDep,
            x_requested_with: str | None = Header(default=None)) -> TokenOut:  # fmt: skip
    _local_only(settings)
    _csrf_guard(x_requested_with)
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise AuthenticationError("No session")
    token = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)))
    now = datetime.now(UTC)
    if token is None:
        raise AuthenticationError("Session expired")
    expires = token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=UTC)
    if token.revoked_at is not None:
        revoked = token.revoked_at if token.revoked_at.tzinfo else token.revoked_at.replace(tzinfo=UTC)
        family_alive = session.scalar(select(RefreshToken.id).where(
            RefreshToken.family_id == token.family_id, RefreshToken.revoked_at.is_(None)).limit(1))  # fmt: skip
        if family_alive and (now - revoked).total_seconds() < REUSE_GRACE_SECONDS:
            # Benign race: two tabs (or a double effect) refreshed with the same cookie within seconds.
            user = session.get(User, token.user_id)
            if user is None or not user.is_active:
                raise AuthenticationError("Account disabled")
            return _issue(session, settings, response, user, request, family=token.family_id)
        # Reuse of a rotated token outside the grace window => likely theft: revoke the whole family.
        session.execute(update(RefreshToken).where(RefreshToken.family_id == token.family_id).values(revoked_at=now))
        audit(session, request, token.user_id, "auth.refresh_reuse_detected")
        session.commit()
        raise AuthenticationError("Session revoked")
    if expires < now:
        raise AuthenticationError("Session expired")
    token.revoked_at = now
    user = session.get(User, token.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Account disabled")
    return _issue(session, settings, response, user, request, family=token.family_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, session: DbSession, x_requested_with: str | None = Header(default=None)) -> None:
    _csrf_guard(x_requested_with)
    if raw := request.cookies.get(COOKIE):
        token = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)))
        if token:
            session.execute(update(RefreshToken).where(RefreshToken.family_id == token.family_id)
                            .values(revoked_at=datetime.now(UTC)))  # fmt: skip
    response.delete_cookie(COOKIE, path=COOKIE_PATH)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return user_out(user)
