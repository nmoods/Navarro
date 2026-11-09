"""Colour utilities and per-style cinematic grading (applied once per source image, not per frame)."""

from __future__ import annotations

import cv2
import numpy as np

DEFAULT_PALETTE = ("#0B0B12", "#7C3AED", "#38BDF8")


def hex_to_bgr(value: str, fallback: tuple[int, int, int] = (255, 255, 255)) -> tuple[int, int, int]:
    v = value.lstrip("#")
    if len(v) not in (6, 8):
        return fallback
    try:
        r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    except ValueError:
        return fallback
    return b, g, r


def hex_to_rgba(value: str) -> tuple[int, int, int, int]:
    v = value.lstrip("#")
    try:
        r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
        a = int(v[6:8], 16) if len(v) == 8 else 255
    except (ValueError, IndexError):
        return 255, 255, 255, 255
    return r, g, b, a


def palette_bgr(palette: tuple[str, ...] | list[str]) -> list[tuple[int, int, int]]:
    colors = [hex_to_bgr(c) for c in palette if c] or [hex_to_bgr(c) for c in DEFAULT_PALETTE]
    while len(colors) < 3:
        colors.append(hex_to_bgr(DEFAULT_PALETTE[len(colors)]))
    return colors


def _curve_lut(shadows: float, highlights: float, gamma: float, lift: float) -> np.ndarray:
    x = np.linspace(0, 1, 256)
    y = np.clip((x - shadows) / max(1e-3, highlights - shadows), 0, 1) ** gamma
    y = lift + y * (1 - lift)
    return np.clip(y * 255, 0, 255).astype(np.uint8)


# (saturation, contrast lut params, shadow tint BGR, highlight tint BGR, tint strength)
_GRADES: dict[str, tuple[float, tuple[float, float, float, float], tuple[int, int, int], tuple[int, int, int], float]] = {
    "cinematic_documentary": (1.05, (0.04, 0.97, 1.05, 0.02), (90, 60, 20), (60, 150, 230), 0.16),
    "historical_realism": (0.82, (0.03, 0.98, 1.0, 0.03), (40, 50, 60), (120, 180, 220), 0.14),
    "dark_mystery": (0.75, (0.08, 0.92, 1.25, 0.0), (80, 50, 20), (160, 170, 150), 0.2),
    "animation_3d": (1.2, (0.02, 0.98, 0.95, 0.02), (60, 30, 30), (200, 210, 255), 0.06),
    "anime": (1.25, (0.02, 0.97, 0.92, 0.03), (90, 40, 60), (210, 220, 255), 0.06),
    "vintage_documentary": (0.55, (0.0, 1.0, 0.95, 0.09), (40, 60, 80), (150, 200, 235), 0.32),
    "minimalist_motion": (0.95, (0.02, 0.98, 1.0, 0.02), (40, 30, 30), (230, 230, 230), 0.04),
    "archival_newspaper": (0.0, (0.06, 0.94, 1.1, 0.06), (30, 30, 30), (200, 215, 225), 0.18),
    "photorealistic": (1.0, (0.02, 0.99, 1.0, 0.0), (40, 30, 20), (200, 210, 230), 0.05),
    "illustrated": (1.15, (0.02, 0.98, 0.95, 0.03), (90, 50, 40), (200, 225, 245), 0.08),
}


def grade_image(img: np.ndarray, style: str) -> np.ndarray:
    sat, (sh, hi, gamma, lift), shadow_tint, high_tint, strength = _GRADES.get(
        style, _GRADES["cinematic_documentary"]
    )
    out = cv2.LUT(img, _curve_lut(sh, hi, gamma, lift))
    if abs(sat - 1.0) > 1e-3:
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[..., 1] = np.clip(hsv[..., 1] * sat, 0, 255)
        out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    if strength > 0:
        lum = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None] / 255.0
        tint = (1 - lum) * np.array(shadow_tint, np.float32) + lum * np.array(high_tint, np.float32)
        out = np.clip(out.astype(np.float32) * (1 - strength) + tint * strength * (0.5 + lum), 0, 255)
        out = out.astype(np.uint8)
    return out


def vignette_mask(width: int, height: int, strength: float = 0.45, roundness: float = 1.0) -> np.ndarray:
    """uint8 3-channel multiplier (255 = untouched) for ``cv2.multiply(frame, mask, scale=1/255)``."""
    ys = np.linspace(-1, 1, height, dtype=np.float32)[:, None]
    xs = np.linspace(-1, 1, width, dtype=np.float32)[None, :] * (width / height) ** (0.5 * roundness)
    d = np.sqrt(xs**2 + ys**2) / np.sqrt(2)
    mask = 1.0 - strength * np.clip((d - 0.35) / 0.65, 0, 1) ** 1.6
    m = (mask * 255).astype(np.uint8)
    return cv2.merge([m, m, m])


def cover_resize(img: np.ndarray, width: int, height: int) -> np.ndarray:
    """Scale to cover (width, height) and centre-crop, like CSS ``object-fit: cover``."""
    h, w = img.shape[:2]
    scale = max(width / w, height / h)
    nw, nh = max(width, round(w * scale)), max(height, round(h * scale))
    interp = cv2.INTER_LANCZOS4 if scale > 1 else cv2.INTER_AREA
    resized = cv2.resize(img, (nw, nh), interpolation=interp)
    x0, y0 = (nw - width) // 2, (nh - height) // 2
    return resized[y0 : y0 + height, x0 : x0 + width].copy()


def sharpen(img: np.ndarray, amount: float = 0.35) -> np.ndarray:
    blur = cv2.GaussianBlur(img, (0, 0), 1.6)
    return cv2.addWeighted(img, 1 + amount, blur, -amount, 0)


def gradient_canvas(width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> np.ndarray:
    t = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
    col = np.array(top, np.float32) * (1 - t) + np.array(bottom, np.float32) * t
    return np.repeat(col, width, axis=1).astype(np.uint8)
