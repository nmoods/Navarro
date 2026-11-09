"""Animated historical/geographic map: vector-rendered every frame so zooms stay crisp."""

from __future__ import annotations

import math

import cv2
import numpy as np

from app.media.color import palette_bgr
from app.media.spec import SceneSpec
from app.media.visuals.common import bgr_to_hex, draw_text, ease, mix
from app.media.visuals.geo import countries, geocode


class MapVisual:
    def __init__(self, spec: SceneSpec, w: int, h: int) -> None:
        self.spec, self.w, self.h = spec, w, h
        pal = palette_bgr(spec.palette)
        self.ocean = mix(pal[0], (18, 12, 8), 0.7)
        self.land = mix(pal[0], (70, 72, 78), 0.6)
        self.accent = pal[1] if sum(pal[1]) > 150 else (250, 139, 167)
        self.border = mix(self.land, (210, 210, 220), 0.35)
        self.places: list[tuple[str, float, float]] = []
        for place in spec.visual_data.get("places", []) or []:
            lon, lat = place.get("longitude"), place.get("latitude")
            if lon is None or lat is None:
                found = geocode(place.get("name", ""))
                if not found:
                    continue
                lon, lat = found
            self.places.append((place.get("name", ""), float(lon), float(lat)))
        self.route = bool(spec.visual_data.get("draw_route")) and len(self.places) > 1
        self.target = self._target_view()
        self.start = self._expand(self.target, 3.2)
        self.highlight = self._highlight_countries()

    def _target_view(self) -> tuple[float, float, float]:
        """(centre lon, centre lat, latitude span)."""
        if not self.places:
            return 10.0, 25.0, 140.0
        lons = [p[1] for p in self.places]
        lats = [p[2] for p in self.places]
        cx, cy = (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2
        aspect = self.w / self.h
        span_lat = max(max(lats) - min(lats), (max(lons) - min(lons)) / aspect * math.cos(math.radians(cy)), 9.0)
        return cx, cy, span_lat * 1.7

    @staticmethod
    def _expand(view: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
        cx, cy, span = view
        return cx, cy * 0.6, min(170.0, span * factor)

    def _highlight_countries(self) -> set[int]:
        out: set[int] = set()
        for _, lon, lat in self.places:
            for i, c in enumerate(countries()):
                if any(cv2.pointPolygonTest(p.reshape(-1, 1, 2), (lon, lat), False) >= 0 for p in c.polygons):
                    out.add(i)
        return out

    def _project(self, pts: np.ndarray, view: tuple[float, float, float]) -> np.ndarray:
        cx, cy, span_lat = view
        ppd = self.h / span_lat  # pixels per degree latitude
        kx = math.cos(math.radians(max(-70, min(70, cy))))
        x = (pts[..., 0] - cx) * ppd * kx + self.w / 2
        y = (cy - pts[..., 1]) * ppd + self.h / 2
        return np.stack([x, y], axis=-1)

    def frame(self, t: float) -> np.ndarray:
        d = self.spec.duration
        p = ease(min(1.0, t / max(0.1, d * 0.55)))
        s0, s1 = self.start, self.target
        view = (
            s0[0] + (s1[0] - s0[0]) * p,
            s0[1] + (s1[1] - s0[1]) * p,
            math.exp(math.log(s0[2]) + (math.log(s1[2]) - math.log(s0[2])) * p),
        )
        img = np.empty((self.h, self.w, 3), np.uint8)
        img[:] = self.ocean
        self._graticule(img, view)
        for i, c in enumerate(countries()):
            polys = [np.round(self._project(poly, view)).astype(np.int32) for poly in c.polygons]
            color = mix(self.land, self.accent, 0.35 + 0.1 * math.sin(t * 2)) if i in self.highlight else self.land
            cv2.fillPoly(img, polys, color, lineType=cv2.LINE_AA)
            cv2.polylines(img, polys, True, self.border, max(1, self.w // 900), cv2.LINE_AA)
        glow = cv2.GaussianBlur(img, (0, 0), self.w / 120)
        img = cv2.addWeighted(img, 0.85, glow, 0.25, 0)
        self._route_and_pins(img, view, t)
        return img

    def _graticule(self, img: np.ndarray, view: tuple[float, float, float]) -> None:
        col = mix(self.ocean, (200, 200, 220), 0.08)
        for lon in range(-180, 181, 10):
            line = self._project(np.array([[lon, la] for la in range(-80, 81, 5)], np.float32), view)
            cv2.polylines(img, [np.round(line).astype(np.int32)], False, col, 1, cv2.LINE_AA)
        for lat in range(-80, 81, 10):
            line = self._project(np.array([[lo, lat] for lo in range(-180, 181, 5)], np.float32), view)
            cv2.polylines(img, [np.round(line).astype(np.int32)], False, col, 1, cv2.LINE_AA)

    def _route_and_pins(self, img: np.ndarray, view: tuple[float, float, float], t: float) -> None:
        d = self.spec.duration
        n = len(self.places)
        thick = max(2, self.w // 300)
        if self.route:
            pts = self._project(np.array([[p[1], p[2]] for p in self.places], np.float32), view)
            prog = ease((t - d * 0.35) / max(0.1, d * 0.45)) * (n - 1)
            for i in range(n - 1):
                seg = min(1.0, max(0.0, prog - i))
                if seg <= 0:
                    break
                a, b = pts[i], pts[i + 1]
                mid = (a + b) / 2 + np.array([0, -np.linalg.norm(b - a) * 0.25])
                curve = [(1 - u) ** 2 * a + 2 * (1 - u) * u * mid + u**2 * b for u in np.linspace(0, seg, 40)]
                curve_i = np.round(np.array(curve)).astype(np.int32)
                for j in range(0, len(curve_i) - 1, 2):
                    cv2.line(img, tuple(curve_i[j]), tuple(curve_i[j + 1]), self.accent, thick, cv2.LINE_AA)
        for i, (name, lon, lat) in enumerate(self.places):
            appear = d * 0.25 + i * min(0.8, d * 0.5 / max(1, n))
            if t < appear:
                continue
            x, y = self._project(np.array([lon, lat], np.float32), view)
            k = ease((t - appear) / 0.35)
            pulse = (t - appear) % 1.4 / 1.4
            r = int(self.w * 0.012 * k)
            cv2.circle(img, (int(x), int(y)), int(r * (1 + 3 * pulse)), self.accent, max(1, thick // 2), cv2.LINE_AA)
            cv2.circle(img, (int(x), int(y)), r, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(img, (int(x), int(y)), max(1, int(r * 0.55)), self.accent, -1, cv2.LINE_AA)
            draw_text(img, name.upper(), int(x), int(y - r * 2.2), px=int(self.w * 0.034), weight=800,
                      color="#FFFFFF", stroke=bgr_to_hex((10, 10, 10)), stroke_px=max(2, self.w // 300),
                      anchor="mb", opacity=k)  # fmt: skip
