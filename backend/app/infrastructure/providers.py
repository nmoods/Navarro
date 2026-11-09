"""Provider registry: builds adapters from settings and exposes availability/capabilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache

from app.application.ports import (
    ImageProvider,
    LLMProvider,
    ProviderHealth,
    ResearchProvider,
    TranscriptionProvider,
    TTSProvider,
)
from app.core.config import Settings, get_settings
from app.infrastructure.ai.ollama import OllamaProvider
from app.infrastructure.audio.kokoro import KokoroProvider
from app.infrastructure.audio.whisper import FasterWhisperProvider
from app.infrastructure.images.comfyui import ComfyUIProvider
from app.infrastructure.images.procedural import ProceduralImageProvider
from app.infrastructure.research.wikipedia import WikipediaResearchProvider
from app.infrastructure.testing import fixtures

logger = logging.getLogger("reelforge.providers")


@dataclass
class Providers:
    llm: LLMProvider
    image: ImageProvider
    image_fallback: ImageProvider
    tts: TTSProvider
    stt: TranscriptionProvider
    research: ResearchProvider | None
    auto_image: bool = False
    _image_ok_cache: dict = field(default_factory=dict)

    def all(self) -> list:
        items = [self.llm, self.image, self.tts, self.stt]
        if self.auto_image:
            items.append(self.image_fallback)
        if self.research:
            items.append(self.research)
        return items

    def health(self) -> list[ProviderHealth]:
        out = []
        for provider in self.all():
            try:
                out.append(provider.health())
            except Exception as exc:  # a broken adapter must never take the API down
                logger.exception("health check failed for %s", provider.name)
                out.append(ProviderHealth(provider.name, "unknown", False, f"health check error: {type(exc).__name__}"))
        return out

    def image_for_generation(self) -> ImageProvider:
        """In auto mode use ComfyUI when healthy, otherwise fall back to (clearly labelled) procedural art."""
        if not self.auto_image:
            return self.image
        return self.image if self.image.health().available else self.image_fallback


def build_providers(settings: Settings) -> Providers:
    llm: LLMProvider = (
        fixtures.FixtureLLM()
        if settings.llm_provider == "fixture"
        else OllamaProvider(settings.ollama_url, settings.ollama_model, settings.llm_timeout_seconds)
    )
    comfy = ComfyUIProvider(settings.comfyui_url, settings.comfyui_checkpoint, settings.comfyui_lcm_lora,
                            settings.comfyui_steps, settings.comfyui_cfg, settings.comfyui_timeout_seconds)  # fmt: skip
    procedural = ProceduralImageProvider()
    image: ImageProvider
    match settings.image_provider:
        case "fixture":
            image = fixtures.FixtureImageProvider()
        case "procedural":
            image = procedural
        case _:
            image = comfy
    tts: TTSProvider = (
        fixtures.FixtureTTS()
        if settings.tts_provider == "fixture"
        else KokoroProvider(settings.kokoro_worker_python, settings.kokoro_worker_script,
                            settings.kokoro_model_path, settings.kokoro_voices_path)  # fmt: skip
    )
    stt: TranscriptionProvider = (
        fixtures.FixtureTranscriber()
        if settings.stt_provider == "fixture"
        else FasterWhisperProvider(settings.whisper_model, settings.whisper_compute_type)
    )
    research: ResearchProvider | None = None
    if settings.research_enabled:
        research = (
            fixtures.FixtureResearch() if settings.llm_provider == "fixture"
            else WikipediaResearchProvider(settings.research_user_agent)
        )  # fmt: skip
    return Providers(llm, image, procedural, tts, stt, research, auto_image=settings.image_provider == "auto")


@lru_cache
def get_providers() -> Providers:
    return build_providers(get_settings())
