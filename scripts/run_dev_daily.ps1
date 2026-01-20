$ErrorActionPreference = "Stop"
Set-Location "C:\Users\FHiro\Projects\ai-agents-dev"

$venv = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venv) {
    . $venv
}

$logDir = $env:TRADER_LOG_DIR
if (-not $logDir) { $logDir = ".\logs" }
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDir "run_dev_daily_$stamp.log"

$summary = @{
    date = (Get-Date -Format s)
    eval_days = $null
    daily_coverage_count = $null
    skipped_reason = $null
    score_exit = $null
    score_pass = $false
    gate_ran = $false
    gate_exit = $null
    gate_pass = $false
    notify_attempted = $false
    notify_sent = $false
}
$main_exit = 0

try {
    Start-Transcript -Path $logPath -Append
} catch {}

function Write-Heartbeat($exitCode, $summaryObj) {
    $reportsDir = $env:TRADER_REPORTS_DIR
    if (-not $reportsDir) { $reportsDir = ".\reports" }
    New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null
    $heartbeat = @{
        finished_at_local = (Get-Date -Format o)
        finished_at_utc   = (Get-Date).ToUniversalTime().ToString("o")
        main_exit = $exitCode
        eval_days = $summaryObj.eval_days
        daily_coverage_count = $summaryObj.daily_coverage_count
        skipped_reason = $summaryObj.skipped_reason
        score_pass = $summaryObj.score_pass
        gate_pass = $summaryObj.gate_pass
        notify_attempted = $summaryObj.notify_attempted
        notify_sent = $summaryObj.notify_sent
    }
    $heartbeatPath = Join-Path $reportsDir "ops_heartbeat_latest.json"
    try {
        ($heartbeat | ConvertTo-Json -Depth 4) | Out-File -FilePath $heartbeatPath -Encoding utf8
    } catch {}
}

try {
    $dataDir = $env:TRADER_DATA_DIR
    if (-not $dataDir) { $dataDir = ".\data" }
    $reportsDir = $env:TRADER_REPORTS_DIR
    if (-not $reportsDir) { $reportsDir = ".\reports" }
    $logsDir = $env:TRADER_LOG_DIR
    if (-not $logsDir) { $logsDir = ".\logs" }
    $stateDir = $env:TRADER_STATE_DIR
    if (-not $stateDir) { $stateDir = ".\state" }

    # Determine eval window
    $windowJson = python -m trader.ops_window --data-dir $dataDir --max-days 7
    $window = $windowJson | ConvertFrom-Json
    $summary.eval_days = $window.eval_days
    $summary.daily_coverage_count = $window.coverage_count
    if ($summary.eval_days -eq $null) {
        Write-Host "[INFO] Not enough daily files; skipping score/gate/notify."
        $summary.skipped_reason = "insufficient_coverage"
        $summaryPath = Join-Path $reportsDir "ops_autorun_latest.json"
        ($summary | ConvertTo-Json -Depth 4) | Out-File -FilePath $summaryPath -Encoding utf8
        Write-Heartbeat 0 $summary
        exit 0
    }

    $threshold = 70
    switch ($summary.eval_days) {
        3 { $threshold = 30 }
        4 { $threshold = 40 }
        5 { $threshold = 50 }
        6 { $threshold = 50 }
        default { $threshold = 70 }
    }

    Write-Host "[INFO] Updating market data (BTCUSDT, binance 1h)..."
    try {
        python -m trader.download_market_data --symbols BTCUSDT --binance-start 2024-01-01 --binance-timeframe 1h --strict
    } catch {
        Write-Host "[WARN] download_market_data failed: $($_.Exception.Message)"
    }

    Write-Host "[INFO] Running paper simulation (BTCUSDT)..."
    $stateFile = Join-Path $stateDir "paper_state_binance.json"
    try {
        python -m trader.run_paper_sim --symbols BTCUSDT --risk-pct 0.25 --out-dir $reportsDir --data-dir $dataDir --state-file $stateFile --steps 500 --timeframe 1h
    } catch {
        Write-Host "[WARN] run_paper_sim failed: $($_.Exception.Message)"
    }

    Write-Host "[INFO] Running ML signals pipeline (non-fatal)..."
    try {
        python -m trader.ml.pipeline --symbol BTCUSDT --interval 1h --k 6 --rebound-n 24 --rebound-pct 0.003 --last 2000
    } catch {
        Write-Host "[WARN] ML pipeline failed; continue"
    }

    python -m trader.ops_scorecard --days $summary.eval_days --threshold $threshold --reports-dir $reportsDir --data-dir $dataDir --logs-dir $logsDir
    $summary.score_exit = $LASTEXITCODE
    if ($LASTEXITCODE -eq 0) { $summary.score_pass = $true }

    if ($summary.score_pass) {
        $summary.gate_ran = $true
        python -m trader.ops_gate --days $summary.eval_days --max-guard 0 --reports-dir $reportsDir --data-dir $dataDir --logs-dir $logsDir
        $summary.gate_exit = $LASTEXITCODE
        if ($LASTEXITCODE -eq 0) { $summary.gate_pass = $true }
    }

    $summaryPath = Join-Path $reportsDir "ops_autorun_latest.json"
    ($summary | ConvertTo-Json -Depth 4) | Out-File -FilePath $summaryPath -Encoding utf8

    if ($summary.score_pass -and $summary.gate_pass -and $summary.gate_ran) {
        $summary.notify_attempted = $true
        try {
            python -m trader.ops_notify --autorun-json $summaryPath --scorecard-txt (Join-Path $reportsDir "ops_scorecard_latest.txt") --gate-txt (Join-Path $reportsDir "ops_gate_latest.txt")
            $notifyPath = Join-Path $reportsDir "ops_notify_latest.json"
            if (Test-Path $notifyPath) {
                $n = Get-Content $notifyPath -Raw | ConvertFrom-Json
                if ($n.sent -eq $true) { $summary.notify_sent = $true }
            }
        } catch {
            Write-Host "[WARN] ops_notify failed: $($_.Exception.Message)"
        }
    }
}
catch {
    Write-Host "[ERROR] $_"
    $main_exit = 3
}
finally {
    try {
        $reportsDir = $env:TRADER_REPORTS_DIR
        if (-not $reportsDir) { $reportsDir = ".\reports" }
        New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null
        $summaryPath = Join-Path $reportsDir "ops_autorun_latest.json"
        ($summary | ConvertTo-Json -Depth 4) | Out-File -FilePath $summaryPath -Encoding utf8
    } catch {}
    Write-Heartbeat $main_exit $summary
    try { Stop-Transcript | Out-Null } catch {}
    exit $main_exit
}
