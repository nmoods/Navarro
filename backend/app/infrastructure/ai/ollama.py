"""Ollama adapter using structured outputs (``format`` = JSON schema) with validation-feedback retries."""

from __future__ import annotations

import json
import logging

import httpx
from pydantic import ValidationError

from app.application.ports import ProviderHealth, T
from app.core.errors import ProviderError, ProviderUnavailableError

logger = logging.getLogger("narravo.ollama")


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 600.0, max_repairs: int = 2) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_repairs = max_repairs

    def health(self) -> ProviderHealth:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]
        except (httpx.HTTPError, ValueError) as exc:
            return ProviderHealth(self.name, "llm", False, f"Ollama not reachable at {self.base_url} ({type(exc).__name__})")
        installed = self.model in models or f"{self.model}:latest" in models
        detail = f"model {self.model} ready" if installed else f"model {self.model} not pulled (run: ollama pull {self.model})"
        return ProviderHealth(self.name, "llm", installed, detail, {"model": self.model, "installed_models": models[:20]})

    def complete_json(self, system: str, prompt: str, schema: type[T], *, temperature: float = 0.7) -> T:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        last_error = ""
        for attempt in range(self.max_repairs + 1):
            raw = self._chat(messages, schema.model_json_schema(), temperature)
            try:
                return schema.model_validate_json(raw)
            except ValidationError as exc:
                last_error = str(exc)[:1500]
                logger.warning("LLM output failed validation (attempt %d)", attempt + 1, extra={"data": {"err": last_error[:300]}})
                messages += [
                    {"role": "assistant", "content": raw[:6000]},
                    {"role": "user", "content": f"That JSON did not match the schema:\n{last_error}\nReturn corrected JSON only."},
                ]
        raise ProviderError(self.name, f"Model output did not match the expected structure: {last_error[:300]}")

    def _chat(self, messages: list[dict], schema: dict, temperature: float) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "format": schema,
            "stream": False,
            "think": False,
            "keep_alive": "30m",  # a story is several calls; reloading the model between them costs seconds
            "options": {"temperature": temperature, "num_ctx": 8192},
        }
        try:
            resp = httpx.post(f"{self.base_url}/api/chat", json=body, timeout=self.timeout)
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(self.name, "Ollama is not running. Start it with `ollama serve`.") from exc
        except httpx.TimeoutException as exc:
            raise ProviderError(self.name, f"Ollama timed out after {self.timeout:.0f}s") from exc
        if resp.status_code == 404:
            raise ProviderUnavailableError(self.name, f"Model '{self.model}' is not installed. Run `ollama pull {self.model}`.")
        if resp.status_code == 400 and "think" in resp.text:
            body.pop("think")  # older Ollama or a model without thinking support
            resp = httpx.post(f"{self.base_url}/api/chat", json=body, timeout=self.timeout)
        if resp.status_code >= 400:
            raise ProviderError(self.name, f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            data = resp.json()
            content = data["message"]["content"]
        except (KeyError, ValueError) as exc:
            raise ProviderError(self.name, "Malformed Ollama response") from exc
        logger.info("ollama %s: %s prompt tokens, %s output tokens in %.1fs", self.model, data.get("prompt_eval_count"),
                    data.get("eval_count"), (data.get("total_duration") or 0) / 1e9)  # fmt: skip
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`").removeprefix("json").strip()
        try:
            json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start >= 0 and end > start:
                content = content[start : end + 1]
        return content
