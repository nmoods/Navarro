# ReelForge AI - full local AI setup for Windows (CPU or NVIDIA GPU).
# Installs everything under <repo>\.runtime (git-ignored). Nothing is installed system-wide.
#   powershell -ExecutionPolicy Bypass -File infrastructure\scripts\setup-ai.ps1 [-SkipComfy] [-SkipOllama] [-Model qwen3.5:4b]
param(
    [switch]$SkipComfy,
    [switch]$SkipOllama,
    [string]$Model = "qwen3.5:4b",
    [string]$OllamaVersion = "v0.40.15"
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
$Runtime = Join-Path $Root ".runtime"
New-Item -ItemType Directory -Force $Runtime | Out-Null

function Get-Uv {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) { return $uv.Source }
    $user = Join-Path ([Environment]::GetFolderPath("ApplicationData")) "Python"
    $found = Get-ChildItem -Path $user -Recurse -Filter uv.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { return $found.FullName }
    Write-Host "Installing uv (Python package manager)..."
    python -m pip install --user uv | Out-Null
    return (Get-ChildItem -Path $user -Recurse -Filter uv.exe | Select-Object -First 1).FullName
}

function Download($Url, $Dest) {
    if (Test-Path $Dest) { Write-Host "  exists: $Dest"; return }
    New-Item -ItemType Directory -Force (Split-Path $Dest) | Out-Null
    Write-Host "  downloading $Url"
    curl.exe -fL --retry 3 -o "$Dest.part" $Url
    if ($LASTEXITCODE -ne 0) { throw "Download failed: $Url" }
    Move-Item "$Dest.part" $Dest
}

$Uv = Get-Uv
& $Uv python install 3.13 | Out-Null

Write-Host "`n[1/3] Kokoro TTS worker (isolated GPL-3.0 process)"
Push-Location (Join-Path $Root "ai-engine\tts-worker"); & $Uv sync; Pop-Location
$K = Join-Path $Runtime "models\kokoro"
Download "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" "$K\kokoro-v1.0.onnx"
Download "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" "$K\voices-v1.0.bin"

if (-not $SkipOllama) {
    Write-Host "`n[2/3] Ollama $OllamaVersion (portable) + $Model"
    $O = Join-Path $Runtime "ollama"
    if (-not (Test-Path "$O\ollama.exe")) {
        $zip = Join-Path $Runtime "ollama-windows-amd64.zip"
        Download "https://github.com/ollama/ollama/releases/download/$OllamaVersion/ollama-windows-amd64.zip" $zip
        Expand-Archive -Force $zip $O
        Remove-Item $zip
    }
    $env:OLLAMA_MODELS = Join-Path $Runtime "ollama-models"
    $env:OLLAMA_HOST = "127.0.0.1:11434"
    $serve = Start-Process -FilePath "$O\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 4
    & "$O\ollama.exe" pull $Model
    if ($LASTEXITCODE -ne 0) { throw "ollama pull $Model failed" }
    Stop-Process -Id $serve.Id -ErrorAction SilentlyContinue
}

if (-not $SkipComfy) {
    Write-Host "`n[3/3] ComfyUI (GPL-3.0, separate process) + SD 1.5 + LCM-LoRA"
    $C = Join-Path $Runtime "ComfyUI"
    if (-not (Test-Path $C)) { git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git $C }
    Push-Location $C
    if (-not (Test-Path ".venv")) { & $Uv venv --python 3.13 .venv }
    $hasNvidia = [bool](Get-Command nvidia-smi -ErrorAction SilentlyContinue)
    $index = if ($hasNvidia) { "https://download.pytorch.org/whl/cu128" } else { "https://download.pytorch.org/whl/cpu" }
    Write-Host "  installing PyTorch from $index"
    & $Uv pip install --python .venv torch torchvision torchaudio --index-url $index
    & $Uv pip install --python .venv -r requirements.txt
    Pop-Location
    # Stable Diffusion 1.5 (CreativeML OpenRAIL-M: use restrictions apply, see docs/research/license-audit.md)
    Download "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors" "$C\models\checkpoints\v1-5-pruned-emaonly.safetensors"
    # LCM-LoRA for SD1.5 (OpenRAIL++): 4-8 step sampling, essential on CPU
    Download "https://huggingface.co/latent-consistency/lcm-lora-sdv1-5/resolve/main/pytorch_lora_weights.safetensors" "$C\models\loras\lcm-lora-sdv1-5.safetensors"
}

Write-Host "`nDone. Start the AI services with: infrastructure\scripts\start-ai.ps1"
