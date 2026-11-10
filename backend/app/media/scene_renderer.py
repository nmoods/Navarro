"""Render one storyboard scene to a silent H.264 clip.

Pipeline per frame: base visual (camera / parallax / procedural visual) -> atmosphere effects -> vignette &
grain -> synchronised captions -> brand mark. Per-scene clips are cached by content hash upstream, so
editing one scene only re-renders that scene.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

from app.core.errors import JobCancelledError
from app.media.camera import HEADROOM, apply_camera, camera_at
from app.media.captions import CaptionRenderer
from app.media.color import cover_resize, grade_image, sharpen
from app.media.effects import EffectStack
from app.media.ffmpeg import FrameWriter
from app.media.parallax import ParallaxLayers, build_layers, render_parallax
from app.media.spec import RenderSettings, SceneSpec
from app.media.visuals.charts import ComparisonVisual, InfographicVisual, TimelineVisual
from app.media.visuals.common import draw_text
from app.media.visuals.map import MapVisual
from app.media.visuals.stills import KineticTypography, newspaper_still, procedural_backdrop

logger = logging.getLogger("narravo.render")

FrameFn = Callable[[float], np.ndarray]
IMAGE_TYPES = {"cinematic_image", "parallax", "character_portrait"}


def load_image(path: Path | None) -> np.ndarray | None:
    if path is None or not path.exists():
        return None
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    return img


def _base_visual(spec: SceneSpec, w: int, h: int) -> FrameFn:
    image = load_image(spec.image_path)
    sw, sh = int(w * HEADROOM) // 2 * 2, int(h * HEADROOM) // 2 * 2
    vt = spec.visual_type
    move = spec.camera
    if vt in IMAGE_TYPES:
        if image is None:
            still, masks = procedural_backdrop(spec, sw, sh)
            layers = ParallaxLayers(
                [still, still, still],
                [np.ones((sh, sw, 1), np.float32), masks[1][..., None], masks[2][..., None]],
                [0.5, 1.0, 1.5],
            )
            move = move if move != "static" else "parallax_drift"
            return lambda t: render_parallax(layers, camera_at(move, t, spec.duration, spec.seed), w, h)
        src = sharpen(grade_image(cover_resize(image, sw, sh), spec.style), 0.25)
        if vt == "parallax":
            layers = build_layers(src)
            return lambda t: render_parallax(layers, camera_at(move, t, spec.duration, spec.seed), w, h)
        if vt == "character_portrait":
            name = spec.characters[0] if spec.characters else ""

            def portrait(t: float) -> np.ndarray:
                frame = apply_camera(src, camera_at(move, t, spec.duration, spec.seed), w, h)
                if name:
                    k = min(1.0, max(0.0, (t - 0.4) / 0.5))
                    x = int(w * 0.07)
                    y = int(h * 0.12)
                    cv2.rectangle(frame, (x - int(w * 0.02), y), (x - int(w * 0.012), y + int(w * 0.075)), (250, 139, 167), -1)
                    draw_text(frame, name.upper(), x, y, px=int(w * 0.055), family="Oswald", weight=700, opacity=k, shadow=True)
                return frame

            return portrait
        return lambda t: apply_camera(src, camera_at(move, t, spec.duration, spec.seed), w, h)
    if vt == "newspaper":
        still = newspaper_still(spec, sw, sh, image)
        move = move if move not in ("static", "handheld") else "slow_zoom_in"
        return lambda t: apply_camera(still, camera_at(move, t, spec.duration, spec.seed), w, h)
    if vt == "historical_map":
        return MapVisual(spec, w, h).frame
    if vt == "timeline":
        return TimelineVisual(spec, w, h).frame
    if vt == "infographic":
        return InfographicVisual(spec, w, h).frame
    if vt == "comparison":
        return ComparisonVisual(spec, w, h, image).frame
    if vt == "kinetic_typography":
        return KineticTypography(spec, w, h).frame
    logger.warning("Unknown visual type %s, using procedural backdrop", vt)
    still, _ = procedural_backdrop(spec, sw, sh)
    return lambda t: apply_camera(still, camera_at(move, t, spec.duration, spec.seed), w, h)


def render_scene(
    spec: SceneSpec,
    settings: RenderSettings,
    out_path: Path,
    *,
    cancel_check: Callable[[], bool] | None = None,
    on_progress: Callable[[float], None] | None = None,
    threads: int = 4,
) -> Path:
    w, h, fps = settings.width, settings.height, settings.fps
    base = _base_visual(spec, w, h)
    effects = EffectStack(spec.effects, w, h, fps, spec.seed, spec.style)
    show_captions = spec.visual_type != "kinetic_typography"
    captions = CaptionRenderer(spec.captions, spec.caption_style, w, h) if show_captions else None
    total = max(1, round(spec.duration * fps))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with FrameWriter(out_path, w, h, fps, crf=14, preset="veryfast", threads=threads) as writer:
        for i in range(total):
            if i % fps == 0:
                if cancel_check and cancel_check():
                    raise JobCancelledError()
                if on_progress:
                    on_progress(i / total)
            t = i / fps
            frame = base(t)
            frame = effects.apply(frame, t, i)
            if captions:
                frame = captions.render(frame, t)
            if spec.brand_text:
                draw_text(frame, spec.brand_text, w - int(w * 0.04), int(h * 0.035), px=int(w * 0.03), weight=700,
                          anchor="rt", opacity=0.6, shadow=True)  # fmt: skip
            writer.write(frame)
    if on_progress:
        on_progress(1.0)
    return out_path


def render_still(spec: SceneSpec, settings: RenderSettings, t: float) -> np.ndarray:
    """Single frame for thumbnails and scene previews (no encoder involved)."""
    base = _base_visual(spec, settings.width, settings.height)
    frame = base(t)
    return EffectStack(spec.effects, settings.width, settings.height, settings.fps, spec.seed, spec.style).apply(frame, t, 0)
