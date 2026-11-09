"""Kokoro-82M TTS via the isolated worker process (see ai-engine/tts-worker)."""

from __future__ import annotations

import json
import logging
import subprocess
import threading
from pathlib import Path

from app.application.ports import ProviderHealth, SpeechResult, Voice
from app.core.errors import ProviderError, ProviderUnavailableError

logger = logging.getLogger("reelforge.kokoro")

_ACCENTS = {"a": ("en", "American"), "b": ("en", "British"), "e": ("es", "Spanish"), "f": ("fr", "French"),
            "h": ("hi", "Hindi"), "i": ("it", "Italian"), "j": ("ja", "Japanese"), "p": ("pt", "Brazilian Portuguese"),
            "z": ("zh", "Mandarin")}  # fmt: skip
_LANG_CODES = {"en": "en-us", "es": "es", "fr": "fr-fr", "hi": "hi", "it": "it", "ja": "ja", "pt": "pt-br", "zh": "cmn"}


def describe_voice(voice_id: str) -> Voice:
    prefix = voice_id[:2]
    lang, accent = _ACCENTS.get(prefix[:1], ("en", "Unknown"))
    gender = {"f": "female", "m": "male"}.get(prefix[1:2], "unknown")
    name = voice_id[3:].replace("_", " ").title() if len(voice_id) > 3 else voice_id
    return Voice(voice_id, name, lang, gender, accent)


class KokoroProvider:
    name = "kokoro"

    def __init__(self, python_exe: Path, script: Path, model: Path, voices: Path, timeout: float = 300.0) -> None:
        self.python_exe, self.script, self.model, self.voices = python_exe, script, model, voices
        self.timeout = timeout
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._voices: list[Voice] | None = None

    def _missing(self) -> str | None:
        for label, path in (("worker python", self.python_exe), ("worker script", self.script),
                            ("model", self.model), ("voices", self.voices)):  # fmt: skip
            if not path.exists():
                return f"Kokoro {label} not found at {path}"
        return None

    def health(self) -> ProviderHealth:
        missing = self._missing()
        if missing:
            return ProviderHealth(self.name, "tts", False, missing + " (run infrastructure/scripts/setup-ai)")
        return ProviderHealth(self.name, "tts", True, "Kokoro-82M (Apache-2.0) via isolated worker",
                              {"voices": len(self._voices or []), "blending": True})  # fmt: skip

    def _ensure(self) -> subprocess.Popen[str]:
        if self._proc and self._proc.poll() is None:
            return self._proc
        missing = self._missing()
        if missing:
            raise ProviderUnavailableError(self.name, missing)
        self._proc = subprocess.Popen(  # noqa: S603 - fixed executable and script from server config
            [str(self.python_exe), str(self.script), str(self.model), str(self.voices)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            bufsize=1,
        )  # fmt: skip
        ready = self._read()
        if not ready.get("ready"):
            raise ProviderUnavailableError(self.name, "Kokoro worker failed to start")
        return self._proc

    def _read(self) -> dict:
        assert self._proc and self._proc.stdout
        result: list[str] = []
        reader = threading.Thread(target=lambda: result.append(self._proc.stdout.readline()), daemon=True)  # type: ignore[union-attr]
        reader.start()
        reader.join(self.timeout)
        if not result or not result[0]:
            self.close()
            raise ProviderError(self.name, "Kokoro worker did not respond")
        return json.loads(result[0])

    def _call(self, request: dict) -> dict:
        with self._lock:
            proc = self._ensure()
            assert proc.stdin
            try:
                proc.stdin.write(json.dumps(request) + "\n")
                proc.stdin.flush()
            except OSError as exc:
                self.close()
                raise ProviderError(self.name, "Kokoro worker crashed") from exc
            resp = self._read()
        if not resp.get("ok"):
            raise ProviderError(self.name, resp.get("error", "TTS failed"), retryable=False)
        return resp

    def list_voices(self) -> list[Voice]:
        if self._voices is None:
            self._voices = [describe_voice(v) for v in self._call({"op": "voices"})["voices"]]
        return self._voices

    def generate_speech(self, text: str, voice_id: str, speed: float, out_path: Path, language: str = "en") -> SpeechResult:
        resp = self._call({
            "op": "synthesize", "text": text, "voice": voice_id, "speed": max(0.5, min(2.0, speed)),
            "lang": _LANG_CODES.get(language, "en-us"), "out": str(out_path),
        })  # fmt: skip
        return SpeechResult(out_path, float(resp["duration"]), int(resp["sample_rate"]), self.name, "generated")

    def close(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.kill()
        self._proc = None
