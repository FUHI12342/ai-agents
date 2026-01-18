$ErrorActionPreference = "Stop"

Write-Host "Setting up Compack environment..."
$repo = Resolve-Path "$PSScriptRoot\..\..\.."
Set-Location $repo

if (-Not (Test-Path ".venv")) {
    Write-Host "Creating virtualenv at .venv"
    python -m venv .venv
}

& .\.venv\Scripts\activate
python -m pip install --upgrade pip

Write-Host "Installing core requirements..."
pip install -r requirements-core.txt

Write-Host "Optional installs:"
Write-Host "  1) Audio (sounddevice/pygame): pip install -r requirements-audio.txt"
Write-Host "  2) TTS (pyttsx3): pip install -r requirements-tts.txt"
Write-Host "  3) Whisper (local): pip install -r requirements-whisper.txt"
Write-Host "  4) Web UI: pip install -r requirements-web.txt"
Write-Host ""
Write-Host "Setup complete. You can run apps/compack/scripts/windows/Compack.bat to start."
