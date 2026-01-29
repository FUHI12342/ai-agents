param(
  [string]$TaskName = "ai-agents_daily_run_2300",
  [string]$ProjectRoot = "C:\Users\FHiro\Projects\ai-agents"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve reports dir (env wins)
if (-not $reportDir -or [string]::IsNullOrWhiteSpace($reportDir)) {
  $reportDir = $env:TRADER_REPORTS_DIR
}

# If still empty, ask python config (last resort)
if (-not $reportDir -or [string]::IsNullOrWhiteSpace($reportDir)) {
  try {
    $reportDir = (python -c "from trader.config import REPORTS_DIR; print(REPORTS_DIR)" 2>$null).Trim()
  } catch { }
}

# Final fallback to repo default
if (-not $reportDir -or [string]::IsNullOrWhiteSpace($reportDir)) {
  $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  $reportDir = Join-Path $projectRoot "trader\reports"
}

New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
Write-Host "[INFO] REPORTS_DIR=$reportDir"

function Say($s){ Write-Host $s }

Say "=== VERIFY OPS GUARD ==="
Say "Root: $ProjectRoot"
cd $ProjectRoot

# venv activate (best-effort)
$act = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $act) { . $act; Say "VENV: activated" } else { Say "VENV: Activate.ps1 not found (skip)" }

# helper: latest log
function Latest-Log {
  $log = Get-ChildItem ".\scripts\logs\daily_run_*.log" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Desc | Select-Object -First 1
  return $log
}

# helper: grep
function Grep($path, $pat){
  Select-String -Path $path -Pattern $pat -Context 0,2 -ErrorAction SilentlyContinue
}

Say "`n[1] Safe run (NoMail)"
powershell -ExecutionPolicy Bypass -File .\scripts\daily_run.ps1 -NoMail
Say ("EXITCODE(NoMail)={0}" -f $LASTEXITCODE)

$log = Latest-Log
if (-not $log) { throw "No daily_run log found." }
Say ("LOG: {0}" -f $log.FullName)

Say "`n[2] STEP list"
Grep $log.FullName "^\[STEP\]"

Say "`n[3] Guard signals"
Grep $log.FullName "\[GUARD\]|\[WARN\]|\[ERROR\]|\[SKIP\]"

Say "`n[4] Paper outputs exist?"
$paperSummary = Join-Path $reportDir "paper_summary_latest.txt"
$paperLatest  = Join-Path $reportDir "paper_trades_latest.csv"
$paperHist    = Join-Path $reportDir "paper_trades_history.csv"
Say ("paper_summary_latest.txt : {0}" -f (Test-Path $paperSummary))
Say ("paper_trades_latest.csv  : {0}" -f (Test-Path $paperLatest))
Say ("paper_trades_history.csv : {0}" -f (Test-Path $paperHist))

Say "`n[4b] Live outputs exist?"
$liveSummary = Join-Path $reportDir "live_summary_latest.txt"
$reconcileLatest = Join-Path $reportDir "reconcile_latest.txt"
$gonogoLatest = Join-Path $reportDir "go_nogo_latest.txt"
Say ("live_summary_latest.txt : {0}" -f (Test-Path $liveSummary))
Say ("reconcile_latest.txt    : {0}" -f (Test-Path $reconcileLatest))
Say ("go_nogo_latest.txt      : {0}" -f (Test-Path $gonogoLatest))

Say "`n[5] KILL_SWITCH behavior (NoMail)"
$ks = Join-Path $ProjectRoot "KILL_SWITCH"
if (Test-Path $ks) { Remove-Item -Force $ks; Say "KILL_SWITCH removed for baseline test." }

Say " - baseline run (should run paper + cleanup)"
powershell -ExecutionPolicy Bypass -File .\scripts\daily_run.ps1 -NoMail
Say ("EXITCODE={0}" -f $LASTEXITCODE)

New-Item -ItemType File -Force -Path $ks | Out-Null
Say " - KILL_SWITCH ON (should skip guarded sections per your implementation)"
powershell -ExecutionPolicy Bypass -File .\scripts\daily_run.ps1 -NoMail
Say ("EXITCODE={0}" -f $LASTEXITCODE)

Remove-Item -Force $ks
Say " - KILL_SWITCH OFF (restore)"
powershell -ExecutionPolicy Bypass -File .\scripts\daily_run.ps1 -NoMail
Say ("EXITCODE={0}" -f $LASTEXITCODE)

$log = Latest-Log
Say ("LOG(after KILL_SWITCH tests): {0}" -f $log.FullName)
Say " - grep KILL_SWITCH / lock / cleanup / live"
Grep $log.FullName "KILL_SWITCH|lock|ops_cleanup|paper_trade_sim|live_trade_run|reconcile_live"

Say "`n[6] ScheduledTask run"
Say ("TaskName: {0}" -f $TaskName)
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5
Get-ScheduledTaskInfo -TaskName $TaskName | Format-List LastRunTime,LastTaskResult

$log = Latest-Log
Say ("LOG(after task): {0}" -f $log.FullName)
Say " - grep paper + live + cleanup + rc summary"
Grep $log.FullName "\[STEP\] paper_trade_sim|\[STEP\] live_trade_run|\[STEP\] reconcile_live|\[STEP\] ops_cleanup|\[INFO\] RC_SUMMARY"

Say "`nDONE. If anything fails, paste the error + latest log path shown above."