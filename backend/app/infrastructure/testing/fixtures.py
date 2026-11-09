"""Deterministic test doubles for automated tests and the lightweight pipeline test mode.

They are flagged ``is_test_double`` in health checks, labelled ``source=fixture`` on every asset they
produce, and refused by configuration validation in production. They never pretend to be AI output.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import soundfile as sf

from app.application.ports import (
    GeneratedImage,
    ImageRequest,
    ProviderHealth,
    Source,
    SpeechResult,
    T,
    TimedWord,
    Voice,
)
from app.domain import story
from app.infrastructure.images.procedural import ProceduralImageProvider

_TOPIC = re.compile(r"(?:TOPIC|SUBJECT|THEME)\s*:\s*(.+)", re.IGNORECASE)


def _topic(prompt: str) -> str:
    m = _TOPIC.search(prompt)
    return (m.group(1).strip().splitlines()[0] if m else "an unsolved historical mystery")[:80]


class FixtureLLM:
    name = "fixture_llm"
    model = "fixture"

    def health(self) -> ProviderHealth:
        return ProviderHealth(self.name, "llm", True, "TEST DOUBLE - deterministic templated output", is_test_double=True)

    def complete_json(self, system: str, prompt: str, schema: type[T], *, temperature: float = 0.7) -> T:
        topic = _topic(prompt)
        builder = getattr(self, f"_{schema.__name__}", None)
        if builder is None:
            raise NotImplementedError(schema.__name__)
        return schema.model_validate(builder(topic, prompt))

    def _StoryBrief(self, topic: str, _: str) -> dict:
        return {
            "subject_summary": f"A short documentary about {topic}.", "target_audience": "Curious history fans",
            "angle": "What the evidence actually shows", "emotional_arc": "curiosity -> tension -> reflection",
            "key_facts": [{"text": f"{topic} is documented in historical records.", "confidence": "well_established"}],
            "open_questions": ["What really happened?"], "music_mood": "mystery",
        }  # fmt: skip

    def _HookSet(self, topic: str, _: str) -> dict:
        styles = ["shocking", "mysterious", "question", "controversial", "emotional", "curiosity"]
        return {"hooks": [{"style": s, "text": f"{s.title()} hook: what happened with {topic}?"} for s in styles]}

    def _Script(self, topic: str, _: str) -> dict:
        return {
            "title": f"The Truth About {topic.title()}"[:80],
            "hook": f"Nobody expected what happened with {topic}.",
            "beginning": f"It began quietly. Records describe {topic} in only a few lines.",
            "middle": "Then the clues started to pile up. Each one raised a new question, and each answer seemed to "
            "contradict the last.",
            "conclusion": "Historians still debate the details today. What do you think happened?",
            "claims": [{"text": f"{topic} is recorded in contemporary sources.", "confidence": "well_established"}],
        }

    def _StoryboardDraft(self, topic: str, prompt: str) -> dict:
        m = re.search(r"exactly (\d+) scenes", prompt)
        count = int(m.group(1)) if m else 5
        narr = re.search(r"NARRATION:\s*(.+?)\n\n", prompt, re.S)
        words = (narr.group(1) if narr else f"This is the story of {topic}. " * count).split()
        per = max(1, len(words) // count)
        types = ["cinematic_image", "historical_map", "timeline", "parallax", "kinetic_typography", "infographic"]
        scenes = []
        for i in range(count):
            chunk = words[i * per : (i + 1) * per] if i < count - 1 else words[i * per :]
            scenes.append({
                "title": f"Scene {i + 1}", "narration": " ".join(chunk) or topic, "visual_type": types[i % len(types)],
                "visual_description": f"Moody depiction of {topic}", "image_prompt": f"{topic}, cinematic, dramatic light",
                "camera_movement": ["slow_zoom_in", "static", "pan_left", "parallax_drift", "static", "static"][i % 6],
                "effects": [["fog"], [], ["dust"], ["embers"], ["light_rays"], []][i % 6],
                "transition": "cut" if i == 0 else "crossfade", "emphasis_words": chunk[:1], "mood": "mysterious",
                "color_palette": ["#0f172a", "#a78bfa", "#38bdf8"], "sound_effects": ["whoosh"] if i else [],
                "visual_data": {"places": [{"name": "London"}, {"name": "New York"}], "draw_route": True,
                                "events": [{"date": "1587", "label": "Founded"}, {"date": "1590", "label": "Abandoned"}],
                                "stats": [{"label": "People", "value": 115}]},
            })  # fmt: skip
        return {"scenes": scenes}

    def _SceneDraft(self, topic: str, prompt: str) -> dict:
        return self._StoryboardDraft(topic, "exactly 1 scenes")["scenes"][0] | {"title": "Regenerated scene"}

    def _SeriesPlan(self, topic: str, prompt: str) -> dict:
        m = re.search(r"exactly (\d+) episodes", prompt)
        n = int(m.group(1)) if m else 3
        return {
            "series_title": f"Mysteries of {topic.title()}"[:80], "logline": f"A series about {topic}.",
            "visual_style_notes": "Dark, cinematic, foggy",
            "recurring_characters": [{"name": "The Narrator", "visual_description": "Silhouette in a long coat"}],
            "recurring_locations": ["Old archive"],
            "episodes": [{"title": f"Episode {i + 1}: Chapter {i + 1}", "premise": f"Part {i + 1} of {topic}",
                          "hook": f"Chapter {i + 1} changes everything."} for i in range(n)],
        }  # fmt: skip

    def _TopicIdeas(self, topic: str, _: str) -> dict:
        return {"ideas": [{"title": f"{topic.title()} idea {i + 1}", "premise": "Premise", "hook": "Hook"} for i in range(5)]}

    def _ClaimCheck(self, topic: str, _: str) -> dict:
        return {"verdict": "supported", "explanation": "Test double: no real verification performed."}


class FixtureImageProvider(ProceduralImageProvider):
    name = "fixture_image"

    def health(self) -> ProviderHealth:
        return ProviderHealth(self.name, "image", True, "TEST DOUBLE - procedural images", is_test_double=True)

    def generate_image(self, request: ImageRequest, palette: tuple[str, ...] | None = None) -> GeneratedImage:
        img = super().generate_image(request, palette)
        return GeneratedImage(img.data, img.width, img.height, self.name, "fixture", "fixture")


class FixtureTTS:
    name = "fixture_tts"
    words_per_second = 2.6

    def health(self) -> ProviderHealth:
        return ProviderHealth(self.name, "tts", True, "TEST DOUBLE - tone audio, not speech", is_test_double=True)

    def list_voices(self) -> list[Voice]:
        return [Voice("af_heart", "Heart", "en", "female", "American"), Voice("am_michael", "Michael", "en", "male", "American")]

    def generate_speech(self, text: str, voice_id: str, speed: float, out_path: Path, language: str = "en") -> SpeechResult:
        rate = 24000
        duration = max(0.6, len(text.split()) / self.words_per_second / max(0.5, speed))
        t = np.arange(int(duration * rate)) / rate
        syllables = (np.sin(2 * np.pi * 4.2 * t) > -0.2).astype(np.float32)
        audio = (0.25 * np.sin(2 * np.pi * (140 + 20 * np.sin(2 * np.pi * 0.7 * t)) * t) * syllables).astype(np.float32)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), audio, rate, subtype="PCM_16")
        return SpeechResult(out_path, duration, rate, self.name, "fixture")


class FixtureTranscriber:
    name = "fixture_stt"

    def health(self) -> ProviderHealth:
        return ProviderHealth(self.name, "stt", True, "TEST DOUBLE - estimated timings", is_test_double=True)

    def get_word_timestamps(self, audio_path: Path, language: str = "en") -> list[TimedWord]:
        return []  # forces alignment to fall back to estimated timings


class FixtureResearch:
    name = "fixture_research"

    def health(self) -> ProviderHealth:
        return ProviderHealth(self.name, "research", True, "TEST DOUBLE", is_test_double=True)

    def search_sources(self, query: str, limit: int = 3) -> list[Source]:
        return [Source("Test source", "https://example.org/test", f"Excerpt about {query}")]

    def retrieve_source(self, title: str) -> Source | None:
        return Source(title, "https://example.org/test", "Excerpt")


__all__ = ["FixtureImageProvider", "FixtureLLM", "FixtureResearch", "FixtureTTS", "FixtureTranscriber", "story"]
