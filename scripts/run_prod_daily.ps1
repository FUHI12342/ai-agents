param([switch]$NoMail)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -Path $repoRoot

if ($env:ENV -ne "prod") {
    throw "ERROR: ENV must be 'prod' for production execution, got: $env:ENV"
}

function Set-EnvIfEmpty([string]$Name, [string]$Value) {
    $item = Get-Item -Path "Env:$Name" -ErrorAction SilentlyContinue
    $cur = if ($item) { $item.Value } else { $null }
    if ([string]::IsNullOrWhiteSpace($cur)) {
        Set-Item -Path "Env:$Name" -Value $Value
    }
}

Set-EnvIfEmpty "TRADER_DATA_DIR"   "D:\ai-data\trader\data"
Set-EnvIfEmpty "TRADER_REPORTS_DIR" "D:\ai-data\trader\reports"
Set-EnvIfEmpty "TRADER_STATE_DIR"  "D:\ai-data\trader\state"
Set-EnvIfEmpty "TRADER_LOG_DIR"    "D:\ai-data\trader\logs"

$dataDir  = $env:TRADER_DATA_DIR
$reportDir = $env:TRADER_REPORTS_DIR
$stateDir = $env:TRADER_STATE_DIR
$logDir   = $env:TRADER_LOG_DIR

New-Item -ItemType Directory -Force -Path $dataDir  | Out-Null
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir   | Out-Null

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir ("run_prod_daily_{0}.log" -f $ts)

Start-Transcript -Path $logFile -Append

try {
    Write-Host "[INFO] ENV=$env:ENV"
    Write-Host "[INFO] DATA_DIR=$dataDir"
    Write-Host "[INFO] REPORTS_DIR=$reportDir"
    Write-Host "[INFO] STATE_DIR=$stateDir"
    Write-Host "[INFO] LOG_DIR=$logDir"

    $python = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) { $python = "python" }

    $symbolsRaw = $env:TRADER_ALLOWED_SYMBOLS
    if ([string]::IsNullOrWhiteSpace($symbolsRaw)) {
        throw "TRADER_ALLOWED_SYMBOLS is required"
    }
    $symbols = $symbolsRaw -split '[, ]+' | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() }

    Write-Host "[STEP] Updating market data"
    & $python -m trader.download_market_data --symbols @($symbols) --start "2024-01-01"
    if ($LASTEXITCODE -ne 0) { throw "Market data update failed" }

    Write-Host "[STEP] Running paper simulation"
    & $python -m trader.run_paper_sim
    if ($LASTEXITCODE -ne 0) { throw "Paper simulation failed" }

    Write-Host "[STEP] Running ML signals pipeline (non-fatal)"
    & $python -m trader.ml.pipeline
    if ($LASTEXITCODE -ne 0) { Write-Host "[WARN] ML pipeline failed (ignored)" }

    Write-Host "[STEP] Running operations scorecard"
    & $python -m trader.ops_scorecard
    if ($LASTEXITCODE -ne 0) { throw "Operations scorecard failed" }

    Write-Host "[STEP] Running operations gate"
    & $python -m trader.ops_gate
    if ($LASTEXITCODE -ne 0) { throw "Operations gate failed" }

    if (-not $NoMail) {
        Write-Host "[STEP] Running operations notify"
        & $python -m trader.ops_notify
        if ($LASTEXITCODE -ne 0) { throw "Operations notify failed" }
    }

    Write-Host "[INFO] Production daily run completed successfully"
    exit 0
} catch {
    Write-Host "[ERROR] Production daily run failed: $_"
    exit 1
} finally {
    Stop-Transcript
}
