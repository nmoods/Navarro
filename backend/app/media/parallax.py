"""2.5D parallax: split a still into depth layers and move them at different speeds.

Depth comes from a pluggable estimator. The default heuristic needs no model: it combines vertical position
(ground is near), local detail (in-focus subjects are near in typical SD/photographic compositions) and a
centre prior, then smooths the result. Layers are separated with feathered masks; the background behind the
foreground is inpainted so camera moves never reveal holes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

from app.media.camera import CameraState, camera_matrix


class DepthEstimator(Protocol):
    def estimate(self, image: np.ndarray) -> np.ndarray:
        """Return float32 depth in [0, 1] where 1 = nearest, same HxW as image."""
        ...


class HeuristicDepth:
    def estimate(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        small = cv2.resize(image, (max(32, w // 4), max(32, h // 4)), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
        detail = cv2.GaussianBlur(np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3)), (0, 0), 6)
        detail /= max(1e-6, float(np.percentile(detail, 98)))
        sh, sw = gray.shape
        vertical = np.linspace(0.0, 1.0, sh, dtype=np.float32)[:, None] ** 1.3
        xs = np.linspace(-1, 1, sw, dtype=np.float32)[None, :]
        ys = np.linspace(-1, 1, sh, dtype=np.float32)[:, None]
        centre = np.exp(-(xs**2 * 1.2 + (ys - 0.15) ** 2 * 0.8))
        depth = 0.45 * vertical + 0.35 * np.clip(detail, 0, 1) + 0.2 * centre
        depth = cv2.GaussianBlur(depth, (0, 0), max(sw, sh) / 30)
        depth -= depth.min()
        depth /= max(1e-6, depth.max())
        return cv2.resize(depth, (w, h), interpolation=cv2.INTER_CUBIC)


@dataclass
class ParallaxLayers:
    layers: list[np.ndarray]  # BGR
    masks: list[np.ndarray]  # float32 alpha (HxWx1), layer 0 is opaque background
    strengths: list[float]


def build_layers(image: np.ndarray, estimator: DepthEstimator | None = None) -> ParallaxLayers:
    depth = (estimator or HeuristicDepth()).estimate(image)
    t_mid, t_fg = np.percentile(depth, 55), np.percentile(depth, 82)
    feather = max(3, image.shape[1] // 180)

    def soft(threshold: float) -> np.ndarray:
        m = np.clip((depth - threshold) * 12 + 0.5, 0, 1).astype(np.float32)
        return cv2.GaussianBlur(m, (0, 0), feather)[..., None]  # (H, W, 1) float32

    mid_mask, fg_mask = soft(t_mid), soft(t_fg)
    hole = ((mid_mask[..., 0] > 0.3) * 255).astype(np.uint8)
    hole = cv2.dilate(hole, np.ones((9, 9), np.uint8))
    scale = 0.25
    small = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    small_hole = cv2.resize(hole, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    filled_small = cv2.inpaint(small, small_hole, 5, cv2.INPAINT_TELEA)
    filled = cv2.resize(filled_small, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_CUBIC)
    background = (image * (1 - mid_mask) + cv2.GaussianBlur(filled, (0, 0), 2) * mid_mask).astype(np.uint8)
    return ParallaxLayers([background, image, image], [np.ones_like(mid_mask), mid_mask, fg_mask], [0.55, 1.0, 1.45])


def render_parallax(layers: ParallaxLayers, state: CameraState, out_w: int, out_h: int) -> np.ndarray:
    src_h, src_w = layers.layers[0].shape[:2]
    out = None
    for layer, mask, strength in zip(layers.layers, layers.masks, layers.strengths, strict=True):
        layered = CameraState(
            zoom=1.0 + (state.zoom - 1.0) * strength,
            cx=0.5 + (state.cx - 0.5) * strength,
            cy=0.5 + (state.cy - 0.5) * strength,
            angle=state.angle * strength,
        )
        m = camera_matrix(layered, src_w, src_h, out_w, out_h)
        warped = cv2.warpAffine(layer, m, (out_w, out_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        if out is None:
            out = warped
            continue
        a = cv2.warpAffine(mask, m, (out_w, out_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        a = a[..., 0] if a.ndim == 3 else a
        out = cv2.blendLinear(warped, out, a, 1.0 - a)
    assert out is not None
    return out
