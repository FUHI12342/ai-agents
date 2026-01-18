$ErrorActionPreference = "Stop"

function Fail($msg) {
    Write-Error $msg
    exit 1
}

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\..\.."
Set-Location $repoRoot

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "[1/4] Checking Ollama version..."
try {
    $version = Invoke-RestMethod "http://localhost:11434/api/version" -TimeoutSec 5
    Write-Host "Ollama version:" $version.version
} catch {
    Fail "Ollama version check failed: $_"
}

Write-Host "[2/4] Listing Ollama models..."
try {
    & ollama list
} catch {
    Fail "ollama list failed: $_"
}

Write-Host "[3/4] Running Compack diagnostics..."
try {
    & $python -m apps.compack.main --diagnose --mode text
} catch {
    Fail "Compack diagnose failed. Ensure dependencies are installed."
}

Write-Host "[4/4] Running Compack single-turn text session..."
try {
    $input = "Hello`n/quit`n"
    $input | & $python -m apps.compack.main --mode text
} catch {
    Fail "Compack text session failed."
}

Write-Host "[OK] Smoke test completed."
