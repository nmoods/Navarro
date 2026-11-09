"""Bundled open-licensed fonts (SIL OFL 1.1 / Apache-2.0), resolved by family name."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

FONT_DIR = Path(__file__).parent / "assets" / "fonts"

_FAMILIES: dict[str, str] = {
    "Montserrat": "Montserrat[wght].ttf",
    "Inter": "Inter[opsz,wght].ttf",
    "Anton": "Anton-Regular.ttf",
    "Bebas Neue": "BebasNeue-Regular.ttf",
    "Archivo Black": "ArchivoBlack-Regular.ttf",
    "Playfair Display": "PlayfairDisplay[wght].ttf",
    "Oswald": "Oswald[wght].ttf",
    "Special Elite": "SpecialElite-Regular.ttf",
    "UnifrakturMaguntia": "UnifrakturMaguntia-Book.ttf",
}

AVAILABLE_FONTS = tuple(_FAMILIES)


@lru_cache(maxsize=256)
def load_font(family: str, size: int, weight: int = 700) -> ImageFont.FreeTypeFont:
    filename = _FAMILIES.get(family, _FAMILIES["Montserrat"])
    font = ImageFont.truetype(str(FONT_DIR / filename), max(6, size))
    try:
        axes = font.get_variation_axes()
    except OSError:
        return font  # static font
    values = []
    for axis in axes:
        name = axis.get("name", b"")
        name = name.decode() if isinstance(name, bytes) else str(name)
        lo, hi = axis["minimum"], axis["maximum"]
        if name.lower().startswith("weight"):
            values.append(max(lo, min(hi, weight)))
        elif name.lower().startswith("optical"):
            values.append(max(lo, min(hi, size / 2)))
        else:
            values.append(axis.get("default", lo))
    font.set_variation_by_axes(values)
    return font
