"""Render specification: the engine's only input. It knows nothing about the database or AI providers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

ENGINE_VERSION = "1.1.0"  # bump whenever rendering output changes, to invalidate cached clips


@dataclass(frozen=True)
class CaptionWord:
    text: str
    start: float
    end: float
    emphasis: bool = False


@dataclass(frozen=True)
class CaptionStyle:
    animation: str = "karaoke"
    font: str = "Montserrat"
    font_weight: int = 800
    size: float = 0.062  # fraction of output width
    color: str = "#FFFFFF"
    highlight_color: str = "#A78BFA"
    emphasis_color: str = "#FACC15"
    stroke_color: str = "#000000"
    stroke_width: float = 0.09  # fraction of font size
    background: str = "none"  # none | box | shadow
    background_color: str = "#000000B3"
    position: str = "bottom"
    vertical_offset: float = 0.0
    uppercase: bool = True
    max_words: int = 4
    enabled: bool = True


@dataclass(frozen=True)
class SceneSpec:
    index: int
    visual_type: str
    duration: float
    narration_offset: float
    camera: str
    effects: tuple[str, ...]
    image_path: Path | None
    visual_data: dict
    palette: tuple[str, ...]
    title: str
    style: str
    captions: tuple[CaptionWord, ...]
    caption_style: CaptionStyle
    characters: tuple[str, ...] = ()
    seed: int = 0
    brand_text: str = ""

    def cache_key(self, render: RenderSettings, image_hash: str | None) -> str:
        data = asdict(self)
        data.pop("index")
        data["image_path"] = image_hash
        data["render"] = asdict(render)
        data["engine"] = ENGINE_VERSION
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class RenderSettings:
    width: int
    height: int
    fps: int = 30
    quality: str = "final"  # final | draft

    @property
    def crf(self) -> int:
        return 19 if self.quality == "final" else 25

    @property
    def preset(self) -> str:
        return "medium" if self.quality == "final" else "veryfast"

    def scaled(self, factor: float) -> RenderSettings:
        even = lambda v: max(2, int(v * factor) // 2 * 2)  # noqa: E731
        return RenderSettings(even(self.width), even(self.height), self.fps, self.quality)


@dataclass(frozen=True)
class AudioCue:
    path: Path
    start: float
    gain_db: float = 0.0


@dataclass(frozen=True)
class SfxCue:
    kind: str
    start: float
    duration: float
    gain_db: float = -10.0


@dataclass
class TimelineSpec:
    scenes: list[SceneSpec]
    transitions: list[str]  # transition INTO scene i (index 0 ignored)
    narration: list[AudioCue] = field(default_factory=list)
    sfx: list[SfxCue] = field(default_factory=list)
    music_mood: str = "mystery"
    music_volume_db: float = -20.0
    music_path: Path | None = None
    music_cues: list[tuple[float, str]] = field(default_factory=list)
    seed: int = 0
