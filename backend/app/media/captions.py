"""Animated, audio-synchronised captions.

Words carry real timestamps (from faster-whisper alignment). Words are grouped into chunks that respect
punctuation, laid out once per chunk, rendered to RGBA sprites once per (word, state), and composited per
frame with pop/bounce/karaoke/typewriter animation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw

from app.media.color import hex_to_rgba
from app.media.fonts import load_font
from app.media.spec import CaptionStyle, CaptionWord

_BREAK_AFTER = (".", "!", "?", ";", ":", ",", "—")


@dataclass(frozen=True)
class Chunk:
    words: tuple[CaptionWord, ...]
    start: float
    end: float


def chunk_words(words: tuple[CaptionWord, ...], max_words: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: list[CaptionWord] = []
    for word in words:
        current.append(word)
        hard = word.text.endswith((".", "!", "?"))
        soft = word.text.endswith(_BREAK_AFTER) and len(current) >= max(2, max_words // 2)
        if len(current) >= max_words or hard or soft:
            chunks.append(Chunk(tuple(current), current[0].start, current[-1].end))
            current = []
    if current:
        chunks.append(Chunk(tuple(current), current[0].start, current[-1].end))
    # hold each chunk on screen until the next one starts (no flicker between words)
    held = []
    for i, c in enumerate(chunks):
        nxt = chunks[i + 1].start if i + 1 < len(chunks) else c.end + 0.5
        held.append(Chunk(c.words, c.start, min(max(c.end, nxt), c.end + 0.6)))
    return held


@lru_cache(maxsize=2048)
def _sprite(text: str, family: str, weight: int, px: int, fill: str, stroke: str, stroke_px: int, shadow: bool) -> np.ndarray:
    font = load_font(family, px, weight)
    pad = stroke_px + (px // 6 if shadow else 0) + 2
    left, top, right, bottom = font.getbbox(text, stroke_width=stroke_px)
    w, h = right - left + pad * 2, bottom - top + pad * 2
    img = Image.new("RGBA", (max(1, w), max(1, h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    origin = (pad - left, pad - top)
    if shadow:
        off = max(2, px // 14)
        draw.text((origin[0] + off, origin[1] + off), text, font=font, fill=(0, 0, 0, 150))
        img = Image.fromarray(cv2.GaussianBlur(np.array(img), (0, 0), max(1, px / 18)))
        draw = ImageDraw.Draw(img)
    draw.text(origin, text, font=font, fill=hex_to_rgba(fill), stroke_width=stroke_px, stroke_fill=hex_to_rgba(stroke))
    rgba = np.array(img)
    return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)


def alpha_composite(frame: np.ndarray, sprite: np.ndarray, x: int, y: int, opacity: float = 1.0) -> None:
    """In-place blend of a BGRA sprite onto a BGR frame at (x, y), clipped to the frame."""
    h, w = sprite.shape[:2]
    fh, fw = frame.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(fw, x + w), min(fh, y + h)
    if x0 >= x1 or y0 >= y1 or opacity <= 0:
        return
    s = sprite[y0 - y : y1 - y, x0 - x : x1 - x]
    a = (s[..., 3:4].astype(np.float32) / 255.0) * opacity
    region = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (s[..., :3].astype(np.float32) * a + region * (1 - a)).astype(np.uint8)


def _scale_sprite(sprite: np.ndarray, scale: float) -> np.ndarray:
    if abs(scale - 1.0) < 0.01:
        return sprite
    h, w = sprite.shape[:2]
    return cv2.resize(sprite, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_LINEAR)


def _pop(t: float, start: float, dur: float = 0.16) -> float:
    if t < start:
        return 0.0
    p = (t - start) / dur
    if p >= 1:
        return 1.0
    return 0.7 + 0.42 * math.sin(p * math.pi * 0.85)  # overshoot then settle


class CaptionRenderer:
    def __init__(self, words: tuple[CaptionWord, ...], style: CaptionStyle, width: int, height: int) -> None:
        self.style, self.w, self.h = style, width, height
        self.px = max(14, int(style.size * width))
        self.stroke_px = max(1, int(self.px * style.stroke_width)) if style.background != "box" else 0
        max_words = 1 if style.animation == "word_pop" and style.max_words <= 1 else style.max_words
        self.chunks = chunk_words(words, max(1, max_words)) if style.enabled else []
        self.space = int(self.px * 0.28)
        self.line_gap = int(self.px * 0.18)

    def _text(self, word: CaptionWord) -> str:
        text = word.text.strip()
        return text.upper() if self.style.uppercase else text

    def _sprite_for(self, word: CaptionWord, active: bool) -> np.ndarray:
        s = self.style
        color = s.emphasis_color if word.emphasis else (s.highlight_color if active else s.color)
        if s.animation in ("sentence", "typewriter") and not word.emphasis:
            color = s.color
        px = int(self.px * (1.12 if word.emphasis else 1.0))
        return _sprite(self._text(word), s.font, s.font_weight, px, color, s.stroke_color, self.stroke_px,
                       s.background == "shadow")  # fmt: skip

    def _layout(self, chunk: Chunk) -> list[tuple[CaptionWord, int, int]]:
        max_line = int(self.w * 0.84)
        lines: list[list[tuple[CaptionWord, int]]] = [[]]
        widths = [0]
        for word in chunk.words:
            sw = self._sprite_for(word, False).shape[1]
            add = sw + (self.space if lines[-1] else 0)
            if lines[-1] and widths[-1] + add > max_line:
                lines.append([])
                widths.append(0)
                add = sw
            lines[-1].append((word, sw))
            widths[-1] += add
        line_h = int(self.px * 1.25)
        total_h = len(lines) * line_h + (len(lines) - 1) * self.line_gap
        anchor = {"top": 0.2, "middle": 0.5, "bottom": 0.74}.get(self.style.position, 0.74)
        top = int(self.h * (anchor + self.style.vertical_offset) - total_h / 2)
        placed = []
        for i, line in enumerate(lines):
            x = (self.w - widths[i]) // 2
            y = top + i * (line_h + self.line_gap)
            for word, sw in line:
                placed.append((word, x, y))
                x += sw + self.space
        return placed

    def render(self, frame: np.ndarray, t: float) -> np.ndarray:
        chunk = next((c for c in self.chunks if c.start - 0.05 <= t < c.end), None)
        if chunk is None:
            return frame
        placed = self._layout(chunk)
        anim = self.style.animation
        if self.style.background == "box":
            self._box(frame, placed)
        chunk_in = min(1.0, (t - chunk.start + 0.05) / 0.12)
        for word, x, y in placed:
            spoken = t >= word.start
            active = word.start <= t < word.end + 0.05
            if anim == "typewriter" and not spoken:
                continue
            sprite = self._sprite_for(word, active and anim in ("karaoke", "word_pop", "bounce"))
            scale, dy, opacity = 1.0, 0, chunk_in
            if anim == "word_pop":
                k = _pop(t, word.start)
                if k == 0:
                    continue
                scale = k
            elif anim == "bounce":
                if spoken:
                    p = min(1.0, (t - word.start) / 0.22)
                    dy = int(-self.px * 0.22 * math.sin(p * math.pi))
                else:
                    opacity *= 0.55
            elif anim == "karaoke":
                scale = 1.06 if active else 1.0
            sp = _scale_sprite(sprite, scale)
            ox = x - (sp.shape[1] - sprite.shape[1]) // 2
            oy = y + dy - (sp.shape[0] - sprite.shape[0]) // 2
            alpha_composite(frame, sp, ox, oy, opacity)
        return frame

    def _box(self, frame: np.ndarray, placed: list[tuple[CaptionWord, int, int]]) -> None:
        if not placed:
            return
        r, g, b, a = hex_to_rgba(self.style.background_color)
        pad = int(self.px * 0.35)
        xs = [x for _, x, _ in placed]
        ys = [y for _, _, y in placed]
        x_end = max(x + self._sprite_for(w, False).shape[1] for w, x, _ in placed)
        x0, y0 = max(0, min(xs) - pad), max(0, min(ys) - pad // 2)
        x1, y1 = min(self.w, x_end + pad), min(self.h, max(ys) + int(self.px * 1.3) + pad // 2)
        roi = frame[y0:y1, x0:x1]
        box = np.zeros_like(roi)
        box[:] = (b, g, r)
        frame[y0:y1, x0:x1] = cv2.addWeighted(roi, 1 - a / 255, box, a / 255, 0)
