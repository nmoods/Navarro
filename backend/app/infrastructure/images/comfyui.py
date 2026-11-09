"""ComfyUI adapter: builds an API-format workflow (SD 1.5 checkpoint + optional LCM LoRA), queues it,
polls history and downloads the PNG. ComfyUI (GPL-3.0) runs as a separate process, called over HTTP."""

from __future__ import annotations

import time
import uuid

import httpx

from app.application.ports import GeneratedImage, ImageRequest, ProviderHealth
from app.core.errors import ProviderError, ProviderUnavailableError


def build_workflow(req: ImageRequest, checkpoint: str, lora: str | None, steps: int, cfg: float) -> dict:
    model_ref, clip_ref = ["1", 0], ["1", 1]
    wf: dict[str, dict] = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
    }
    if lora:
        wf["2"] = {
            "class_type": "LoraLoader",
            "inputs": {"model": model_ref, "clip": clip_ref, "lora_name": lora, "strength_model": 1.0, "strength_clip": 1.0},
        }
        model_ref, clip_ref = ["2", 0], ["2", 1]
    sampler, scheduler = ("lcm", "sgm_uniform") if lora else ("dpmpp_2m", "karras")
    wf |= {
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": req.prompt, "clip": clip_ref}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": req.negative_prompt, "clip": clip_ref}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": req.width, "height": req.height, "batch_size": 1}},
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": model_ref, "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
                "seed": req.seed, "steps": steps, "cfg": cfg, "sampler_name": sampler, "scheduler": scheduler,
                "denoise": 1.0,
            },
        },  # fmt: skip
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "reelforge"}},
    }
    return wf


class ComfyUIProvider:
    name = "comfyui"

    def __init__(self, base_url: str, checkpoint: str, lora: str | None, steps: int, cfg: float, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.checkpoint, self.lora, self.steps, self.cfg, self.timeout = checkpoint, lora, steps, cfg, timeout
        self.client_id = uuid.uuid4().hex

    def health(self) -> ProviderHealth:
        try:
            resp = httpx.get(f"{self.base_url}/object_info/CheckpointLoaderSimple", timeout=3.0)
            resp.raise_for_status()
            ckpts = resp.json()["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        except (httpx.HTTPError, KeyError, ValueError, IndexError) as exc:
            return ProviderHealth(self.name, "image", False, f"ComfyUI not reachable at {self.base_url} ({type(exc).__name__})")
        ok = self.checkpoint in ckpts
        detail = f"checkpoint {self.checkpoint} ready" if ok else f"checkpoint {self.checkpoint} missing from ComfyUI/models/checkpoints"
        return ProviderHealth(self.name, "image", ok, detail, {"checkpoint": self.checkpoint, "lora": self.lora, "steps": self.steps})

    def generate_image(self, request: ImageRequest) -> GeneratedImage:
        wf = build_workflow(request, self.checkpoint, self.lora, self.steps, self.cfg)
        try:
            resp = httpx.post(f"{self.base_url}/prompt", json={"prompt": wf, "client_id": self.client_id}, timeout=30)
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(self.name, "ComfyUI is not running") from exc
        if resp.status_code >= 400:
            raise ProviderError(self.name, f"ComfyUI rejected the workflow: {resp.text[:300]}", retryable=False)
        prompt_id = resp.json()["prompt_id"]
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            time.sleep(1.0)
            hist = httpx.get(f"{self.base_url}/history/{prompt_id}", timeout=10).json()
            entry = hist.get(prompt_id)
            if not entry:
                continue
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise ProviderError(self.name, f"ComfyUI execution failed: {str(status.get('messages', ''))[:300]}")
            for output in entry.get("outputs", {}).values():
                for img in output.get("images", []):
                    data = httpx.get(
                        f"{self.base_url}/view",
                        params={"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")},
                        timeout=30,
                    ).content
                    return GeneratedImage(data, request.width, request.height, self.name, self.checkpoint, "generated")
        raise ProviderError(self.name, f"ComfyUI timed out after {self.timeout:.0f}s")
