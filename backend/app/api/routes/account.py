"""Account settings, dashboard summary, system health and option catalogues."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, ProvidersDep, SettingsDep, StorageDep, audit, owned
from app.api.presenters import export_out, project_out
from app.api.routes.auth import COOKIE, COOKIE_PATH, user_out
from app.core.errors import AuthenticationError, ValidationFailedError
from app.core.security import hash_password, verify_password
from app.domain import enums
from app.infrastructure.database.models import (
    ContentSeries,
    GenerationJob,
    MediaAsset,
    Project,
    StoryDnaProfile,
    Template,
    VideoExport,
)
from app.media.fonts import AVAILABLE_FONTS
from app.schemas.core import JobOut, PasswordChange, ProfileUpdate, RegisterIn, UserOut

router = APIRouter(tags=["account"])


@router.patch("/account/profile", response_model=UserOut)
def update_profile(body: ProfileUpdate, session: DbSession, user: CurrentUser) -> UserOut:
    data = body.model_dump(exclude_unset=True)
    if "default_story_dna_id" in data and data["default_story_dna_id"]:
        owned(session, StoryDnaProfile, data["default_story_dna_id"], user)
    for key, value in data.items():
        setattr(user.profile, key, value)
    session.flush()
    return user_out(user)


@router.post("/account/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: PasswordChange, request: Request, session: DbSession, user: CurrentUser) -> None:
    if not user.password_hash or not verify_password(user.password_hash, body.current_password):
        raise AuthenticationError("Current password is incorrect")
    RegisterIn.model_validate({"email": "x@example.com", "password": body.new_password, "display_name": "x"})
    user.password_hash = hash_password(body.new_password)
    audit(session, request, user.id, "account.password_changed")


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(request: Request, response: Response, session: DbSession, storage: StorageDep, user: CurrentUser,
                   confirm: str = "") -> None:  # fmt: skip
    """Permanently delete the account, all projects and every stored media file."""
    if confirm != user.email:
        raise ValidationFailedError("Pass ?confirm=<your email> to delete your account")
    for asset in session.scalars(select(MediaAsset).where(MediaAsset.user_id == user.id)):
        storage.delete(asset.storage_key)
    audit(session, request, None, "account.deleted", "user", user.id)
    session.delete(user)
    response.delete_cookie(COOKIE, path=COOKIE_PATH)


@router.get("/dashboard")
def dashboard(session: DbSession, settings: SettingsDep, storage: StorageDep, user: CurrentUser) -> dict:
    projects = session.scalars(select(Project).where(Project.user_id == user.id).order_by(Project.updated_at.desc()).limit(6)).unique()
    exports = session.execute(
        select(VideoExport, Project.title).join(Project, Project.id == VideoExport.project_id)
        .where(VideoExport.user_id == user.id).order_by(VideoExport.created_at.desc()).limit(6)
    ).all()  # fmt: skip
    jobs = session.scalars(select(GenerationJob).where(GenerationJob.user_id == user.id).order_by(GenerationJob.created_at.desc()).limit(8))
    count = lambda model: session.scalar(select(func.count()).select_from(model).where(model.user_id == user.id)) or 0  # noqa: E731
    seconds = session.scalar(select(func.coalesce(func.sum(VideoExport.duration_seconds), 0)).where(
        VideoExport.user_id == user.id, VideoExport.quality == "final")) or 0  # fmt: skip
    return {
        "recent_projects": [project_out(session, settings, storage, p, with_settings=False).model_dump(mode="json") for p in projects],
        "recent_exports": [export_out(session, settings, storage, e, t).model_dump(mode="json") for e, t in exports],
        "activity": [JobOut.model_validate(j).model_dump(mode="json") for j in jobs],
        "stats": {"projects": count(Project), "exports": count(VideoExport), "series": count(ContentSeries),
                  "story_dna": count(StoryDnaProfile), "minutes_rendered": round(float(seconds) / 60, 1)},
        "templates": [{"id": str(t.id), "name": t.name, "category": t.category} for t in session.scalars(
            select(Template).where((Template.user_id == user.id) | Template.is_builtin.is_(True)).limit(6))],
    }  # fmt: skip


@router.get("/system/providers")
def provider_status(providers: ProvidersDep, user: CurrentUser) -> list[dict]:
    return [h.__dict__ for h in providers.health()]


@router.get("/system/options")
def options() -> dict:
    """Closed vocabularies for UI pickers, generated from the same enums the backend validates against."""
    def values(e):  # type: ignore[no-untyped-def]
        return [m.value for m in e]

    return {
        "visual_styles": values(enums.VisualStyle), "visual_types": values(enums.VisualType),
        "camera_moves": values(enums.CameraMove), "effects": values(enums.Effect), "transitions": values(enums.Transition),
        "caption_animations": values(enums.CaptionAnimation), "caption_positions": values(enums.CaptionPosition),
        "sound_effects": values(enums.SoundEffect), "music_moods": values(enums.MusicMood),
        "story_tones": values(enums.StoryTone), "platforms": values(enums.Platform), "aspect_ratios": values(enums.AspectRatio),
        "hook_styles": values(enums.HookStyle), "fonts": list(AVAILABLE_FONTS), "durations": [30, 45, 60, 90],
        "languages": [{"code": c, "name": n} for c, n in (("en", "English"), ("es", "Spanish"), ("fr", "French"),
                      ("it", "Italian"), ("pt", "Portuguese"), ("hi", "Hindi"), ("ja", "Japanese"), ("zh", "Mandarin"))],
    }  # fmt: skip
