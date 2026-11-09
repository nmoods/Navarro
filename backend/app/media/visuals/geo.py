"""Offline geography from Natural Earth 1:110m (public domain): country shapes and a small geocoder."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

GEO_DIR = Path(__file__).resolve().parents[1] / "assets" / "geo"


@dataclass(frozen=True)
class Country:
    name: str
    polygons: tuple[np.ndarray, ...]  # each (n, 2) lon/lat
    label: tuple[float, float]  # lon, lat


def _norm(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return "".join(ch for ch in text if ch.isalnum() or ch == " ").strip()


@lru_cache
def countries() -> tuple[Country, ...]:
    data = json.loads((GEO_DIR / "ne_110m_admin_0_countries.geojson").read_text(encoding="utf-8"))
    out = []
    for feat in data["features"]:
        props, geom = feat["properties"], feat["geometry"]
        rings = geom["coordinates"] if geom["type"] == "Polygon" else [p[0] for p in geom["coordinates"]]
        if geom["type"] == "Polygon":
            rings = [rings[0]]
        polys = tuple(np.asarray(r, np.float32) for r in rings)
        label = (float(props.get("LABEL_X") or polys[0][:, 0].mean()), float(props.get("LABEL_Y") or polys[0][:, 1].mean()))
        out.append(Country(props.get("ADMIN") or props.get("NAME"), polys, label))
    return tuple(out)


@lru_cache
def _gazetteer() -> dict[str, tuple[float, float]]:
    table: dict[str, tuple[float, float]] = {}
    for c in countries():
        table[_norm(c.name)] = c.label
    data = json.loads((GEO_DIR / "ne_110m_populated_places_simple.geojson").read_text(encoding="utf-8"))
    for feat in data["features"]:
        p = feat["properties"]
        lon, lat = feat["geometry"]["coordinates"][:2]
        for key in ("name", "nameascii", "namealt"):
            if p.get(key):
                table.setdefault(_norm(str(p[key])), (float(lon), float(lat)))
    extras = {  # common historical/regional names not in the 110m gazetteer
        "roanoke island": (-75.70, 35.89), "roanoke": (-75.70, 35.89), "england": (-1.5, 52.6),
        "virginia": (-78.6, 37.5), "north carolina": (-79.4, 35.6), "atlantic ocean": (-40.0, 30.0),
        "pacific ocean": (-150.0, 0.0), "mediterranean": (18.0, 35.0), "mediterranean sea": (18.0, 35.0),
        "scotland": (-4.2, 56.8), "wales": (-3.7, 52.3), "siberia": (100.0, 62.0), "atlantis": (-25.0, 35.0),
        "rome": (12.5, 41.9), "athens": (23.7, 38.0), "constantinople": (28.97, 41.01), "babylon": (44.42, 32.54),
        "pompeii": (14.49, 40.75), "giza": (31.13, 29.98), "troy": (26.24, 39.96), "jerusalem": (35.21, 31.77),
        "bermuda triangle": (-71.0, 25.0), "easter island": (-109.35, -27.11), "machu picchu": (-72.55, -13.16),
    }
    for k, v in extras.items():
        table.setdefault(k, v)
    return table


def geocode(name: str) -> tuple[float, float] | None:
    """Return (lon, lat) for a place name, or None if unknown. Offline, deterministic."""
    key = _norm(name)
    table = _gazetteer()
    if key in table:
        return table[key]
    for part in [p.strip() for p in key.replace(",", " ,").split(",")]:
        if part in table:
            return table[part]
    candidates = [k for k in table if len(k) > 3 and (k in key or key in k)]
    return table[min(candidates, key=len)] if candidates else None
