"""Visuals that are composed once as a still and then animated by the camera: newspaper front page,
procedural backdrop (used when no AI image is available) and kinetic typography."""

from __future__ import annotations

import math

import cv2
import numpy as np

from app.media.color import cover_resize, gradient_canvas, palette_bgr
from app.media.effects import fractal_noise
from app.media.spec import SceneSpec
from app.media.visuals.common import bgr_to_hex, draw_text, ease, mix, wrap


def newspaper_still(spec: SceneSpec, w: int, h: int, image: np.ndarray | None) -> np.ndarray:
    rng = np.random.default_rng(spec.seed + 11)
    paper = fractal_noise(max(8, w // 4), max(8, h // 4), rng)
    paper = cv2.resize(paper, (w, h))[..., None]
    base = np.array((178, 214, 232), np.float32)  # warm newsprint (BGR)
    img = np.clip(base * (0.86 + 0.18 * paper), 0, 255).astype(np.uint8)
    ink = "#1C1917"
    m = int(w * 0.06)
    data = spec.visual_data
    draw_text(img, "The Chronicle", w // 2, m, px=int(w * 0.1), family="UnifrakturMaguntia", weight=400, color=ink, anchor="mt")
    y = m + int(w * 0.14)
    cv2.line(img, (m, y), (w - m, y), (40, 40, 45), max(2, w // 400))
    dateline = data.get("dateline") or "Special Edition"
    draw_text(img, dateline.upper(), w // 2, y + int(w * 0.012), px=int(w * 0.026), family="Playfair Display",
              weight=600, color=ink, anchor="mt")  # fmt: skip
    y += int(w * 0.05)
    cv2.line(img, (m, y), (w - m, y), (40, 40, 45), max(1, w // 700))
    headline = data.get("headline") or spec.title
    y += int(w * 0.03)
    for line in wrap(headline.upper(), 18)[:3]:
        _, lh = draw_text(img, line, w // 2, y, px=int(w * 0.085), family="Playfair Display", weight=900, color=ink, anchor="mt")
        y += int(lh * 0.98)
    y += int(w * 0.03)
    photo_h = int(h * 0.36)
    if image is not None:
        photo = cv2.cvtColor(cover_resize(image, w - 2 * m, photo_h), cv2.COLOR_BGR2GRAY)
        photo = cv2.equalizeHist(photo)
        dots = (np.indices(photo.shape).sum(axis=0) % 3 == 0).astype(np.float32) * 18
        photo = np.clip(photo.astype(np.float32) * 0.85 + dots - 6, 0, 255).astype(np.uint8)
        sepia = cv2.merge([(photo * 0.75).astype(np.uint8), (photo * 0.88).astype(np.uint8), photo])
        img[y : y + photo_h, m : w - m] = cv2.addWeighted(img[y : y + photo_h, m : w - m], 0.25, sepia, 0.75, 0)
        cv2.rectangle(img, (m, y), (w - m, y + photo_h), (40, 40, 45), max(1, w // 600))
        y += photo_h + int(w * 0.03)
    col_w = (w - 2 * m - int(w * 0.04)) // 2
    line_h = int(w * 0.022)
    for c in range(2):
        x0 = m + c * (col_w + int(w * 0.04))
        yy = y
        while yy < h - m:
            length = int(col_w * rng.uniform(0.7, 1.0)) if rng.random() > 0.12 else int(col_w * 0.4)
            cv2.line(img, (x0, yy), (x0 + length, yy), (95, 105, 115), max(1, line_h // 3))
            yy += line_h
    vig = cv2.GaussianBlur(np.ones((h, w), np.float32), (0, 0), 1)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    vig = 1 - 0.35 * (((xs / w - 0.5) ** 2 + (ys / h - 0.5) ** 2) * 2.2)
    return np.clip(img * vig[..., None], 0, 255).astype(np.uint8)


def procedural_backdrop(spec: SceneSpec, w: int, h: int) -> tuple[np.ndarray, list[np.ndarray]]:
    """Layered landscape from the scene palette. Returns (composite, [sky, far, near] layer alphas)."""
    rng = np.random.default_rng(spec.seed + 3)
    pal = palette_bgr(spec.palette)
    sky_top, sky_bottom = mix(pal[0], (6, 6, 10), 0.55), mix(pal[1], pal[0], 0.45)
    img = gradient_canvas(w, h, sky_top, sky_bottom).astype(np.float32)
    clouds = cv2.resize(fractal_noise(max(8, w // 5), max(8, h // 5), rng), (w, h))
    img += (clouds[..., None] - 0.5) * 40
    sun_x, sun_y = int(w * rng.uniform(0.25, 0.75)), int(h * rng.uniform(0.25, 0.42))
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    glow = np.exp(-((xs - sun_x) ** 2 + (ys - sun_y) ** 2) / (2 * (w * 0.18) ** 2))
    img += glow[..., None] * np.array(mix(pal[2], (255, 255, 255), 0.4), np.float32) * 0.7
    stars = rng.random((h, w)) > 0.9993
    img[stars] = 230
    masks = []
    for depth, (base, amp, color_t) in enumerate(((0.58, 0.08, 0.55), (0.7, 0.1, 0.75), (0.84, 0.07, 0.92))):
        ridge = np.cumsum(rng.normal(0, 1, w // 8 + 2))
        ridge = cv2.resize(((ridge - ridge.mean()) / (ridge.std() + 1e-6)).reshape(1, -1).astype(np.float32), (w, 1))[0]
        line = (base + amp * ridge / 3) * h
        mask = (ys > line[None, :]).astype(np.float32)
        mask = cv2.GaussianBlur(mask, (0, 0), 1.2)
        color = np.array(mix(pal[0], (4, 4, 6), color_t), np.float32)
        haze = (1 - depth / 3) * 0.25
        layer_col = color * (1 - haze) + np.array(sky_bottom, np.float32) * haze
        img = img * (1 - mask[..., None]) + layer_col * mask[..., None]
        masks.append(mask)
    return np.clip(img, 0, 255).astype(np.uint8), masks


class KineticTypography:
    def __init__(self, spec: SceneSpec, w: int, h: int) -> None:
        self.spec, self.w, self.h = spec, w, h
        lines = spec.visual_data.get("kinetic_lines") or []
        if not lines:
            words = " ".join(c.text for c in spec.captions).split() or spec.title.split()
            per = max(1, math.ceil(len(words) / 4))
            lines = [" ".join(words[i : i + per]) for i in range(0, len(words), per)][:4]
        self.lines = [ln.upper() for ln in lines][:4]
        pal = palette_bgr(spec.palette)
        self.bg = gradient_canvas(w, h, mix(pal[0], (5, 5, 8), 0.6), mix(pal[1], (5, 5, 8), 0.7))
        self.accent = bgr_to_hex(pal[1] if sum(pal[1]) > 150 else (250, 139, 167))
        self.emph = {c.text.strip(".,!?").upper() for c in spec.captions if c.emphasis}

    def frame(self, t: float) -> np.ndarray:
        img = self.bg.copy()
        w, h = self.w, self.h
        streak_x = int((t * 0.35 % 1.6 - 0.3) * w)
        cv2.line(img, (streak_x, 0), (streak_x - int(w * 0.4), h), (255, 255, 255), max(2, w // 60), cv2.LINE_AA)
        img = cv2.addWeighted(self.bg, 0.92, img, 0.08, 0)
        n = len(self.lines)
        slot = self.spec.duration * 0.8 / max(1, n)
        total_h = n * w * 0.14
        y0 = int(h / 2 - total_h / 2)
        for i, line in enumerate(self.lines):
            k = ease((t - i * slot) / 0.4)
            if k <= 0:
                continue
            emph = any(word.strip(".,!?") in self.emph for word in line.split())
            px = int(w * (0.115 if emph else 0.095) * (len(line) <= 12 and 1.25 or 1.0))
            px = min(px, int(w * 1.6 / max(4, len(line))))
            y = int(y0 + i * w * 0.14 + (1 - k) * w * 0.08)
            draw_text(img, line, w // 2, y, px=px, family="Anton", weight=400, color=self.accent if emph else "#FFFFFF",
                      anchor="mt", opacity=k, shadow=True)  # fmt: skip
        return img
