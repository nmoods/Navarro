#!/usr/bin/env bash
# Start local AI services bound to localhost only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNTIME="$ROOT/.runtime"; mkdir -p "$RUNTIME/logs"
if command -v ollama >/dev/null; then
  OLLAMA_HOST=127.0.0.1:11434 nohup ollama serve >"$RUNTIME/logs/ollama.log" 2>&1 &
  echo "Ollama  -> http://127.0.0.1:11434"
fi
C="$RUNTIME/ComfyUI"
if [[ -x "$C/.venv/bin/python" ]]; then
  FLAGS=(--listen 127.0.0.1 --port 8188 --disable-auto-launch)
  command -v nvidia-smi >/dev/null || [[ "$(uname)" == "Darwin" ]] || FLAGS+=(--cpu)
  (cd "$C" && nohup .venv/bin/python main.py "${FLAGS[@]}" >"$RUNTIME/logs/comfyui.log" 2>&1 &)
  echo "ComfyUI -> http://127.0.0.1:8188"
fi
