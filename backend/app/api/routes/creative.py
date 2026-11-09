"""Story DNA, Voice Studio, voice profiles, templates, music and sound effects."""

from __future__ import annotations

import uuid
from pathlib import Path

import soundfile as sf
from fastapi import APIRouter, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession, ProvidersDep, SettingsDep, StorageDep, audit, owned
from app.api.presenters import media_url
from app.application.assets import hash_inputs
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.domain.enums import MusicMood, SoundEffect
from app.infrastructure.database.models import MediaAsset, MusicTrack, Project, StoryDnaProfile, Template, VoiceProfile
from app.media.audio.music import generate_music
from app.media.audio.sfx import generate_sfx
from app.media.audio.synth import SR
from app.schemas.core import (
    MusicTrackOut,
    StoryDnaIn,
    StoryDnaOut,
    TemplateIn,
    TemplateOut,
    VoiceOut,
    VoicePreviewIn,
    VoiceProfileIn,
    VoiceProfileOut,
)

router = APIRouter(tags=["creative"])


def _dna_values(body: StoryDnaIn) -> dict:
    data = body.model_dump(mode="json")
    data["caption_style"] = body.caption_style.clean()
    data["visual_references"] = [str(v) for v in body.visual_references]
    return data


# ---- Story DNA -----------------------------------------------------------------------------------------
@router.get("/story-dna", response_model=list[StoryDnaOut])
def list_dna(session: DbSession, user: CurrentUser) -> list[StoryDnaOut]:
    rows = session.scalars(select(StoryDnaProfile).where(StoryDnaProfile.user_id == user.id).order_by(StoryDnaProfile.name))
    return [StoryDnaOut.model_validate(r) for r in rows]


@router.post("/story-dna", response_model=StoryDnaOut, status_code=status.HTTP_201_CREATED)
def create_dna(body: StoryDnaIn, session: DbSession, user: CurrentUser) -> StoryDnaOut:
    for ref in body.visual_references:
        owned(session, MediaAsset, ref, user)
    dna = StoryDnaProfile(user_id=user.id, **_dna_values(body))
    session.add(dna)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ConflictError("A Story DNA profile with this name already exists") from exc
    return StoryDnaOut.model_validate(dna)


@router.put("/story-dna/{dna_id}", response_model=StoryDnaOut)
def update_dna(dna_id: uuid.UUID, body: StoryDnaIn, session: DbSession, user: CurrentUser) -> StoryDnaOut:
    dna = owned(session, StoryDnaProfile, dna_id, user)
    for ref in body.visual_references:
        owned(session, MediaAsset, ref, user)
    for key, value in _dna_values(body).items():
        setattr(dna, key, value)
    session.flush()
    return StoryDnaOut.model_validate(dna)


