# Starts the local AI services bound to 127.0.0.1 only (never exposed to the network).
#   powershell -ExecutionPolicy Bypass -File infrastructure\scripts\start-ai.ps1
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
$Runtime = Join-Path $Root ".runtime"
$Logs = Join-Path $Runtime "logs"
New-Item -ItemType Directory -Force $Logs | Out-Null

$ollama = Join-Path $Runtime "ollama\ollama.exe"
if (Test-Path $ollama) {
    $env:OLLAMA_MODELS = Join-Path $Runtime "ollama-models"
    $env:OLLAMA_HOST = "127.0.0.1:11434"
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden `
        -RedirectStandardOutput "$Logs\ollama.out.log" -RedirectStandardError "$Logs\ollama.err.log"
    Write-Host "Ollama   -> http://127.0.0.1:11434"
} else { Write-Warning "Ollama not installed (run setup-ai.ps1)" }

$comfy = Join-Path $Runtime "ComfyUI"
if (Test-Path "$comfy\.venv\Scripts\python.exe") {
    $gpu = [bool](Get-Command nvidia-smi -ErrorAction SilentlyContinue)
    $comfyArgs = @("main.py", "--listen", "127.0.0.1", "--port", "8188", "--disable-auto-launch")
    if (-not $gpu) { $comfyArgs += "--cpu" }
    Start-Process -FilePath "$comfy\.venv\Scripts\python.exe" -ArgumentList $comfyArgs -WorkingDirectory $comfy -WindowStyle Hidden `
        -RedirectStandardOutput "$Logs\comfyui.out.log" -RedirectStandardError "$Logs\comfyui.err.log"
    Write-Host "ComfyUI  -> http://127.0.0.1:8188 ($(if ($gpu) {'GPU'} else {'CPU'}) mode)"
} else { Write-Warning "ComfyUI not installed (run setup-ai.ps1)" }
