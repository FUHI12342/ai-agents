Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -Path $repoRoot

if (-not $env:ENV) {
    $env:ENV = "prod"
    Write-Host "[INFO] ENV not set, defaulting to prod"
}
if ($env:ENV -ne "prod") {
    throw "ERROR: ENV must be 'prod' for production execution, got: $env:ENV"
}

Write-Host "[INFO] ENV validation passed: $env:ENV"

function Set-EnvIfEmpty([string]$Name, [string]$Value) {
    $item = Get-Item -Path "Env:$Name" -ErrorAction SilentlyContinue
    $cur = if ($item) { $item.Value } else { $null }
    if ([string]::IsNullOrWhiteSpace($cur)) {
        Set-Item -Path "Env:$Name" -Value $Value
        Write-Host "[INFO] $Name set to: $Value"
    } else {
        Write-Host "[INFO] $Name already set: $cur"
    }
}

Set-EnvIfEmpty "TRADER_DATA_DIR"   "D:\ai-data\trader\data"
Set-EnvIfEmpty "TRADER_REPORTS_DIR" "D:\ai-data\trader\reports"
Set-EnvIfEmpty "TRADER_STATE_DIR"  "D:\ai-data\trader\state"
Set-EnvIfEmpty "TRADER_LOG_DIR"    "D:\ai-data\trader\logs"
Set-EnvIfEmpty "TRADER_DOTENV_PATH" ".env.prod"

Write-Host "[INFO] Calling main production script..."
$main = Join-Path $PSScriptRoot "run_prod_daily.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File $main
exit $LASTEXITCODE
