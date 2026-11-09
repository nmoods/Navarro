"""Provider interfaces (ports). Business logic depends only on these; adapters live in infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ProviderHealth:
    name: str
    kind: str  # llm | image | tts | stt | research
    available: bool
    detail: str
    capabilities: dict = field(default_factory=dict)
    is_test_double: bool = False


class LLMProvider(Protocol):
    name: str
    model: str

    def health(self) -> ProviderHealth: ...

    def complete_json(self, system: str, prompt: str, schema: type[T], *, temperature: float = 0.7) -> T:
        """Return a schema-validated object. Must raise ProviderUnavailableError / ProviderError."""
        ...


@dataclass(frozen=True)
class ImageRequest:
    prompt: str
    negative_prompt: str
    width: int
    height: int
    seed: int


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes  # PNG
    width: int
    height: int
    provider: str
    model: str
    source: str  # generated | procedural | fixture


class ImageProvider(Protocol):
    name: str

    def health(self) -> ProviderHealth: ...

    def generate_image(self, request: ImageRequest) -> GeneratedImage: ...


@dataclass(frozen=True)
class Voice:
    id: str
    name: str
    language: str
    gender: str
    accent: str


@dataclass(frozen=True)
class SpeechResult:
    path: Path  # WAV
    duration: float
    sample_rate: int
    provider: str
    source: str


class TTSProvider(Protocol):
    name: str

    def health(self) -> ProviderHealth: ...

    def list_voices(self) -> list[Voice]: ...

    def generate_speech(self, text: str, voice_id: str, speed: float, out_path: Path, language: str = "en") -> SpeechResult: ...


@dataclass(frozen=True)
class TimedWord:
    text: str
    start: float
    end: float
    probability: float = 1.0


class TranscriptionProvider(Protocol):
    name: str

    def health(self) -> ProviderHealth: ...

    def get_word_timestamps(self, audio_path: Path, language: str = "en") -> list[TimedWord]: ...


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    excerpt: str


class ResearchProvider(Protocol):
    name: str

    def health(self) -> ProviderHealth: ...

    def search_sources(self, query: str, limit: int = 3) -> list[Source]: ...

    def retrieve_source(self, title: str) -> Source | None: ...
