param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)

# --- script path resolve (StrictMode-safe) ---
$scriptPath = $null
if ($PSCommandPath) { $scriptPath = $PSCommandPath }
elseif ($MyInvocation -and $MyInvocation.MyCommand -and $MyInvocation.MyCommand.Path) { $scriptPath = $MyInvocation.MyCommand.Path }
if (-not $scriptPath) { throw "Cannot determine script path." }

$scriptDir   = Split-Path -Parent $scriptPath
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
Set-Location -Path $projectRoot

$python    = Join-Path $projectRoot ".venv\Scripts\python.exe"
$dailyRun  = Join-Path $scriptDir "daily_run.ps1"
$logDir    = Join-Path $scriptDir "logs"
$reportDir = Join-Path $projectRoot "trader\reports"
$bodyDir   = Join-Path $projectRoot "reports"

New-Item -ItemType Directory -Force -Path $logDir    | Out-Null
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
New-Item -ItemType Directory -Force -Path $bodyDir   | Out-Null

function Write-Log([string]$m) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] $m"
}

function Get-LatestFile([string]$dir, [string]$pattern) {
    $files = Get-ChildItem -LiteralPath $dir -Filter $pattern -File | Sort-Object LastWriteTime -Descending
    if ($files) { return $files[0] }
    return $null
}

Write-Log "Starting smoke test for daily_run.ps1"

# Set dummy environment
$env:TRADER_MODE = "testnet"  # to check API configured
$env:BINANCE_TESTNET_API_KEY = "dummy"
$env:BINANCE_TESTNET_API_SECRET = "dummy"

# Clean up KILL_SWITCH and lock
$killSwitchPath = Join-Path $projectRoot "KILL_SWITCH"
$lockPath = Join-Path $scriptDir "daily_run.lock"
Remove-Item -LiteralPath $killSwitchPath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
Write-Log "CLEAN: removed KILL_SWITCH and lock if existed"

# Run daily_run.ps1 -NoMail
Write-Log "RUN: daily_run.ps1 -NoMail"
$proc = Start-Process -FilePath "powershell.exe" -ArgumentList ("-ExecutionPolicy", "Bypass", "-File", "`"$dailyRun`"", "-NoMail") -Wait -PassThru -NoNewWindow
$rcNoMail = $proc.ExitCode
Write-Log "RC: $rcNoMail"

# Get latest files
$latestLog = Get-LatestFile $logDir "daily_run_*.log"
$latestBody = Get-LatestFile $bodyDir "daily_body_*.txt"
if (-not $latestLog) { throw "No daily_run log found" }
if (-not $latestBody) { throw "No daily_body found" }
Write-Log "Latest log: $($latestLog.FullName)"
Write-Log "Latest body: $($latestBody.FullName)"

# Check expectations
$failures = @()

# 1. daily_body 先頭20行に WARNING: API_NOT_CONFIGURED
$bodyLines = Get-Content -LiteralPath $latestBody.FullName -TotalCount 20
$hasWarning = $bodyLines -contains "WARNING: API_NOT_CONFIGURED"
if (-not $hasWarning) {
    $failures += "Body does not contain WARNING: API_NOT_CONFIGURED in first 20 lines"
}

# 2. SKIPPED: の次行に timestamp: がある（改行あり）
$bodyContent = Get-Content -LiteralPath $latestBody.FullName -Raw
Write-Log "Body content length: $($bodyContent.Length)"
$skippedPattern = [regex]::new("SKIPPED:\s*\r?\n\s*timestamp:", [System.Text.RegularExpressions.RegexOptions]::Multiline)
if (-not $skippedPattern.IsMatch($bodyContent)) {
    $failures += "Body does not have SKIPPED with timestamp on next line"
}

# 3. log に OK: sent（NoMail時は無し）
$logContent = Get-Content -LiteralPath $latestLog.FullName -Raw
$hasSent = $logContent -match "OK:\s*sent"
if ($hasSent) {
    $failures += "Log contains OK: sent but should not (NoMail mode)"
}

# 4. log に RC_SUMMARY
$hasRcSummary = $logContent -match "RC_SUMMARY:"
if (-not $hasRcSummary) {
    $failures += "Log does not contain RC_SUMMARY"
}

# 5. paper_yahoo が FAIL のとき summary_latest に ERROR: などが入っている（既に FAIL 上書きされているはず）
$paperYahooSummary = Join-Path $reportDir "paper_yahoo_summary_latest.txt"
if (Test-Path -LiteralPath $paperYahooSummary) {
    $summaryContent = Get-Content -LiteralPath $paperYahooSummary -Raw
    $hasError = $summaryContent -match "ERROR:"
    if (-not $hasError) {
        $failures += "paper_yahoo_summary_latest.txt does not contain ERROR:"
    }
} else {
    $failures += "paper_yahoo_summary_latest.txt not found"
}

# Run daily_run.ps1 (without -NoMail)
Write-Log "RUN: daily_run.ps1 (with mail)"
$proc = Start-Process -FilePath "powershell.exe" -ArgumentList ("-ExecutionPolicy", "Bypass", "-File", "`"$dailyRun`"") -Wait -PassThru -NoNewWindow
$rcMail = $proc.ExitCode
Write-Log "RC: $rcMail"

# Get latest log again
$latestLog2 = Get-LatestFile $logDir "daily_run_*.log"
if ($latestLog2 -and ($latestLog2.FullName -ne $latestLog.FullName)) {
    $logContent2 = Get-Content -LiteralPath $latestLog2.FullName -Raw
    $hasSent2 = $logContent2 -match "OK:\s*sent"
    if (-not $hasSent2) {
        $failures += "Log does not contain OK: sent (with mail)"
    }
    $hasRcSummary2 = $logContent2 -match "RC_SUMMARY:"
    if (-not $hasRcSummary2) {
        $failures += "Log does not contain RC_SUMMARY (with mail)"
    }
} else {
    $failures += "New log not generated for mail run"
}

# Check lock behavior
Write-Log "CHECK: lock exists -> exit 0"
# Create lock
$lockContent = "pid=test`nstart=$(Get-Date -Format o)"
[System.IO.File]::WriteAllText($lockPath, $lockContent, (New-Object System.Text.UTF8Encoding($false)))
$proc = Start-Process -FilePath "powershell.exe" -ArgumentList ("-ExecutionPolicy", "Bypass", "-File", "`"$dailyRun`"") -Wait -PassThru -NoNewWindow
$rcLock = $proc.ExitCode
if ($rcLock -ne 0) {
    $failures += "Lock exists but did not exit 0, rc=$rcLock"
}
Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue

# Report
if ($failures) {
    Write-Log "Failures: $($failures -join '; ')"
    Write-Error "Smoke test FAILED:"
    foreach ($f in $failures) {
        Write-Error "- $f"
    }
    exit 1
} else {
    Write-Log "Smoke test PASSED"
    exit 0
}