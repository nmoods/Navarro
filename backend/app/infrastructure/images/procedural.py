"""Procedural (non-AI) art provider used when ComfyUI is offline. Clearly labelled ``source=procedural``."""

from __future__ import annotations

import cv2

from app.application.ports import GeneratedImage, ImageRequest, ProviderHealth
from app.media.spec import CaptionStyle, SceneSpec
from app.media.visuals.stills import procedural_backdrop


class ProceduralImageProvider:
    name = "procedural"

    def __init__(self, palette: tuple[str, ...] = ("#0f172a", "#7c3aed", "#38bdf8")) -> None:
        self.palette = palette

    def health(self) -> ProviderHealth:
        return ProviderHealth(self.name, "image", True, "Procedural landscapes (no AI model)", {"ai": False})

    def generate_image(self, request: ImageRequest, palette: tuple[str, ...] | None = None) -> GeneratedImage:
        spec = SceneSpec(0, "cinematic_image", 1, 0, "static", (), None, {}, palette or self.palette, "", "cinematic_documentary",
                         (), CaptionStyle(), seed=request.seed)  # fmt: skip
        img, _ = procedural_backdrop(spec, request.width, request.height)
        ok, buf = cv2.imencode(".png", img)
        assert ok
        return GeneratedImage(buf.tobytes(), request.width, request.height, self.name, "procedural-landscape", "procedural")
