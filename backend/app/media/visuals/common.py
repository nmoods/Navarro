"""Shared drawing helpers for procedural visuals."""

from __future__ import annotations

import textwrap

import numpy as np

from app.media.captions import _sprite, alpha_composite
from app.media.color import gradient_canvas, palette_bgr
from app.media.effects import fractal_noise
from app.media.spec import SceneSpec


def bgr_to_hex(c: tuple[int, int, int]) -> str:
    b, g, r = c
    return f"#{r:02X}{g:02X}{b:02X}"


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(x * (1 - t) + y * t) for x, y in zip(a, b, strict=True))  # type: ignore[return-value]


def draw_text(
    frame: np.ndarray,
    text: str,
    x: int,
    y: int,
    *,
    px: int,
    family: str = "Montserrat",
    weight: int = 700,
    color: str = "#FFFFFF",
    stroke: str = "#000000",
    stroke_px: int = 0,
    anchor: str = "lt",  # l/m/r + t/m/b
    opacity: float = 1.0,
    shadow: bool = False,
) -> tuple[int, int]:
    if not text:
        return 0, 0
    sprite = _sprite(text, family, weight, px, color, stroke, stroke_px, shadow)
    h, w = sprite.shape[:2]
    if anchor[0] == "m":
        x -= w // 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "m":
        y -= h // 2
    elif anchor[1] == "b":
        y -= h
    alpha_composite(frame, sprite, x, y, opacity)
    return w, h


def wrap(text: str, chars: int) -> list[str]:
    return textwrap.wrap(text, width=max(6, chars)) or [""]


def themed_background(spec: SceneSpec, w: int, h: int, darkness: float = 0.75) -> np.ndarray:
    pal = palette_bgr(spec.palette)
    top = mix(pal[0], (8, 8, 12), darkness)
    bottom = mix(pal[1], (10, 8, 14), min(0.92, darkness + 0.1))
    bg = gradient_canvas(w, h, top, bottom)
    rng = np.random.default_rng(spec.seed + 7)
    noise = fractal_noise(max(8, w // 6), max(8, h // 6), rng, octaves=4)
    import cv2

    tex = cv2.resize(noise, (w, h))[..., None]
    return np.clip(bg.astype(np.float32) * (0.8 + 0.4 * tex), 0, 255).astype(np.uint8)


def ease(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3
