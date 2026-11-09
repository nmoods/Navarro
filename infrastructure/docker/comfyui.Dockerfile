# ComfyUI (GPL-3.0) as an isolated internal service, CPU build. Models are downloaded on first build.
FROM python:3.13-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends git curl libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git /opt/ComfyUI
WORKDIR /opt/ComfyUI
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
# Stable Diffusion 1.5 (CreativeML OpenRAIL-M, use restrictions apply) + LCM-LoRA (OpenRAIL++)
RUN curl -fL -o models/checkpoints/v1-5-pruned-emaonly-fp16.safetensors \
      https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly-fp16.safetensors \
 && curl -fL -o models/loras/lcm-lora-sdv1-5.safetensors \
      https://huggingface.co/latent-consistency/lcm-lora-sdv1-5/resolve/main/pytorch_lora_weights.safetensors
RUN useradd --create-home --uid 10002 comfy && chown -R comfy /opt/ComfyUI
USER comfy
# Listens on the internal compose network only (not published to the host).
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188", "--cpu", "--disable-auto-launch"]
