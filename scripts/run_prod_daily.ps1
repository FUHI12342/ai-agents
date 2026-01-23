param([switch]$NoMail)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)

# Set working directory to repo root derived from script location
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -Path $repoRoot

# Environment validation - must be prod
if ($env:ENV -ne "prod") {
    throw "ERROR: ENV must be 'prod' for production execution, got: $env:ENV"
}

# Set TRADER environment variables with prod defaults if unset
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

$dataDir = $env:TRADER_DATA_DIR
$reportDir = $env:TRADER_REPORTS_DIR
$stateDir = $env:TRADER_STATE_DIR
$logDir = $env:TRADER_LOG_DIR

# Create directories
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir ("run_prod_daily_{0}.log" -f $ts)

# Start transcript logging
Start-Transcript -Path $logFile -Append

# Step tracking for diagnostics
$lastStep = "BOOT"

try {
    # Environment logging at startup
    Write-Host "[INFO] ENV=$env:ENV"
    Write-Host "[INFO] DATA_DIR=$dataDir"
    Write-Host "[INFO] REPORTS_DIR=$reportDir"
    Write-Host "[INFO] STATE_DIR=$stateDir"
    Write-Host "[INFO] LOG_DIR=$logDir"

    $python = ".venv\Scripts\python.exe"
    
    # Validate TRADER_ALLOWED_SYMBOLS is set
    if (-not $env:TRADER_ALLOWED_SYMBOLS) {
        throw "ERROR: TRADER_ALLOWED_SYMBOLS must be set for production execution"
    }
    
    # Parse TRADER_ALLOWED_SYMBOLS
    $symbols = $env:TRADER_ALLOWED_SYMBOLS -split '[,\s]+' | Where-Object { $_.Trim() -ne '' } | ForEach-Object { $_.Trim() }
    if ($symbols.Count -eq 0) {
        throw "ERROR: TRADER_ALLOWED_SYMBOLS contains no valid symbols"
    }
    
    # Exit codes for non-fatal steps
    $scorecardExitCode = 0
    $gateExitCode = 0
    
    # Market data update (using dev pattern)
    $lastStep = "MARKET_DATA"
    Write-Host "[STEP] Updating market data"
    & $python -m trader.download_market_data --symbols ($symbols -join ",") --start "2010-01-01" --strict
    if ($LASTEXITCODE -ne 0) { throw "Market data update failed" }

    # Paper simulation (using dev pattern)
    $lastStep = "PAPER_SIM"
    Write-Host "[STEP] Running paper simulation"
    & $python -m trader.run_paper_sim --capital "10000" --symbols ($symbols -join ",") --ma-short "20" --ma-long "100" --risk-pct "0.25" --fee-rate "0.0005" --slippage-bps "5" --timeframe "1h" --steps "500" --state-file (Join-Path $stateDir "paper_state.json") --out-dir $reportDir
    if ($LASTEXITCODE -ne 0) { throw "Paper simulation failed" }

    # ML pipeline (non-fatal)
    $lastStep = "ML_PIPELINE"
    Write-Host "[STEP] Running ML signals pipeline (non-fatal)"
    if (Test-Path "trader\ml_pipeline.py") {
        & $python -m trader.ml_pipeline
        if ($LASTEXITCODE -ne 0) { 
            Write-Host "[WARN] ML signals pipeline failed with exit code $LASTEXITCODE, continuing..."
        }
    } else {
        Write-Host "[INFO] ML pipeline not found, skipping"
    }

    # Operations scorecard (non-fatal)
    $lastStep = "OPS_SCORECARD"
    Write-Host "[STEP] Running operations scorecard (non-fatal)"
    & $python -m trader.ops_scorecard
    $scorecardExitCode = $LASTEXITCODE
    Write-Host "[INFO] ops_scorecard exit code: $scorecardExitCode"
    if ($scorecardExitCode -ne 0) { 
        Write-Host "[WARN] Operations scorecard failed with exit code $scorecardExitCode, continuing..."
    }

    # Operations gate (non-fatal)
    $lastStep = "OPS_GATE"
    Write-Host "[STEP] Running operations gate (non-fatal)"
    & $python -m trader.ops_gate
    $gateExitCode = $LASTEXITCODE
    Write-Host "[INFO] ops_gate exit code: $gateExitCode"
    if ($gateExitCode -ne 0) { 
        Write-Host "[WARN] Operations gate failed with exit code $gateExitCode, continuing..."
    }

    # Operations notify (must succeed unless -NoMail)
    $lastStep = "OPS_NOTIFY"
    if ($NoMail) {
        Write-Host "[STEP] Running operations notify (SKIP: -NoMail)"
        Write-Host "[INFO] ops_notify skipped due to -NoMail flag"
    } else {
        Write-Host "[STEP] Running operations notify"
        & $python -m trader.ops_notify
        if ($LASTEXITCODE -ne 0) { throw "Operations notify failed" }
    }

    # Copy files from repo reports to prod reports if they ended up in wrong location
    $repoReportsDir = Join-Path $repoRoot "trader\reports"
    if ((Test-Path $repoReportsDir) -and ($repoReportsDir -ne $reportDir)) {
        $filesToCopy = @("paper_summary_latest.txt", "paper_trades_latest.csv", "paper_trades_history.csv", "ops_notify_latest.json", "ops_notify_body_latest.txt")
        foreach ($file in $filesToCopy) {
            $srcPath = Join-Path $repoReportsDir $file
            if (Test-Path $srcPath) {
                $dstPath = Join-Path $reportDir $file
                Copy-Item -Path $srcPath -Destination $dstPath -Force
                Write-Host "[INFO] Copied $file from $repoReportsDir to $reportDir"
            }
        }
    }

    # Verify ops_notify files exist (unless -NoMail)
    if (-not $NoMail) {
        $opsJsonPath = Join-Path $reportDir "ops_notify_latest.json"
        $opsTextPath = Join-Path $reportDir "ops_notify_body_latest.txt"
        
        if (-not (Test-Path $opsJsonPath) -or -not (Test-Path $opsTextPath)) {
            Write-Host "[ERROR] ops_notify files not found after completion"
            Write-Host "[DIAG] last_step=$lastStep"
            Write-Host "[DIAG] transcript=$logFile"
            Write-Host "[ERROR] Report directory contents:"
            Get-ChildItem -Path $reportDir | Format-Table Name, Length, LastWriteTime
            throw "ops_notify files not generated: missing $(if (-not (Test-Path $opsJsonPath)) { 'ops_notify_latest.json' }) $(if (-not (Test-Path $opsTextPath)) { 'ops_notify_body_latest.txt' })"
        }
    }

    # Final exit code determination
    if ($scorecardExitCode -ne 0 -or $gateExitCode -ne 0) {
        Write-Host "[WARN] Some non-fatal steps failed: scorecard=$scorecardExitCode, gate=$gateExitCode"
        Write-Host "[INFO] Production daily run completed with warnings"
        exit 1
    } else {
        Write-Host "[INFO] Production daily run completed successfully"
        exit 0
    }

} catch {
    Write-Host "[ERROR] Production daily run failed: $_"
    Write-Host "[DIAG] last_step=$lastStep"
    Write-Host "[DIAG] transcript=$logFile"
    exit 1
} finally {
    Stop-Transcript
}