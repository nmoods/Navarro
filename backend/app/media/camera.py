"""Virtual camera: maps scene time to a crop window (zoom, centre, rotation) over an oversized source."""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

HEADROOM = 1.22  # source images are prepared this much larger than the output to allow moves


@dataclass(frozen=True)
class CameraState:
    zoom: float  # 1.0 == the whole headroom-sized source fills the frame... see window()
    cx: float  # normalised centre in source (0..1)
    cy: float
    angle: float = 0.0  # degrees


def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, t)))


def ease_out_cubic(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def ease_in_quad(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _drift(seed: int, t: float, freq: float, amp: float) -> float:
    """Smooth pseudo-random wobble (sum of incommensurate sines), deterministic per seed."""
    r = (seed % 997) / 997.0
    return amp * (
        0.6 * math.sin(2 * math.pi * (freq * t + r))
        + 0.3 * math.sin(2 * math.pi * (freq * 2.31 * t + r * 3.7))
        + 0.1 * math.sin(2 * math.pi * (freq * 5.13 * t + r * 7.1))
    )


def camera_at(move: str, t: float, duration: float, seed: int = 0) -> CameraState:
    """Camera state at time ``t``. zoom is relative to the output frame (1.0 = source scaled to cover)."""
    p = t / max(duration, 1e-3)
    e = ease_in_out(p)
    match move:
        case "static":
            return CameraState(1.04, 0.5, 0.5)
        case "slow_zoom_in":
            return CameraState(_lerp(1.0, 1.14, e), 0.5, 0.5)
        case "slow_zoom_out":
            return CameraState(_lerp(1.16, 1.0, e), 0.5, 0.5)
        case "pan_left":
            return CameraState(1.12, _lerp(0.56, 0.44, e), 0.5)
        case "pan_right":
            return CameraState(1.12, _lerp(0.44, 0.56, e), 0.5)
        case "tilt_up":
            return CameraState(1.12, 0.5, _lerp(0.57, 0.43, e))
        case "tilt_down":
            return CameraState(1.12, 0.5, _lerp(0.43, 0.57, e))
        case "dramatic_push_in":
            return CameraState(_lerp(1.0, 1.32, ease_in_quad(p)), 0.5, _lerp(0.5, 0.46, e))
        case "crash_zoom":
            punch = ease_out_cubic(min(1.0, t / 0.45))
            return CameraState(_lerp(1.0, 1.28, punch) + 0.04 * p, 0.5, 0.48)
        case "handheld":
            return CameraState(
                1.1 + _drift(seed, t, 0.11, 0.01),
                0.5 + _drift(seed + 1, t, 0.17, 0.012),
                0.5 + _drift(seed + 2, t, 0.13, 0.01),
                _drift(seed + 3, t, 0.09, 0.45),
            )
        case "parallax_drift":
            return CameraState(_lerp(1.06, 1.12, e), _lerp(0.46, 0.54, e), 0.5)
        case _:  # ken_burns and unknown values
            direction = -1 if seed % 2 else 1
            return CameraState(_lerp(1.03, 1.17, e), 0.5 + direction * _lerp(-0.035, 0.035, e), _lerp(0.53, 0.47, e))


def camera_matrix(state: CameraState, src_w: int, src_h: int, out_w: int, out_h: int) -> np.ndarray:
    """Affine matrix mapping source pixels to output pixels for ``cv2.warpAffine``.

    The source is HEADROOM x the cover size; zoom=1 shows exactly the cover-sized area (1/HEADROOM).
    """
    base_scale = out_w / (src_w / HEADROOM)
    scale = base_scale * state.zoom
    view_w, view_h = out_w / scale, out_h / scale
    cx = min(max(state.cx * src_w, view_w / 2), src_w - view_w / 2)
    cy = min(max(state.cy * src_h, view_h / 2), src_h - view_h / 2)
    m = cv2.getRotationMatrix2D((cx, cy), state.angle, scale)
    m[0, 2] += out_w / 2 - cx
    m[1, 2] += out_h / 2 - cy
    return m


def apply_camera(src: np.ndarray, state: CameraState, out_w: int, out_h: int) -> np.ndarray:
    m = camera_matrix(state, src.shape[1], src.shape[0], out_w, out_h)
    return cv2.warpAffine(src, m, (out_w, out_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
