"""Atmospheric effects composited per frame: fog, smoke, particles, weather, light and film texture.

Every effect is deterministic for a given seed so re-renders of an unchanged scene are identical.
Expensive textures are computed once per scene at reduced resolution and scrolled/resized per frame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from app.media.color import vignette_mask


def fractal_noise(width: int, height: int, rng: np.random.Generator, octaves: int = 5) -> np.ndarray:
    """Tileable-ish value noise in [0, 1] (float32), built by summing upscaled random grids."""
    acc = np.zeros((height, width), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells = 3 * 2**o
        grid = rng.random((cells + 1, max(2, int(cells * width / height)) + 1)).astype(np.float32)
        acc += amp * cv2.resize(grid, (width, height), interpolation=cv2.INTER_CUBIC)
        total += amp
        amp *= 0.5
    acc /= total
    acc -= acc.min()
    return acc / max(1e-6, acc.max())


def screen_blend(frame: np.ndarray, layer: np.ndarray) -> np.ndarray:
    inv = cv2.multiply(255 - frame, 255 - layer, scale=1 / 255)
    return 255 - inv


@dataclass
class _Particles:
    pos: np.ndarray  # (n, 2) normalised
    vel: np.ndarray  # (n, 2) normalised per second
    size: np.ndarray
    phase: np.ndarray
    color: tuple[int, int, int]


class EffectStack:
    def __init__(self, effects: tuple[str, ...], width: int, height: int, fps: int, seed: int, style: str) -> None:
        self.w, self.h, self.fps = width, height, fps
        self.effects = set(effects)
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.lw, self.lh = max(2, width // 3), max(2, height // 3)  # low-res layer size
        grain_strength = 18 if style in ("vintage_documentary", "archival_newspaper") else 9
        if "film_grain" in self.effects:
            grain_strength += 6
        self.grain_strength = grain_strength
        self._grain = [self._grain_tile(grain_strength) for _ in range(3)]
        self.vignette = vignette_mask(width, height, 0.5 if style == "dark_mystery" else 0.38)
        if self.effects & {"fog", "smoke"}:
            self.fog_tex = (fractal_noise(self.lw * 2, self.lh * 2, self.rng) * 255).astype(np.uint8)
        if "light_rays" in self.effects:
            self.rays = self._make_rays()
        self.particles: dict[str, _Particles] = {}
        n = lambda k: max(10, int(k * (width * height) / (1080 * 1920)))  # noqa: E731
        if "dust" in self.effects:
            self.particles["dust"] = self._spawn(n(140), (0.004, -0.006), 0.012, (1.2, 3.2), (215, 225, 235))
        if "embers" in self.effects:
            self.particles["embers"] = self._spawn(n(90), (0.0, -0.09), 0.03, (1.5, 4.0), (40, 140, 255))
        if "snow" in self.effects:
            self.particles["snow"] = self._spawn(n(220), (0.01, 0.07), 0.015, (1.5, 4.5), (250, 250, 250))
        if "bokeh" in self.effects:
            self.particles["bokeh"] = self._spawn(n(26), (0.004, -0.008), 0.006, (18, 46), (200, 190, 255))
        if "rain" in self.effects:
            self.rain = self._spawn(n(380), (0.08, 1.6), 0.15, (0.03, 0.07), (210, 210, 220))
        self.lightning_times = sorted(self.rng.uniform(0.6, 30, 4)) if "lightning" in self.effects else []

    def _grain_tile(self, strength: int) -> tuple[np.ndarray, np.ndarray]:
        g = self.rng.normal(0, 1, (self.h // 2, self.w // 2)).astype(np.float32) * strength
        g = cv2.resize(g, (self.w, self.h), interpolation=cv2.INTER_NEAREST)
        pos = cv2.merge([np.clip(g, 0, 255).astype(np.uint8)] * 3)
        neg = cv2.merge([np.clip(-g, 0, 255).astype(np.uint8)] * 3)
        return pos, neg

    def _spawn(self, count: int, vel: tuple[float, float], jitter: float, size: tuple[float, float], color) -> _Particles:
        pos = self.rng.random((count, 2)).astype(np.float32)
        v = np.array(vel, np.float32) + self.rng.normal(0, jitter, (count, 2)).astype(np.float32)
        return _Particles(pos, v, self.rng.uniform(*size, count).astype(np.float32), self.rng.random(count) * 6.28, color)

    def _make_rays(self) -> np.ndarray:
        ys, xs = np.mgrid[0 : self.lh, 0 : self.lw].astype(np.float32)
        ox, oy = self.lw * 0.15, -self.lh * 0.1
        ang = np.arctan2(ys - oy, xs - ox)
        dist = np.hypot(xs - ox, ys - oy) / max(self.lw, self.lh)
        beams = (0.5 + 0.5 * np.sin(ang * 23 + 1.3)) * (0.5 + 0.5 * np.sin(ang * 9 + 0.4))
        return np.clip(beams**3 * np.exp(-dist * 1.6), 0, 1).astype(np.float32)

    def apply(self, frame: np.ndarray, t: float, frame_index: int) -> np.ndarray:
        e = self.effects
        if e & {"fog", "smoke"}:
            frame = self._fog(frame, t, smoke="smoke" in e)
        if "light_rays" in e:
            pulse = 0.75 + 0.25 * math.sin(t * 0.9)
            layer = cv2.resize((self.rays * 120 * pulse).astype(np.uint8), (self.w, self.h))
            frame = screen_blend(frame, cv2.merge([layer // 2 + layer // 3, layer, layer]))
        if self.particles or "rain" in e:
            frame = self._particles(frame, t)
        if "flicker" in e:
            k = 0.9 + 0.1 * math.sin(t * 13.0 + math.sin(t * 7.3) * 2) * math.sin(t * 3.1)
            frame = cv2.convertScaleAbs(frame, alpha=k)
        if "lightning" in e:
            for lt in self.lightning_times:
                dt = t - lt
                if 0 <= dt < 0.35:
                    flash = (1 - dt / 0.35) * (1.0 if (dt < 0.06 or 0.12 < dt < 0.18) else 0.4)
                    frame = cv2.addWeighted(frame, 1.0, np.full_like(frame, (255, 230, 220)), 0.55 * flash, 0)
        frame = cv2.multiply(frame, self.vignette, scale=1 / 255)
        if "vignette_pulse" in e:
            beat = max(0.0, math.sin(t * 2 * math.pi * 1.1)) ** 8
            frame = cv2.convertScaleAbs(frame, alpha=0.82 + 0.18 * beat)
        pos, neg = self._grain[frame_index % len(self._grain)]
        return cv2.subtract(cv2.add(frame, pos), neg)

    def _fog(self, frame: np.ndarray, t: float, smoke: bool) -> np.ndarray:
        speed = (0.012, -0.02) if smoke else (0.008, 0.0)
        ox = int((t * speed[0] * self.lw * 2) % self.lw)
        oy = int((t * -speed[1] * self.lh * 2) % self.lh)
        patch = self.fog_tex[oy : oy + self.lh, ox : ox + self.lw]
        density = 0.55 if smoke else 0.45
        ys = np.linspace(0.25, 1.0, self.lh, dtype=np.float32)[:, None]  # denser near the ground
        layer = np.clip(patch.astype(np.float32) * density * ys, 0, 255).astype(np.uint8)
        layer = cv2.resize(layer, (self.w, self.h), interpolation=cv2.INTER_LINEAR)
        tint = (150, 150, 150) if smoke else (235, 228, 220)
        colored = cv2.merge([cv2.multiply(layer, np.full_like(layer, c), scale=1 / 255) for c in tint])
        return screen_blend(frame, colored)

    def _particles(self, frame: np.ndarray, t: float) -> np.ndarray:
        overlay = np.zeros((self.h, self.w, 3), np.uint8)
        for name, p in self.particles.items():
            pos = (p.pos + p.vel * t) % 1.0
            sway = np.sin(p.phase + t * 1.3) * (0.01 if name in ("snow", "embers") else 0.004)
            xs = ((pos[:, 0] + sway) % 1.0) * self.w
            ys = pos[:, 1] * self.h
            twinkle = 0.55 + 0.45 * np.sin(p.phase * 3 + t * (4.0 if name == "embers" else 1.5))
            for x, y, s, a in zip(xs, ys, p.size, twinkle, strict=True):
                c = tuple(int(ch * a) for ch in p.color)
                cv2.circle(overlay, (int(x), int(y)), max(1, int(s)), c, -1, lineType=cv2.LINE_AA)
            if name in ("bokeh", "embers"):
                overlay = cv2.GaussianBlur(overlay, (0, 0), 3 if name == "embers" else 6)
        if "rain" in self.effects:
            r = self.rain
            pos = (r.pos + r.vel * t) % 1.0
            for (x, y), length in zip(pos, r.size, strict=True):
                x0, y0 = int(x * self.w), int(y * self.h)
                cv2.line(overlay, (x0, y0), (x0 + int(length * 0.05 * self.w), y0 + int(length * self.h)),
                         (120, 120, 130), 1, cv2.LINE_AA)  # fmt: skip
            frame = cv2.convertScaleAbs(frame, alpha=0.86)
        return cv2.add(frame, overlay)