@router.delete("/story-dna/{dna_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dna(dna_id: uuid.UUID, session: DbSession, user: CurrentUser) -> None:
    session.delete(owned(session, StoryDnaProfile, dna_id, user))


# ---- Voice Studio ----------------------------------------------------------------------------------------
@router.get("/voices", response_model=list[VoiceOut])
def voices(providers: ProvidersDep) -> list[VoiceOut]:
    return [VoiceOut(**v.__dict__) for v in providers.tts.list_voices()]


@router.post("/voices/preview")
def preview_voice(body: VoicePreviewIn, settings: SettingsDep, providers: ProvidersDep, user: CurrentUser) -> FileResponse:
    """Synthesise a short sample. Cached by input so repeated previews are instant."""
    cache = settings.work_root / "voice-previews"
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / f"{hash_inputs(providers.tts.name, body.voice_id, body.speed, body.language, body.text)}.wav"
    if not out.exists():
        tmp = out.with_suffix(".part.wav")
        providers.tts.generate_speech(body.text, body.voice_id, body.speed, tmp, body.language)
        tmp.replace(out)
    return FileResponse(out, media_type="audio/wav")


@router.get("/voice-profiles", response_model=list[VoiceProfileOut])
def list_voice_profiles(session: DbSession, user: CurrentUser) -> list[VoiceProfileOut]:
    rows = session.scalars(select(VoiceProfile).where(VoiceProfile.user_id == user.id).order_by(VoiceProfile.name))
    return [VoiceProfileOut.model_validate(r) for r in rows]


@router.post("/voice-profiles", response_model=VoiceProfileOut, status_code=status.HTTP_201_CREATED)
def create_voice_profile(body: VoiceProfileIn, session: DbSession, providers: ProvidersDep, user: CurrentUser) -> VoiceProfileOut:
    profile = VoiceProfile(user_id=user.id, provider=providers.tts.name, **body.model_dump())
    session.add(profile)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ConflictError("A voice profile with this name already exists") from exc
    return VoiceProfileOut.model_validate(profile)


@router.delete("/voice-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_voice_profile(profile_id: uuid.UUID, session: DbSession, user: CurrentUser) -> None:
    session.delete(owned(session, VoiceProfile, profile_id, user))


# ---- Templates (community foundation, no payments) -------------------------------------------------------
@router.get("/templates", response_model=list[TemplateOut])
def list_templates(session: DbSession, user: CurrentUser) -> list[TemplateOut]:
    rows = session.scalars(select(Template).where(or_(Template.user_id == user.id, Template.is_public.is_(True),
                                                      Template.is_builtin.is_(True))).order_by(Template.is_builtin.desc(), Template.name))  # fmt: skip
    out = []
    for t in rows:
        item = TemplateOut.model_validate(t)
        item.owned = t.user_id == user.id
        out.append(item)
    return out


@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateIn, request: Request, session: DbSession, user: CurrentUser) -> TemplateOut:
    config = dict(body.config)
    if body.project_id:
        project = owned(session, Project, body.project_id, user)
        s = project.settings
        config = {
            "duration_seconds": s.duration_seconds, "aspect_ratio": s.aspect_ratio, "platform": s.platform,
            "visual_style": s.visual_style, "story_tone": s.story_tone, "voice_id": s.voice_id, "voice_speed": s.voice_speed,
            "caption_style": s.caption_style, "music": {k: v for k, v in s.music.items() if k != "track_id"},
            "sfx_enabled": s.sfx_enabled,
        }  # fmt: skip
    if len(str(config)) > 8000:
        raise ValidationFailedError("Template configuration too large")
    template = Template(user_id=user.id, name=body.name, description=body.description, category=body.category,
                        is_public=body.is_public, config=config)  # fmt: skip
    session.add(template)
    session.flush()
    audit(session, request, user.id, "template.create", "template", template.id, public=body.is_public)
    out = TemplateOut.model_validate(template)
    out.owned = True
    return out


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: uuid.UUID, session: DbSession, user: CurrentUser) -> None:
    session.delete(owned(session, Template, template_id, user))


# ---- Music & sound effects ------------------------------------------------------------------------------
@router.get("/music", response_model=list[MusicTrackOut])
def music_tracks(session: DbSession, settings: SettingsDep, storage: StorageDep, user: CurrentUser) -> list[MusicTrackOut]:
    builtin = [MusicTrackOut(id=None, name=f"{m.value.title()} score", mood=m.value, source="procedural",
                             license_note="Generated locally by ReelForge; royalty-free", preview_url=None)
               for m in MusicMood if m is not MusicMood.NONE]  # fmt: skip
    uploads = []
    for track in session.scalars(select(MusicTrack).where(MusicTrack.user_id == user.id).order_by(MusicTrack.created_at.desc())):
        asset = session.get(MediaAsset, track.media_asset_id) if track.media_asset_id else None
        uploads.append(MusicTrackOut(id=track.id, name=track.name, mood=track.mood, source=track.source,
                                     license_note=track.license_note,
                                     preview_url=media_url(settings, storage, asset) if asset else None))  # fmt: skip
    return builtin + uploads


def _cached_wav(settings, name: str, make) -> Path:  # type: ignore[no-untyped-def]
    cache = settings.work_root / "audio-previews"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{name}.wav"
    if not path.exists():
        sf.write(str(path), make(), SR, subtype="PCM_16")
    return path


@router.get("/music/moods/{mood}/preview")
def music_preview(mood: MusicMood, settings: SettingsDep, user: CurrentUser) -> FileResponse:
    if mood is MusicMood.NONE:
        raise NotFoundError("No preview for 'none'")
    cues = [(0.0, "steady"), (8.0, "build"), (14.0, "tension")]
    return FileResponse(_cached_wav(settings, f"music-{mood.value}", lambda: generate_music(mood.value, 20.0, cues, 7)),
                        media_type="audio/wav")  # fmt: skip


@router.get("/sfx")
def list_sfx() -> list[dict]:
    return [{"kind": s.value, "license_note": "Synthesised locally; royalty-free"} for s in SoundEffect]


@router.get("/sfx/{kind}/preview")
def sfx_preview(kind: SoundEffect, settings: SettingsDep, user: CurrentUser) -> FileResponse:
    return FileResponse(_cached_wav(settings, f"sfx-{kind.value}", lambda: generate_sfx(kind.value, 4.0, 3)), media_type="audio/wav")
