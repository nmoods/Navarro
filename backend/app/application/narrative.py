"""Narrative Intelligence: deterministic script splitting and pacing analysis (no LLM needed)."""

from __future__ import annotations

import re
from collections import Counter

_SENTENCE = re.compile(r"(?<=[.!?…])\s+(?=[\"'“A-Z0-9¿¡À-ÖØ-Þ])")
_STOP = set(
    "the a an and or but of to in on at for with by from as is was were be been are it its this that these those he "
    "she they them his her their we you i not no so than then there what which who when where why how into over "
    "under after before about up out more most just only also very".split()
)


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE.split(text.strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def split_into_scenes(text: str, scene_count: int) -> list[str]:
    """Group sentences into ``scene_count`` scenes with balanced word counts; never alters the words."""
    sentences = split_sentences(text)
    if not sentences:
        return []
    count = max(1, min(scene_count, len(sentences)))
    total = sum(len(s.split()) for s in sentences)
    target = total / count
    scenes: list[list[str]] = [[]]
    acc = 0
    for i, sentence in enumerate(sentences):
        remaining_sentences = len(sentences) - i
        remaining_slots = count - len(scenes)
        words = len(sentence.split())
        must_break = remaining_sentences <= remaining_slots
        should_break = scenes[-1] and acc + words / 2 > target * len(scenes) and remaining_slots > 0
        if scenes[-1] and (must_break or should_break):
            scenes.append([])
        scenes[-1].append(sentence)
        acc += words
    return [" ".join(s) for s in scenes if s]


def analyse(scenes: list[str], hook: str, words_per_second: float = 2.45) -> dict:
    """Pacing report surfaced in the editor: durations, density, repetition and hook strength."""
    words_per_scene = [len(s.split()) for s in scenes]
    total_words = sum(words_per_scene)
    tokens = [w for w in re.findall(r"[a-zA-Z']+", " ".join(scenes).lower()) if w not in _STOP and len(w) > 3]
    repeated = [w for w, c in Counter(tokens).most_common(8) if c >= 4]
    bigrams = Counter(zip(tokens, tokens[1:], strict=False))
    repeated_phrases = [" ".join(b) for b, c in bigrams.most_common(5) if c >= 3]
    warnings: list[str] = []
    hook_words = len(hook.split())
    if hook_words > 22:
        warnings.append(f"Hook is {hook_words} words; under 22 keeps it inside the first ~3 seconds.")
    if hook and not re.search(r"[?!]|never|nobody|no one|vanish|secret|truth|why|how", hook.lower()):
        warnings.append("Hook has no tension marker (question, contradiction or stakes).")
    for i, n in enumerate(words_per_scene):
        if n > 40:
            warnings.append(f"Scene {i + 1} is long ({n} words, ~{n / words_per_second:.0f}s); consider splitting it.")
        elif n < 5:
            warnings.append(f"Scene {i + 1} is very short ({n} words).")
    if repeated:
        warnings.append("Repeated words: " + ", ".join(repeated))
    return {
        "total_words": total_words,
        "estimated_seconds": round(total_words / words_per_second, 1),
        "words_per_scene": words_per_scene,
        "estimated_scene_seconds": [round(n / words_per_second, 1) for n in words_per_scene],
        "repeated_words": repeated,
        "repeated_phrases": repeated_phrases,
        "hook_words": hook_words,
        "warnings": warnings,
    }
