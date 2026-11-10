#!/usr/bin/env bash
# NaRRAVO - full local AI setup for macOS / Linux. Installs under <repo>/.runtime (git-ignored).
#   ./infrastructure/scripts/setup-ai.sh [--with-comfy] [--skip-ollama] [--model qwen3.5:4b]
# Images use OpenVINO on the CPU by default. ComfyUI is installed with --with-comfy or when an NVIDIA GPU is
# present (Apple Silicon users who want GPU images should pass --with-comfy).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME="$ROOT/.runtime"
MODEL="qwen3.5:4b"; WITH_COMFY=0; SKIP_OLLAMA=0
command -v nvidia-smi >/dev/null && WITH_COMFY=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-comfy) WITH_COMFY=1 ;; --skip-ollama) SKIP_OLLAMA=1 ;; --model) MODEL="$2"; shift ;;
    *) echo "unknown option $1"; exit 1 ;;
  esac; shift
done
mkdir -p "$RUNTIME"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.13

download() { [[ -f "$2" ]] && { echo "  exists: $2"; return; }; mkdir -p "$(dirname "$2")"; curl -fL --retry 3 -o "$2.part" "$1" && mv "$2.part" "$2"; }

echo "[1/4] Kokoro TTS worker"
(cd "$ROOT/ai-engine/tts-worker" && uv sync)
K="$RUNTIME/models/kokoro"
download https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx "$K/kokoro-v1.0.onnx"
download https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin "$K/voices-v1.0.bin"

echo "[2/4] Image model for OpenVINO (LCM Dreamshaper v7 INT8 + TAESD decoder, ~1 GB)"
(cd "$ROOT/backend" && uv sync && (.venv/bin/opt_in_out --opt_out >/dev/null 2>&1 || true) \
  && uv run python ../infrastructure/scripts/fetch_image_model.py)

if [[ $SKIP_OLLAMA -eq 0 ]]; then
  echo "[3/4] Ollama + $MODEL"
  if ! command -v ollama >/dev/null; then
    if [[ "$(uname)" == "Darwin" ]]; then echo "Install Ollama from https://ollama.com/download/mac then re-run."; exit 1; fi
    curl -fsSL https://ollama.com/install.sh | sh
  fi
  (OLLAMA_HOST=127.0.0.1:11434 ollama serve >/dev/null 2>&1 &) ; sleep 4
  ollama pull "$MODEL"
fi

if [[ $WITH_COMFY -eq 1 ]]; then
  echo "[4/4] ComfyUI + SD1.5 + LCM-LoRA"
  C="$RUNTIME/ComfyUI"
  [[ -d "$C" ]] || git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git "$C"
  (cd "$C" && [[ -d .venv ]] || uv venv --python 3.13 .venv)
  if command -v nvidia-smi >/dev/null; then IDX=https://download.pytorch.org/whl/cu128
  elif [[ "$(uname)" == "Darwin" ]]; then IDX=https://pypi.org/simple   # Apple Silicon uses MPS from the default wheels
  else IDX=https://download.pytorch.org/whl/cpu; fi
  uv pip install --python "$C/.venv" torch torchvision torchaudio --index-url "$IDX"
  uv pip install --python "$C/.venv" -r "$C/requirements.txt"
  download https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors \
    "$C/models/checkpoints/v1-5-pruned-emaonly.safetensors"
  download https://huggingface.co/latent-consistency/lcm-lora-sdv1-5/resolve/main/pytorch_lora_weights.safetensors \
    "$C/models/loras/lcm-lora-sdv1-5.safetensors"
fi
echo "Done. Start services with infrastructure/scripts/start-ai.sh"
