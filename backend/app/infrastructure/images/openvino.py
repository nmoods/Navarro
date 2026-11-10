"""OpenVINO GenAI image provider: a Latent Consistency Model (LCM Dreamshaper v7, INT8) run in-process on
the CPU (or an Intel GPU/NPU). LCM needs only ~4 denoising steps, and OpenVINO's INT8 kernels make each step
several times faster than PyTorch on CPU, so an image takes seconds instead of minutes on a desktop CPU.

The pipeline is loaded lazily on first use and kept in memory; generation is serialised with a lock because
one compiled pipeline must not run two requests at once.
"""

from __future__ import annotations

import importlib.util
import logging
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from app.application.ports import GeneratedImage, ImageRequest, ProviderHealth
from app.core.errors import ProviderError, ProviderUnavailableError

logger = logging.getLogger("narravo.openvino")


class OpenVINOImageProvider:
    name = "openvino"

    def __init__(self, model_dir: Path, device: str = "CPU", steps: int = 4, guidance: float = 8.0) -> None:
        self.model_dir, self.device, self.steps, self.guidance = Path(model_dir), device, steps, guidance
        self.checkpoint = self.model_dir.name
        self._pipe = None
        self._lock = threading.Lock()

    def _problem(self) -> str | None:
        if importlib.util.find_spec("openvino_genai") is None:
            return "openvino-genai is not installed"
        if not (self.model_dir / "model_index.json").is_file():
            return f"model not downloaded to {self.model_dir} (run the AI setup script)"
        return None

    def health(self) -> ProviderHealth:
        problem = self._problem()
        if problem:
            return ProviderHealth(self.name, "image", False, problem)
        return ProviderHealth(self.name, "image", True, f"{self.checkpoint} on {self.device}, {self.steps} steps",
                              {"checkpoint": self.checkpoint, "steps": self.steps, "device": self.device})  # fmt: skip

    def warm_up(self) -> None:
        with self._lock:
            self._pipeline()

    def _pipeline(self):  # noqa: ANN202 - openvino_genai types are optional at import time
        if self._pipe is None:
            import openvino_genai as ov_genai

            started = time.monotonic()
            self._pipe = ov_genai.Text2ImagePipeline(str(self.model_dir), self.device)
            logger.info("OpenVINO pipeline loaded in %.1fs", time.monotonic() - started)
        return self._pipe

    def generate_image(self, request: ImageRequest) -> GeneratedImage:
        problem = self._problem()
        if problem:
            raise ProviderUnavailableError(self.name, problem)
        with self._lock:
            try:
                tensor = self._pipeline().generate(
                    request.prompt, width=request.width, height=request.height, num_inference_steps=self.steps,
                    guidance_scale=self.guidance, rng_seed=request.seed,
                )  # fmt: skip
            except RuntimeError as exc:
                raise ProviderError(self.name, f"OpenVINO generation failed: {str(exc)[:300]}") from exc
        rgb = np.asarray(tensor.data)[0]
        ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if not ok:
            raise ProviderError(self.name, "Could not encode the generated image")
        return GeneratedImage(buf.tobytes(), int(rgb.shape[1]), int(rgb.shape[0]), self.name, self.checkpoint, "generated")
