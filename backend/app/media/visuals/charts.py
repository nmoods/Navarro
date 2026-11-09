"""Timeline, statistical infographic and animated comparison visuals."""

from __future__ import annotations

import math

import cv2
import numpy as np

from app.media.color import cover_resize, palette_bgr
from app.media.spec import SceneSpec
from app.media.visuals.common import bgr_to_hex, draw_text, ease, mix, themed_background, wrap


class TimelineVisual:
    def __init__(self, spec: SceneSpec, w: int, h: int) -> None:
        self.spec, self.w, self.h = spec, w, h
        events = spec.visual_data.get("events") or []
        self.events = [(e.get("date", ""), e.get("label", "")) for e in events][:6] or [("", spec.title)]
        self.bg = themed_background(spec, w, h)
        pal = palette_bgr(spec.palette)
        self.accent = pal[1] if sum(pal[1]) > 150 else (250, 139, 167)
        self.spacing = int(w * 0.62)

    def frame(self, t: float) -> np.ndarray:
        img = self.bg.copy()
        n, d, w, h = len(self.events), self.spec.duration, self.w, self.h
        slot = d * 0.85 / n
        active = min(n - 1, int(t / slot))
        local = ease((t - active * slot) / min(0.8, slot * 0.6))
        focus = (active - 1 + local) if active else 0.0  # glide from previous event to the active one
        offset = w / 2 - focus * self.spacing
        y = int(h * 0.5)
        thick = max(2, w // 250)
        x_start = int(offset - self.spacing)
        x_end = int(offset + (n - 1) * self.spacing * min(1.0, (t + slot * 0.5) / (slot * n)) + self.spacing * 0.3)
        cv2.line(img, (x_start, y), (x_end, y), mix(self.accent, (255, 255, 255), 0.3), thick, cv2.LINE_AA)
        for i, (date, label) in enumerate(self.events):
            appear = i * slot
            if t < appear:
                continue
            k = ease((t - appear) / 0.45)
            x = int(offset + i * self.spacing)
            r = int(w * 0.022 * k)
            cv2.circle(img, (x, y), int(r * 1.8), mix(self.accent, (0, 0, 0), 0.5), -1, cv2.LINE_AA)
            cv2.circle(img, (x, y), r, self.accent, -1, cv2.LINE_AA)
            dim = 1.0 if i == active else 0.55
            draw_text(img, date, x, int(y - w * 0.06 - (1 - k) * 40), px=int(w * 0.11), family="Anton", weight=400,
                      color="#FFFFFF", anchor="mb", opacity=k * dim, shadow=True)  # fmt: skip
            for j, line in enumerate(wrap(label, 18)[:3]):
                draw_text(img, line, x, int(y + w * 0.06 + j * w * 0.058 + (1 - k) * 40), px=int(w * 0.045),
                          weight=600, color="#E5E7EB", anchor="mt", opacity=k * dim)  # fmt: skip
        return img


class InfographicVisual:
    def __init__(self, spec: SceneSpec, w: int, h: int) -> None:
        self.spec, self.w, self.h = spec, w, h
        self.stats = [(s.get("label", ""), float(s.get("value", 0)), s.get("unit", "")) for s in spec.visual_data.get("stats") or []][:5]
        self.bg = themed_background(spec, w, h, 0.82)
        pal = palette_bgr(spec.palette)
        self.colors = [c if sum(c) > 150 else (250, 139, 167) for c in (pal[1], pal[2], pal[0])]

    @staticmethod
    def _fmt(v: float, unit: str) -> str:
        if abs(v) >= 1_000_000:
            text = f"{v / 1_000_000:.1f}M"
        elif abs(v) >= 10_000:
            text = f"{v / 1000:.0f}K"
        elif abs(v - round(v)) < 1e-6:
            text = f"{int(round(v)):,}"
        else:
            text = f"{v:.1f}"
        return f"{text}{unit if unit in ('%', '°', 'x') else (' ' + unit if unit else '')}"

    def frame(self, t: float) -> np.ndarray:
        img = self.bg.copy()
        w, h, d = self.w, self.h, self.spec.duration
        if not self.stats:
            draw_text(img, self.spec.title.upper(), w // 2, h // 2, px=int(w * 0.08), family="Anton", anchor="mm")
            return img
        if len(self.stats) == 1:
            label, value, unit = self.stats[0]
            k = ease(t / max(0.5, d * 0.5))
            draw_text(img, self._fmt(value * k, unit), w // 2, int(h * 0.45), px=int(w * 0.2), family="Anton",
                      weight=400, color=bgr_to_hex(self.colors[0]), anchor="mm", shadow=True)  # fmt: skip
            for j, line in enumerate(wrap(label, 22)[:3]):
                draw_text(img, line.upper(), w // 2, int(h * 0.56 + j * w * 0.065), px=int(w * 0.05), weight=800,
                          anchor="mt", opacity=min(1.0, t / 0.6))  # fmt: skip
            return img
        top, gap = int(h * 0.28), int(h * 0.5 / len(self.stats))
        vmax = max(abs(v) for _, v, _ in self.stats) or 1
        bar_max = int(w * 0.72)
        for i, (label, value, unit) in enumerate(self.stats):
            start = i * d * 0.12
            k = ease((t - start) / max(0.4, d * 0.4))
            if t < start:
                continue
            y = top + i * gap
            x0 = int(w * 0.14)
            draw_text(img, label.upper(), x0, y, px=int(w * 0.036), weight=700, color="#D1D5DB", opacity=min(1, k * 2))
            bar_y = y + int(w * 0.055)
            bh = int(w * 0.06)
            length = int(bar_max * abs(value) / vmax * k)
            color = self.colors[i % len(self.colors)]
            cv2.rectangle(img, (x0, bar_y), (x0 + bar_max, bar_y + bh), mix(color, (0, 0, 0), 0.8), -1, cv2.LINE_AA)
            if length > 0:
                cv2.rectangle(img, (x0, bar_y), (x0 + length, bar_y + bh), color, -1, cv2.LINE_AA)
            draw_text(img, self._fmt(value * k, unit), x0 + max(length, 0) + int(w * 0.02), bar_y + bh // 2,
                      px=int(w * 0.045), family="Anton", weight=400, anchor="lm")  # fmt: skip
        return img


class ComparisonVisual:
    def __init__(self, spec: SceneSpec, w: int, h: int, image: np.ndarray | None) -> None:
        self.spec, self.w, self.h = spec, w, h
        data = spec.visual_data
        self.sides = [data.get("left") or {"label": "Then", "points": []}, data.get("right") or {"label": "Now", "points": []}]
        if image is not None:
            bg = cv2.GaussianBlur(cover_resize(image, w, h), (0, 0), w / 60)
            self.bg = cv2.convertScaleAbs(bg, alpha=0.45)
        else:
            self.bg = themed_background(spec, w, h)
        pal = palette_bgr(spec.palette)
        self.colors = [c if sum(c) > 150 else (250, 139, 167) for c in (pal[1], pal[2])]
        self.vertical = h > w

    def frame(self, t: float) -> np.ndarray:
        img = self.bg.copy()
        w, h = self.w, self.h
        for i, side in enumerate(self.sides):
            k = ease((t - i * 0.5) / 0.6)
            if k <= 0:
                continue
            if self.vertical:
                x0, y0, x1, y1 = int(w * 0.07), int(h * (0.12 + i * 0.42)), int(w * 0.93), int(h * (0.48 + i * 0.42))
                shift = int((1 - k) * w * (-1 if i == 0 else 1))
                x0, x1 = x0 + shift, x1 + shift
            else:
                x0, y0, x1, y1 = int(w * (0.05 + i * 0.48)), int(h * 0.15), int(w * (0.47 + i * 0.48)), int(h * 0.85)
                shift = int((1 - k) * h * 0.3)
                y0, y1 = y0 + shift, y1 + shift
            roi = img[max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)]
            if roi.size:
                img[max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)] = cv2.addWeighted(
                    roi, 0.35, np.full_like(roi, mix(self.colors[i], (10, 10, 14), 0.75)), 0.65, 0
                )
            cv2.rectangle(img, (x0, y0), (x1, y1), self.colors[i], max(2, w // 300), cv2.LINE_AA)
            draw_text(img, str(side.get("label", "")).upper(), (x0 + x1) // 2, y0 + int(w * 0.04), px=int(w * 0.07),
                      family="Anton", weight=400, color=bgr_to_hex(self.colors[i]), anchor="mt", opacity=k)  # fmt: skip
            for j, point in enumerate((side.get("points") or [])[:4]):
                pk = ease((t - i * 0.5 - 0.6 - j * 0.35) / 0.4)
                for li, line in enumerate(wrap(f"• {point}", 30)[:2]):
                    draw_text(img, line, x0 + int(w * 0.05), y0 + int(w * 0.16 + j * w * 0.1 + li * w * 0.045),
                              px=int(w * 0.04), weight=600, color="#F3F4F6", opacity=pk)  # fmt: skip
        vk = ease((t - 1.0) / 0.35)
        if vk > 0:
            r = int(w * 0.07 * (0.6 + 0.4 * vk + 0.05 * math.sin(t * 6)))
            cx, cy = w // 2, h // 2
            cv2.circle(img, (cx, cy), r, (20, 20, 24), -1, cv2.LINE_AA)
            cv2.circle(img, (cx, cy), r, (255, 255, 255), max(2, w // 270), cv2.LINE_AA)
            draw_text(img, "VS", cx, cy, px=int(r * 0.95), family="Anton", weight=400, anchor="mm", opacity=vk)
        return img
