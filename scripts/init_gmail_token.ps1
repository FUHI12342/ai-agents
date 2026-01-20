$ErrorActionPreference = "Stop"
Set-Location "C:\Users\FHiro\Projects\ai-agents-dev"

$secretsPath = Join-Path $PSScriptRoot "secrets.local.ps1"
if (Test-Path $secretsPath) {
    . "$secretsPath"
} else {
    Write-Host "secrets.local.ps1 not found. Copy scripts\\secrets.local.ps1.example and fill GMAIL_* values."
    exit 1
}

$required = @("GMAIL_SENDER", "GMAIL_TO", "GMAIL_CREDENTIALS_PATH", "GMAIL_TOKEN_PATH")
$missing = @()
foreach ($k in $required) {
    $val = (Get-Item "Env:$k" -ErrorAction SilentlyContinue)
    if (-not $val) { $missing += $k }
}
if ($missing.Count -gt 0) {
    Write-Host "Missing env: $($missing -join ', ')"
    exit 1
}

$credPath = $env:GMAIL_CREDENTIALS_PATH
$tokenPath = $env:GMAIL_TOKEN_PATH
if (-not (Test-Path $credPath)) {
    Write-Host "credentials.json not found at $credPath"
    exit 1
}
$tokenDir = Split-Path -Parent $tokenPath
if (-not (Test-Path $tokenDir)) {
    New-Item -ItemType Directory -Force -Path $tokenDir | Out-Null
}

python -m trader.notify.gmail_sender --sender $env:GMAIL_SENDER --to $env:GMAIL_TO `
  --credentials $credPath --token $tokenPath --init-only
exit $LASTEXITCODE
