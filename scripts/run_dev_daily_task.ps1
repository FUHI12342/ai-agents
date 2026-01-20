$ErrorActionPreference = "Stop"
Set-Location "C:\Users\FHiro\Projects\ai-agents-dev"

$env:ENV = "dev"
$env:TRADER_DOTENV_PATH = ".env.dev"
$env:TRADER_MODE = "paper"
$env:TRADER_EXCHANGE_ENV = "testnet"
$env:TRADER_ALLOWED_SYMBOLS = "BTCUSDT"
$env:PYTHONUTF8 = "1"
$env:TRADER_DATA_DIR = "D:\ai-data\trader-dev\data"
$env:TRADER_REPORTS_DIR = "D:\ai-data\trader-dev\reports"
$env:TRADER_LOG_DIR = "D:\ai-data\trader-dev\logs"
$env:TRADER_STATE_DIR = "D:\ai-data\trader-dev\state"

$secretsPath = Join-Path $PSScriptRoot "secrets.local.ps1"
if (Test-Path $secretsPath) {
    . "$secretsPath"
}

try {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "run_dev_daily.ps1")
} catch {
    Write-Host $_.Exception.Message
    exit 3
}
