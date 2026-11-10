"""Download NaRRAVO's default image model for the OpenVINO provider.

Assembles one folder from two Hugging Face repositories:
  * OpenVINO/LCM_Dreamshaper_v7-int8-ov (MIT; derived from SD 1.5, whose CreativeML OpenRAIL-M use
    restrictions still apply to generated images): text encoder, tokenizer, scheduler, INT8 UNet.
  * rupeshs/taesd-ov (MIT; TAESD by madebyollin): a tiny VAE decoder that decodes in well under a second
    on a CPU, instead of ~12 s for the full decoder, with near-identical results at 512 px.
Files the OpenVINO pipeline never loads (safety checker weights, encoders) are skipped.

Usage (from the repo root):  uv run --project backend python infrastructure/scripts/fetch_image_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / ".runtime" / "models" / "openvino" / "lcm-dreamshaper-v7-taesd"


def main(target: Path = TARGET) -> None:
    if (target / "model_index.json").is_file() and (target / "vae_decoder" / "openvino_model.xml").is_file():
        print(f"  exists: {target}")
        return
    print(f"  downloading LCM Dreamshaper v7 (INT8, OpenVINO) to {target}")
    snapshot_download("OpenVINO/LCM_Dreamshaper_v7-int8-ov", local_dir=target,
                      allow_patterns=["model_index.json", "scheduler/*", "text_encoder/*", "tokenizer/*", "unet/*"])  # fmt: skip
    print("  downloading TAESD decoder (OpenVINO)")
    snapshot_download("rupeshs/taesd-ov", local_dir=target, allow_patterns=["vae_decoder/*"])
    print("  done")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET)
