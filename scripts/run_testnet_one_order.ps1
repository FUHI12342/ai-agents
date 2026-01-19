# Testnet One Order Script
# Places a single minimum notional limit order on testnet for validation

param(
    [string]$Symbol = "BTCUSDT",
    [string]$Side = "buy",
    [double]$MinNotional = 5.0,
    [double]$PriceOffsetBps = 5.0,
    [int]$MaxWaitSec = 60
)

# Activate venv
$venvPath = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
} else {
    Write-Host "[ERROR] Virtual environment not found at $venvPath"
    exit 1
}

# Set environment variables
$env:TRADER_MODE = "testnet"
$env:TRADER_DRY_RUN = "false"
$env:TRADER_ALLOW_MARKET = "false"
$env:TRADER_SYMBOLS = $Symbol
$env:TRADER_TESTNET_MIN_NOTIONAL_QUOTE = $MinNotional
$env:TRADER_TESTNET_PRICE_OFFSET_BPS = $PriceOffsetBps
$env:TRADER_TESTNET_MAX_WAIT_SEC = $MaxWaitSec

# Check KILL_SWITCH
$killSwitchPath = ".\KILL_SWITCH"
if (Test-Path $killSwitchPath) {
    Write-Host "[SKIP] KILL_SWITCH present: $killSwitchPath"
    exit 0
}

# Run the Python module
Write-Host "[START] Running testnet one order..."
& python -m trader.testnet_one_order --symbol $Symbol --side $Side --min-notional $MinNotional --price-offset-bps $PriceOffsetBps

$exitCode = $LASTEXITCODE
Write-Host "[DONE] Exit code: $exitCode"

if ($exitCode -ne 0) {
    Write-Host "[ERROR] Testnet one order failed"
    exit 1
} else {
    Write-Host "[SUCCESS] Testnet one order completed"
    exit 0
}