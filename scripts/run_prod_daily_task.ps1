Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Set working directory to repo root derived from script location
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -Path $repoRoot

# Environment validation - must be prod
if (-not $env:ENV) {
    $env:ENV = "prod"
}
if ($env:ENV -ne "prod") {
    throw "ERROR: ENV must be 'prod' for production execution, got: $env:ENV"
}

# Set TRADER environment variables only if unset (no override)
if (-not $env:TRADER_DATA_DIR) {
    $env:TRADER_DATA_DIR = "D:\ai-data\trader\data"
}
if (-not $env:TRADER_REPORTS_DIR) {
    $env:TRADER_REPORTS_DIR = "D:\ai-data\trader\reports"
}
if (-not $env:TRADER_STATE_DIR) {
    $env:TRADER_STATE_DIR = "D:\ai-data\trader\state"
}
if (-not $env:TRADER_LOG_DIR) {
    $env:TRADER_LOG_DIR = "D:\ai-data\trader\logs"
}
if (-not $env:TRADER_DOTENV_PATH) {
    $env:TRADER_DOTENV_PATH = ".env.prod"
}

# Display environment variables at startup
Write-Host "[INFO] ENV=$env:ENV"
Write-Host "[INFO] TRADER_DATA_DIR=$env:TRADER_DATA_DIR"
Write-Host "[INFO] TRADER_REPORTS_DIR=$env:TRADER_REPORTS_DIR"
Write-Host "[INFO] TRADER_STATE_DIR=$env:TRADER_STATE_DIR"
Write-Host "[INFO] TRADER_LOG_DIR=$env:TRADER_LOG_DIR"

# Call main production script
Write-Host "[INFO] Calling main production script..."
$scriptPath = Join-Path $PSScriptRoot "run_prod_daily.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File $scriptPath
exit $LASTEXITCODE