"""Production pipeline: ensure scene assets (cached by input hash) -> render scene clips (cached) -> mix
audio -> assemble MP4 -> thumbnail -> export record.

Re-running after an edit only regenerates what changed: a caption tweak re-renders that scene's clip but
reuses its image and narration; a narration edit regenerates that scene's voice + transcript only.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import cv2
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application import prompts
from app.application.assets import hash_inputs, store_bytes, store_file
from app.application.ports import ImageRequest, TimedWord
from app.application.story_service import current_storyboard, latest_script
from app.core.config import Settings
from app.domain.enums import AspectRatio, JobStatus, ProjectStatus, VisualType
from app.infrastructure.audio.whisper import align_to_script
from app.infrastructure.database.models import (
    ContentSeries,
    MediaAsset,
    MusicTrack,
    Project,
    Scene,
    SceneAsset,
    StoryDnaProfile,
    VideoExport,
)
from app.infrastructure.providers import Providers
from app.infrastructure.storage.base import Storage
from app.media.assembler import SceneTiming, assemble, plan_timeline
from app.media.audio.mixer import mix_timeline
from app.media.ffmpeg import media_duration
from app.media.scene_renderer import render_scene, render_still
from app.media.spec import (
    AudioCue,
    CaptionStyle,
    CaptionWord,
    RenderSettings,
    SceneSpec,
    SfxCue,
    TimelineSpec,
)
from app.media.visuals.common import draw_text
from app.workers.context import JobContext

logger = logging.getLogger("narravo.production")

# SD 1.5 is trained at 512 px; very elongated canvases duplicate subjects (two heads, two towers). Generate at
# moderate aspect ratios and let the compositor crop to the output format.
IMAGE_SIZES = {AspectRatio.VERTICAL: (512, 768), AspectRatio.LANDSCAPE: (768, 512), AspectRatio.SQUARE: (576, 576)}
PORTRAIT_SIZE = (512, 640)
NON_AI_IMAGES = frozenset({"procedural", "fixture_image"})
_CAPTION_FIELDS = set(CaptionStyle.__dataclass_fields__)


@dataclass
class SceneAssets:
    scene: Scene
    image: MediaAsset | None
    narration: MediaAsset
    words: list[TimedWord]


def current_asset(session: Session, scene_id: uuid.UUID, role: str) -> tuple[SceneAsset, MediaAsset] | None:
    row = session.execute(
        select(SceneAsset, MediaAsset)
        .join(MediaAsset, MediaAsset.id == SceneAsset.media_asset_id)
        .where(SceneAsset.scene_id == scene_id, SceneAsset.role == role, SceneAsset.is_current.is_(True))
        .order_by(SceneAsset.created_at.desc())
    ).first()
    return (row[0], row[1]) if row else None


def attach(session: Session, scene: Scene, role: str, asset: MediaAsset, input_hash: str, provider: str, details: dict | None = None) -> None:
    for old in session.scalars(select(SceneAsset).where(SceneAsset.scene_id == scene.id, SceneAsset.role == role, SceneAsset.is_current.is_(True))):
        old.is_current = False
    session.add(SceneAsset(scene_id=scene.id, role=role, media_asset_id=asset.id, input_hash=input_hash, provider=provider,
                           details=details or {}))  # fmt: skip
    session.flush()


def caption_style(project: Project, scene: Scene | None = None, scale: float = 1.0) -> CaptionStyle:
    data = {k: v for k, v in (project.settings.caption_style or {}).items() if k in _CAPTION_FIELDS}
    if scene is not None:
        data |= {k: v for k, v in (scene.caption_override or {}).items() if k in _CAPTION_FIELDS}
    return CaptionStyle(**data)


class ProductionService:
    def __init__(self, session: Session, settings: Settings, providers: Providers, storage: Storage, ctx: JobContext) -> None:
        self.session, self.settings, self.providers, self.storage, self.ctx = session, settings, providers, storage, ctx
        self.work = Path(tempfile.mkdtemp(prefix="job-", dir=self._ensure(settings.work_root / "jobs")))
        self.clip_cache = self._ensure(settings.work_root / "clips")

    @staticmethod
    def _ensure(path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cleanup(self) -> None:
        shutil.rmtree(self.work, ignore_errors=True)

    # -- prompts --------------------------------------------------------------------------------------
    def image_prompt(self, project: Project, scene: Scene) -> str:
        parts = [scene.image_prompt or scene.visual_description, prompts.STYLE_PROMPTS.get(project.settings.visual_style, "")]
        if project.settings.style_prompt:
            parts.append(project.settings.style_prompt)
        if project.story_dna_id and (dna := self.session.get(StoryDnaProfile, project.story_dna_id)) and dna.style_prompt:
            parts.append(dna.style_prompt)
        if scene.characters and project.series_id and (series := self.session.get(ContentSeries, project.series_id)):
            lookup = {c["name"].lower(): c["visual_description"] for c in (series.bible or {}).get("recurring_characters", [])}
            parts += [f"{name}: {lookup[name.lower()]}" for name in scene.characters if name.lower() in lookup]
        return ", ".join(p.strip() for p in parts if p and p.strip())[:900]

    def _character_seed(self, project: Project, scene: Scene) -> int:
        """Visual memory: scenes featuring the same series character share a seed for consistent looks."""
        if scene.characters and project.series_id:
            return int(hash_inputs(str(project.series_id), scene.characters[0].lower())[:8], 16) % (2**31)
        return scene.image_seed

    # -- assets -----------------------------------------------------------------------------------------
    def ensure_image(self, project: Project, scene: Scene) -> MediaAsset | None:
        if not VisualType(scene.visual_type).needs_ai_image:
            return None
        existing = current_asset(self.session, scene.id, "image")
        if existing and existing[0].details.get("locked"):
            return existing[1]  # user-uploaded or pinned image: never overwrite
        provider = self.providers.image_for_generation()
        w, h = IMAGE_SIZES[AspectRatio(project.settings.aspect_ratio)]
        if scene.visual_type == "character_portrait" and project.settings.aspect_ratio != "16:9":
            w, h = PORTRAIT_SIZE
        seed = self._character_seed(project, scene)
        prompt = self.image_prompt(project, scene)
        # The key is what the image should show, not which engine drew it: switching image engines must not
        # redraw every unchanged scene. A placeholder drawn while AI was offline is still upgraded later.
        digest = hash_inputs("image", prompt, prompts.NEGATIVE_PROMPT, w, h, seed)
        if existing and existing[0].input_hash == digest and (existing[0].provider not in NON_AI_IMAGES or provider.name in NON_AI_IMAGES):
            return existing[1]
        request = ImageRequest(prompt, prompts.NEGATIVE_PROMPT, w, h, seed)
        if provider.name in ("procedural", "fixture_image"):
            image = provider.generate_image(request, tuple(scene.color_palette) or None)  # type: ignore[call-arg]
        else:
            image = provider.generate_image(request)
        asset = store_bytes(self.session, self.storage, user_id=project.user_id, kind="image", source=image.source,
                            data=image.data, mime="image/png", width=image.width, height=image.height,
                            details={"prompt": prompt, "seed": seed, "model": image.model, "provider": image.provider})  # fmt: skip
        attach(self.session, scene, "image", asset, digest, image.provider, {"prompt": prompt})
        return asset

    def ensure_narration(self, project: Project, scene: Scene) -> MediaAsset:
        s = project.settings
        tts = self.providers.tts
        digest = hash_inputs("tts", tts.name, s.voice_id, round(s.voice_speed, 2), s.language, scene.narration)
        existing = current_asset(self.session, scene.id, "narration")
        if existing and existing[0].input_hash == digest:
            return existing[1]
        out = self.work / f"narration-{scene.id.hex}.wav"
        result = tts.generate_speech(scene.narration, s.voice_id, s.voice_speed, out, s.language)
        asset = store_file(self.session, self.storage, user_id=project.user_id, kind="audio", source=result.source, path=out,
                           mime="audio/wav", duration=result.duration,
                           details={"voice": s.voice_id, "speed": s.voice_speed, "provider": result.provider})  # fmt: skip
        attach(self.session, scene, "narration", asset, digest, result.provider)
        return asset

    def ensure_transcript(self, project: Project, scene: Scene, narration: MediaAsset) -> list[TimedWord]:
        stt = self.providers.stt
        digest = hash_inputs("stt", stt.name, getattr(stt, "model_name", ""), narration.sha256, scene.narration)
        existing = current_asset(self.session, scene.id, "transcript")
        if existing and existing[0].input_hash == digest:
            words = existing[0].details.get("words", [])
            return [TimedWord(w["text"], w["start"], w["end"]) for w in words]
        audio_path = self.storage.local_path(narration.storage_key)
        duration = narration.duration_seconds or media_duration(audio_path)
        try:
            recognised = stt.get_word_timestamps(audio_path, project.settings.language)
            method = "whisper-aligned" if recognised else "estimated"
        except Exception as exc:  # STT is optional: fall back to estimated timings, and say so
            logger.warning("transcription failed, using estimated timings: %s", exc)
            self.ctx.log("warning", f"Transcription unavailable, using estimated caption timing ({type(exc).__name__})")
            recognised, method = [], "estimated"
        words = align_to_script(scene.narration, recognised, duration)
        payload = [{"text": w.text, "start": round(w.start, 3), "end": round(w.end, 3)} for w in words]
        import json

        asset = store_bytes(self.session, self.storage, user_id=project.user_id, kind="transcript", source="generated",
                            data=json.dumps(payload).encode(), mime="application/json", details={"method": method})  # fmt: skip
        attach(self.session, scene, "transcript", asset, digest, stt.name, {"words": payload, "method": method})
        return words

    def ensure_assets(self, project: Project, scenes: list[Scene], start: float, end: float) -> list[SceneAssets]:
        out = []
        n = len(scenes)
        for i, scene in enumerate(scenes):
            frac = start + (end - start) * i / max(1, n)
            self.ctx.stage(JobStatus.IMAGE_GENERATION, frac, f"Scene {i + 1}/{n}: visuals")
            image = self.ensure_image(project, scene)
            self.session.commit()
            self.ctx.stage(JobStatus.VOICE_GENERATION, frac + (end - start) / n * 0.5, f"Scene {i + 1}/{n}: voiceover")
            narration = self.ensure_narration(project, scene)
            words = self.ensure_transcript(project, scene, narration)
            self.session.commit()
            out.append(SceneAssets(scene, image, narration, words))
        return out

    # -- render --------------------------------------------------------------------------------------
    def build_specs(self, project: Project, assets: list[SceneAssets], timings: list[SceneTiming]) -> list[SceneSpec]:
        brand = (project.settings.brand or {}).get("handle", "")
        specs = []
        for a, timing in zip(assets, timings, strict=True):
            sc = a.scene
            emphasis = {w.lower() for w in sc.emphasis_words}
            offset = timing.narration_offset + (sc.caption_override or {}).get("offset_ms", 0) / 1000
            captions = tuple(
                CaptionWord(w.text, w.start + offset, w.end + offset, w.text.strip(".,!?;:\"'").lower() in emphasis)
                for w in a.words
            )
            image_path = self.storage.local_path(a.image.storage_key) if a.image else None
            specs.append(SceneSpec(
                index=sc.position, visual_type=sc.visual_type, duration=round(timing.duration, 3),
                narration_offset=timing.narration_offset, camera=sc.camera_movement, effects=tuple(sc.effects),
                image_path=image_path, visual_data=sc.visual_data, palette=tuple(sc.color_palette), title=sc.title,
                style=project.settings.visual_style, captions=captions, caption_style=caption_style(project, sc),
                characters=tuple(sc.characters), seed=sc.image_seed % 100000, brand_text=brand,
            ))  # fmt: skip
        return specs

    def render_clips(self, specs: list[SceneSpec], assets: list[SceneAssets], rs: RenderSettings, start: float, end: float) -> list[Path]:
        paths: list[Path | None] = [None] * len(specs)
        todo = []
        for i, (spec, a) in enumerate(zip(specs, assets, strict=True)):
            key = spec.cache_key(rs, a.image.sha256 if a.image else None)
            cached = self.clip_cache / f"{key}.mp4"
            if cached.exists():
                paths[i] = cached
            else:
                todo.append((i, spec, cached))
        self.ctx.stage(JobStatus.ANIMATION, start, f"Animating {len(todo)} scene(s), {len(specs) - len(todo)} reused from cache")
        workers = max(1, min(self.settings.worker_concurrency * 3, len(todo), 4))
        threads = max(1, self.settings.ffmpeg_threads // workers)
        if workers == 1 or len(todo) <= 1:
            for k, (i, spec, cached) in enumerate(todo):
                tmp = cached.with_suffix(".part.mp4")
                render_scene(spec, rs, tmp, cancel_check=self.ctx.cancelled, threads=threads,
                             on_progress=lambda p, k=k: self.ctx.progress(start + (end - start) * (k + p) / len(todo),
                                                                        f"Rendering scene {k + 1}/{len(todo)}"))  # fmt: skip
                tmp.replace(cached)
                paths[i] = cached
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_render_to, spec, rs, cached, threads): i for i, spec, cached in todo}
                for done, fut in enumerate(as_completed(futures), start=1):
                    paths[futures[fut]] = fut.result()
                    self.ctx.progress(start + (end - start) * done / len(todo), f"Rendered {done}/{len(todo)} scenes")
                    if self.ctx.cancelled():
                        for f in futures:
                            f.cancel()
                        self.ctx.check()
        return [p for p in paths if p is not None]

    def produce(self, project: Project, *, quality: str = "final", job_id: uuid.UUID | None = None) -> VideoExport:
        board = current_storyboard(self.session, project.id)
        if board is None or not board.scenes:
            raise ValueError("Project has no storyboard yet")
        scenes = sorted(board.scenes, key=lambda s: s.position)
        project.status = ProjectStatus.PRODUCING.value
        self.session.commit()
        assets = self.ensure_assets(project, scenes, 2, 45)

        ps = project.settings
        width, height = AspectRatio(ps.aspect_ratio).resolution
        rs = RenderSettings(width, height, ps.fps, quality)
        if quality == "draft":
            rs = rs.scaled(0.5)
        transitions = [sc.transition for sc in scenes]
        lengths = [a.narration.duration_seconds or 1.0 for a in assets]
        timings, total = plan_timeline(lengths, transitions, [sc.duration_override for sc in scenes])
        specs = self.build_specs(project, assets, timings)
        clips = self.render_clips(specs, assets, rs, 46, 85)

        self.ctx.stage(JobStatus.RENDERING, 86, "Mixing narration, music and sound effects")
        timeline = self.build_audio(project, assets, scenes, timings)
        mix = mix_timeline(timeline, total, self.work / "mix.wav")
        self.ctx.stage(JobStatus.RENDERING, 90, "Assembling transitions and encoding MP4")
        video_path = assemble(clips, timings, transitions, mix, self.work / "final.mp4", rs, total,
                              timeout=self.settings.render_timeout_seconds, threads=0,  # 0 = all cores: nothing else runs during assembly
                              cancel_check=self.ctx.cancelled)  # fmt: skip

        self.ctx.stage(JobStatus.FINALIZING, 96, "Generating thumbnail and saving export")
        thumb_path = self.thumbnail(project, specs[0], rs)
        render_hash = hash_inputs([s.cache_key(rs, a.image.sha256 if a.image else None) for s, a in zip(specs, assets, strict=True)],
                                  timeline.music_mood, transitions)  # fmt: skip
        video = store_file(self.session, self.storage, user_id=project.user_id, kind="video", source="generated", path=video_path,
                           mime="video/mp4", width=rs.width, height=rs.height, duration=total,
                           original_name=f"{_slug(project.title)}.mp4")  # fmt: skip
        thumb = store_file(self.session, self.storage, user_id=project.user_id, kind="thumbnail", source="generated",
                           path=thumb_path, mime="image/jpeg", width=rs.width, height=rs.height)  # fmt: skip
        export = VideoExport(user_id=project.user_id, project_id=project.id, job_id=job_id, video_asset_id=video.id,
                             thumbnail_asset_id=thumb.id, quality=quality, aspect_ratio=ps.aspect_ratio, width=rs.width,
                             height=rs.height, fps=rs.fps, duration_seconds=round(total, 2), render_hash=render_hash,
                             details={"scenes": len(scenes), "image_sources": sorted({a.image.source for a in assets if a.image})})  # fmt: skip
        self.session.add(export)
        project.thumbnail_asset_id = thumb.id
        project.status = ProjectStatus.READY.value
        project.last_error = None
        self.session.commit()
        return export

    def build_audio(self, project: Project, assets: list[SceneAssets], scenes: list[Scene], timings: list[SceneTiming]) -> TimelineSpec:
        ps = project.settings
        music = ps.music or {}
        narration = [AudioCue(self.storage.local_path(a.narration.storage_key), t.start + t.narration_offset)
                     for a, t in zip(assets, timings, strict=True)]  # fmt: skip
        sfx: list[SfxCue] = []
        if ps.sfx_enabled:
            for sc, t in zip(scenes, timings, strict=True):
                if sc.position > 0 and sc.transition not in ("cut", "crossfade", "dissolve"):
                    sfx.append(SfxCue("whoosh", max(0.0, t.start - 0.15), 1.0, -16))
                for kind in sc.sound_effects[:2]:
                    one_shot = kind in ("whoosh", "impact", "riser", "paper", "shimmer", "thunder")
                    sfx.append(SfxCue(kind, t.start + (0.1 if one_shot else 0.0), t.duration, -12 if one_shot else -22))
        music_path = None
        if music.get("track_id"):
            track = self.session.get(MusicTrack, uuid.UUID(str(music["track_id"])))
            if track and track.media_asset_id and track.user_id in (None, project.user_id):
                asset = self.session.get(MediaAsset, track.media_asset_id)
                music_path = self.storage.local_path(asset.storage_key) if asset else None
        script = latest_script(self.session, project.id)
        mood = music.get("mood") or (script.brief.get("music_mood") if script else None) or "mystery"
        return TimelineSpec(
            scenes=[], transitions=[sc.transition for sc in scenes], narration=narration, sfx=sfx,
            music_mood="none" if music.get("enabled") is False else mood, music_volume_db=float(music.get("volume_db", -20)),
            music_path=music_path, music_cues=[(t.start, sc.music_cue) for sc, t in zip(scenes, timings, strict=True)],
            seed=int(project.id.int % 10_000),
        )  # fmt: skip

    def thumbnail(self, project: Project, first: SceneSpec, rs: RenderSettings) -> Path:
        frame = render_still(first, rs, min(first.duration * 0.6, 2.5))
        w, h = rs.width, rs.height
        shade = cv2.addWeighted(frame, 0.55, frame * 0, 0.45, 0)
        frame[int(h * 0.55) :] = shade[int(h * 0.55) :]
        words = project.title.upper().split()
        lines, line = [], ""
        for word in words:
            if len(line) + len(word) > 14 and line:
                lines.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        lines.append(line)
        y = int(h * 0.62)
        for ln in lines[:4]:
            _, lh = draw_text(frame, ln, w // 2, y, px=int(w * 0.11), family="Anton", weight=400, color="#FFFFFF",
                              stroke="#000000", stroke_px=max(2, w // 200), anchor="mt", shadow=True)  # fmt: skip
            y += int(lh * 1.02)
        out = self.work / "thumbnail.jpg"
        cv2.imwrite(str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return out


def _render_to(spec: SceneSpec, rs: RenderSettings, cached: Path, threads: int) -> Path:
    tmp = cached.with_suffix(f".{uuid.uuid4().hex[:6]}.part.mp4")
    render_scene(spec, rs, tmp, threads=threads)
    tmp.replace(cached)
    return cached


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")[:60] or "narravo-video"
