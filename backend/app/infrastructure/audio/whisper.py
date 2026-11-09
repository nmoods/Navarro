"""faster-whisper word timestamps, plus alignment of recognised words back onto the known script text."""

from __future__ import annotations

import difflib
import re
import threading
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

from app.application.ports import ProviderHealth, TimedWord
from app.core.errors import ProviderUnavailableError

_WORD = re.compile(r"[\w']+", re.UNICODE)


def _load_16k_mono(path: Path) -> np.ndarray:
    data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != 16000:
        g = gcd(int(rate), 16000)
        mono = signal.resample_poly(mono, 16000 // g, int(rate) // g)
    return mono.astype(np.float32)


class FasterWhisperProvider:
    name = "faster_whisper"

    def __init__(self, model: str, compute_type: str = "int8", cpu_threads: int = 4) -> None:
        self.model_name, self.compute_type, self.cpu_threads = model, compute_type, cpu_threads
        self._model = None
        self._lock = threading.Lock()

    def health(self) -> ProviderHealth:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return ProviderHealth(self.name, "stt", False, "faster-whisper not installed")
        state = "loaded" if self._model else "loads on first use (downloads once from Hugging Face)"
        return ProviderHealth(self.name, "stt", True, f"{self.model_name} {self.compute_type}, {state}", {"word_timestamps": True})

    def _load(self):  # type: ignore[no-untyped-def]
        with self._lock:
            if self._model is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as exc:
                    raise ProviderUnavailableError(self.name, "faster-whisper is not installed") from exc
                self._model = WhisperModel(self.model_name, device="cpu", compute_type=self.compute_type,
                                           cpu_threads=self.cpu_threads)  # fmt: skip
            return self._model

    def get_word_timestamps(self, audio_path: Path, language: str = "en") -> list[TimedWord]:
        model = self._load()
        audio = _load_16k_mono(audio_path)  # decode ourselves: avoids PyAV version coupling
        segments, _ = model.transcribe(audio, language=language, word_timestamps=True, vad_filter=False,
                                       beam_size=1, condition_on_previous_text=False)  # fmt: skip
        words: list[TimedWord] = []
        for seg in segments:
            for w in seg.words or []:
                words.append(TimedWord(w.word.strip(), float(w.start), float(w.end), float(w.probability)))
        return words


def estimate_word_timestamps(text: str, duration: float, lead: float = 0.05) -> list[TimedWord]:
    """Fallback when no recogniser is available: distribute time by syllable-ish weight (labelled estimated)."""
    tokens = text.split()
    if not tokens:
        return []
    weights = [max(1.0, len(re.findall(r"[aeiouy]+", t.lower())) + (0.6 if t[-1:] in ",.;:!?" else 0)) for t in tokens]
    usable = max(0.1, duration - lead * 2)
    per = usable / sum(weights)
    out, cursor = [], lead
    for tok, w in zip(tokens, weights, strict=True):
        span = w * per
        out.append(TimedWord(tok, cursor, cursor + span * 0.92))
        cursor += span
    return out


def align_to_script(script: str, recognised: list[TimedWord], duration: float) -> list[TimedWord]:
    """Map recogniser timings onto the exact script tokens (keeps the writer's spelling and punctuation).

    Matched tokens take recognised timings; unmatched runs are interpolated between their neighbours.
    """
    tokens = script.split()
    if not tokens:
        return []
    if not recognised:
        return estimate_word_timestamps(script, duration)
    norm = lambda s: "".join(_WORD.findall(s.lower()))  # noqa: E731
    a = [norm(t) for t in tokens]
    b = [norm(w.text) for w in recognised]
    times: list[tuple[float, float] | None] = [None] * len(tokens)
    for block in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            w = recognised[block.b + k]
            times[block.a + k] = (w.start, w.end)
    i = 0
    while i < len(tokens):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(tokens) and times[j] is None:
            j += 1
        left = times[i - 1][1] if i > 0 and times[i - 1] else 0.0
        right = times[j][0] if j < len(tokens) and times[j] else duration
        span = max(0.05, right - left) / (j - i)
        for k in range(i, j):
            times[k] = (left + (k - i) * span, left + (k - i + 1) * span * 0.95)
        i = j
    return [TimedWord(tok, t[0], max(t[0] + 0.04, t[1])) for tok, t in zip(tokens, times, strict=True) if t]
