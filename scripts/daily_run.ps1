param([switch]$NoMail)

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
  $reportDir = Join-Path $projectRoot "trader\reports"
}

$python    = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logDir    = Join-Path $scriptDir "logs"
$bodyDir   = Join-Path $projectRoot "reports"

New-Item -ItemType Directory -Force -Path $logDir    | Out-Null
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
New-Item -ItemType Directory -Force -Path $bodyDir   | Out-Null

$ts    = Get-Date -Format "yyyyMMdd_HHmmss"
$today = Get-Date -Format "yyyyMMdd"
$logFile  = Join-Path $logDir  ("daily_run_{0}.log" -f $ts)
$bodyFile = Join-Path $bodyDir ("daily_body_{0}.txt" -f $ts)

function Write-Log([string]$m) { Add-Content -Path $logFile -Value $m -Encoding UTF8 }

function To-Int($v) {
  if ($null -eq $v) { return 0 }
  if ($v -is [array]) {
    if ($v.Count -eq 0) { return 0 }
    return [int]$v[-1]   # 陟｢・ｵ邵ｺ・ｮ邵ｺ貅假ｽ∫ｸｲ譴ｧ諤呵募ｾ後・髫補悪・ｴ・ｰ邵ｲ髦ｪ・定ｬ暦ｽ｡騾包ｽｨ
  }
  return [int]$v
}

# 隨倥・纃ｾ髫輔・・ｼ螢ｹ・・ｸｺ・ｮ鬮｢・｢隰ｨ・ｰ邵ｺ・ｯ邵ｲ譎ｯnt邵ｺ・ｰ邵ｺ莉｣ﾂ髦ｪ・定ｬ鯉ｽｻ邵ｺ蜻ｻ・ｼ蝓滂ｽｨ蜻趣ｽｺ髢繝ｻ陷牙ｸ吶・ Write-Host 邵ｺ・ｫ鬨ｾ繝ｻ窶ｲ邵ｺ蜻ｻ・ｼ繝ｻ
function Invoke-Exe([string]$step, [string]$exe, [string[]]$argv) {
  Write-Log ""
  Write-Log ("[STEP] {0}" -f $step)
  Write-Log ("[EXE ] {0}" -f $exe)
  Write-Log ("[ARGV] {0}" -f ($argv -join " "))

  if (-not (Test-Path -LiteralPath $exe)) {
    Write-Log ("[ERR ] exe not found: {0}" -f $exe)
    return 9009
  }

  $out = & {
    $ErrorActionPreference = "Continue"
    & $exe @argv 2>&1
  }
  $rc = [int]$LASTEXITCODE

  foreach ($line in $out) {
    if ($null -ne $line -and "$line" -ne "") { Write-Host $line }
    if ($null -ne $line) { Write-Log $line }
  }
  Write-Log ("[RC  ] {0}" -f $rc)
  return [int]$rc
}

# rc 陞溽判辟夂ｸｺ・ｯ陟｢繝ｻ笘・崕譎・ｄ陋ｹ繝ｻ
$rc_py = 0; $rc_data = 0; $rc_bt1 = 0; $rc_bt2 = 0; $rc_paper = 0; $rc_paper_yahoo = 0; $rc_live = 0; $rc_reconcile = 0; $rc_gonogo = 0; $rc_mail = 0

$lockPath = Join-Path $projectRoot "scripts\daily_run.lock"
$staleMinutes = 180

if (Test-Path -LiteralPath $lockPath) {
  $age = ((Get-Date) - (Get-Item -LiteralPath $lockPath).LastWriteTime).TotalMinutes
  if ($age -gt $staleMinutes) {
    Write-Log ("[GUARD] stale lock found ({0:N0} min). removing: {1}" -f $age, $lockPath)
    Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
  } else {
    Write-Log ("[GUARD] lock exists ({0:N0} min). another run is active. exit 0: {1}" -f $age, $lockPath)
    exit 0
  }
}

try {
  $fs = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
  $sw = New-Object System.IO.StreamWriter($fs)
  $sw.WriteLine("pid=$PID")
  $sw.WriteLine("start=$(Get-Date -Format o)")
  $sw.Flush()
  $sw.Dispose()
  $fs.Dispose()
  Write-Log ("[GUARD] lock acquired: {0}" -f $lockPath)
} catch {
  Write-Log ("[GUARD] failed to create lock (likely concurrent start). exit 0: {0}" -f $lockPath)
  exit 0
}

try {
  Write-Log ("[INFO] Start : {0}" -f (Get-Date))
  Write-Log ("[INFO] Script: {0}" -f $scriptPath)
  Write-Log ("[INFO] Root  : {0}" -f $projectRoot)
  Write-Log ("[INFO] Python: {0}" -f $python)
  Write-Log ("[ENV ] PSVersion: {0}" -f $PSVersionTable.PSVersion)
  Write-Log ("[ENV ] PSEdition: {0}" -f $PSVersionTable.PSEdition)

  $killSwitchPath = Join-Path $projectRoot "KILL_SWITCH"
  $killOn = Test-Path -LiteralPath $killSwitchPath
  if ($killOn) {
    Write-Log ("[GUARD] KILL_SWITCH present -> paper_trade_sim will be skipped. path={0}" -f $killSwitchPath)
  }

  # Get TRADER_MODE from config
  $traderMode = & $python -c "from trader.config import load_config; print(load_config().trader_mode)" 2>$null
  if (-not $traderMode) { $traderMode = "paper" }

  $rc_py = Invoke-Exe "python_version" $python @("--version")

  $rc_data = Invoke-Exe "download_market_data" $python @(
    "-m","trader.download_market_data",
    "--symbols","^GSPC","^N225","^IXIC","USDJPY=X",
    "--start","2010-01-01",
    "--strict"
  )

  $rc_bt1 = Invoke-Exe "backtest risk=0.25" $python @(
    "-m","trader.run_backtest_multi_assets",
    "--risk-pct","0.25",
    "--ma-short","20",
    "--ma-long","100",
    "--report-prefix","daily"
  )

  $rc_bt2 = Invoke-Exe "backtest risk=0.50" $python @(
    "-m","trader.run_backtest_multi_assets",
    "--risk-pct","0.50",
    "--ma-short","20",
    "--ma-long","100",
    "--report-prefix","daily"
  )

  if (-not $killOn) {
    $rc_paper = Invoke-Exe "paper_trade_sim" $python @(
      "-m","trader.run_paper_sim",
      "--capital","10000",
      "--symbols","BTCUSDT",
      "--ma-short","20","--ma-long","100",
      "--risk-pct","0.25",
      "--fee-rate","0.0005",
      "--slippage-bps","5",
      "--timeframe","1h",
      "--steps","500",
      "--state-file","D:\ai-data\paper_state.json",
      "--out-dir",$reportDir
    )
    # Generate paper execution summary
    $rc_paper_exec = Invoke-Exe "paper_execution_report" $python @(
      "-m","trader.paper_execution_report",
      "--state-file","D:\ai-data\paper_state.json",
      "--symbols","BTCUSDT",
      "--ma-short","20","--ma-long","100",
      "--risk-pct","0.25",
      "--jpy-per-usdt","150",
      "--out-dir",$reportDir
    )
  } else {
    Write-Log "[STEP] paper_trade_sim (SKIP: KILL_SWITCH)"
    $rc_paper = 0
  }

  if (-not $killOn) {
    $rc_paper_yahoo = Invoke-Exe "paper_yahoo_sim" $python @(
      "-m","trader.run_paper_sim_yahoo",
      "--symbols","^N225,USDJPY=X,^GSPC,^IXIC",
      "--capital-jpy","10000",
      "--ma-short","20","--ma-long","100",
      "--risk-pct","0.25",
      "--state-file","D:\ai-data\paper_state_yahoo.json",
      "--out-dir",$reportDir
    )
    if ($rc_paper_yahoo -ne 0) {
      # Overwrite summary with FAIL content
      $paperYahooSummary = Join-Path $reportDir "paper_yahoo_summary_latest.txt"
      "PaperYahoo Summary`nERROR: rc=$rc_paper_yahoo`n" | Out-File -FilePath $paperYahooSummary -Encoding UTF8
      # Overwrite trades with header only
      $paperYahooTrades = Join-Path $reportDir "paper_yahoo_trades_latest.csv"
      "time_iso,time_ms,symbol,side,price,qty,notional_quote,fee_quote,cash_quote_after,pos_base_after,equity_quote_after,equity_jpy_after,reason" | Out-File -FilePath $paperYahooTrades -Encoding UTF8
    }
  } else {
    Write-Log "[STEP] paper_yahoo_sim (SKIP: KILL_SWITCH)"
    $rc_paper_yahoo = 0
  }

  # Check API configured
  $isApiConfigured = & $python -c "from trader.config import load_config; print(load_config().is_api_configured())" 2>$null
  if ($isApiConfigured -ne "True") { $isApiConfigured = $false } else { $isApiConfigured = $true }

  # Auth smoke test
  $rc_auth_smoke = Invoke-Exe "auth_smoke" $python @("-m","trader.exchange_auth_smoke")

  # Live trade run
  if ($traderMode -eq "paper") {
    Write-Log "[STEP] live_trade_run (SKIP: mode=paper)"
    $rc_live = 0
    # Generate placeholder for live_summary_latest.txt
    $liveSummaryPath = Join-Path $reportDir "live_summary_latest.txt"
    $content = @"
Live Summary
----------------------------------------
SKIPPED: mode=paper
timestamp: $(Get-Date -Format o)
mode: $traderMode
dry_run: true
"@
    $content | Out-File -FilePath $liveSummaryPath -Encoding UTF8
  } elseif ($killOn) {
    Write-Log "[STEP] live_trade_run (SKIP: KILL_SWITCH)"
    $rc_live = 0
    # Generate placeholder for live_summary_latest.txt
    $liveSummaryPath = Join-Path $reportDir "live_summary_latest.txt"
    $content = @"
Live Summary
----------------------------------------
SKIPPED: KILL_SWITCH
timestamp: $(Get-Date -Format o)
mode: $traderMode
dry_run: true
"@
    $content | Out-File -FilePath $liveSummaryPath -Encoding UTF8
  } elseif (-not $isApiConfigured) {
    Write-Log "[STEP] live_trade_run (SKIP: api_not_configured)"
    $rc_live = 0
    # Generate placeholder for live_summary_latest.txt
    $liveSummaryPath = Join-Path $reportDir "live_summary_latest.txt"
    $content = @"
Live Summary
----------------------------------------
SKIPPED: api_not_configured
timestamp: $(Get-Date -Format o)
mode: $traderMode
dry_run: true
"@
    $content | Out-File -FilePath $liveSummaryPath -Encoding UTF8
  } else {
    $rc_live = Invoke-Exe "live_trade_run" $python @("-m","trader.run_live_trade")
  }

  # Reconcile live
  if ($traderMode -eq "paper") {
    Write-Log "[STEP] reconcile_live (SKIP: mode=paper)"
    $rc_reconcile = 0
    # Generate placeholder for reconcile_latest.txt and .json
    $reconcileTxtPath = Join-Path $reportDir "reconcile_latest.txt"
    $reconcileJsonPath = Join-Path $reportDir "reconcile_latest.json"
    $timestamp = Get-Date -Format o
    $reason = "SKIPPED_MODE_PAPER"
    $contentTxt = @"
Reconcile Summary
----------------------------------------
ok=false
reason=$reason
mode=$traderMode
timestamp=$timestamp
"@
    $contentTxt | Out-File -FilePath $reconcileTxtPath -Encoding UTF8
    $jsonObj = @{ok=$false; reason=$reason; mode=$traderMode; timestamp=$timestamp} | ConvertTo-Json -Compress
    $jsonObj | Out-File -FilePath $reconcileJsonPath -Encoding UTF8 -NoNewline
  } elseif ($killOn) {
    Write-Log "[STEP] reconcile_live (SKIP: KILL_SWITCH)"
    $rc_reconcile = 0
    # Generate placeholder for reconcile_latest.txt and .json
    $reconcileTxtPath = Join-Path $reportDir "reconcile_latest.txt"
    $reconcileJsonPath = Join-Path $reportDir "reconcile_latest.json"
    $timestamp = Get-Date -Format o
    $reason = "SKIPPED_KILL_SWITCH"
    $contentTxt = @"
Reconcile Summary
----------------------------------------
ok=false
reason=$reason
mode=$traderMode
timestamp=$timestamp
"@
    $contentTxt | Out-File -FilePath $reconcileTxtPath -Encoding UTF8
    $jsonObj = @{ok=$false; reason=$reason; mode=$traderMode; timestamp=$timestamp} | ConvertTo-Json -Compress
    $jsonObj | Out-File -FilePath $reconcileJsonPath -Encoding UTF8 -NoNewline
  } elseif (-not $isApiConfigured) {
    Write-Log "[STEP] reconcile_live (SKIP: api_not_configured)"
    $rc_reconcile = 0
    # Generate placeholder for reconcile_latest.txt and .json
    $reconcileTxtPath = Join-Path $reportDir "reconcile_latest.txt"
    $reconcileJsonPath = Join-Path $reportDir "reconcile_latest.json"
    $timestamp = Get-Date -Format o
    $reason = "SKIPPED_API_NOT_CONFIGURED"
    $contentTxt = @"
Reconcile Summary
----------------------------------------
ok=false
reason=$reason
mode=$traderMode
timestamp=$timestamp
"@
    $contentTxt | Out-File -FilePath $reconcileTxtPath -Encoding UTF8
    $jsonObj = @{ok=$false; reason=$reason; mode=$traderMode; timestamp=$timestamp} | ConvertTo-Json -Compress
    $jsonObj | Out-File -FilePath $reconcileJsonPath -Encoding UTF8 -NoNewline
  } else {
    $rc_reconcile = Invoke-Exe "reconcile_live" $python @("-m","trader.reconcile_live")
  }

  # Go/No-Go check
  $rc_gonogo = Invoke-Exe "go_nogo" $python @("-m","trader.go_nogo")

    # --- compose mail body & write file (no BOM) ---
  $body = @()
  # Self-diagnosis for Windows Task
  $taskInfo = Get-ScheduledTaskInfo -TaskName "ai-agents_daily_run_2300" -ErrorAction SilentlyContinue
  if ($taskInfo) {
    $lastRun = $taskInfo.LastRunTime
    $missed = $taskInfo.NumberOfMissedRuns
    $now = Get-Date
    $hoursSinceLastRun = if ($lastRun) { ($now - $lastRun).TotalHours } else { 999 }
    if ($hoursSinceLastRun -gt 36 -or $missed -gt 0) {
      $body += "WARNING: Task Issues - LastRun: $lastRun, MissedRuns: $missed"
      $body += ""
    }
  }
  # Add WARNING if API not configured
  if (-not $isApiConfigured) {
    $body += "WARNING: API_NOT_CONFIGURED"
    $body += "Set .env: BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET (mode=$traderMode)"
    $body += ""
  }
  $body += ("Daily Trader Report {0}" -f (Get-Date))
  $body += ""
  $body += "Status"
  $body += ("- python --version : {0}" -f $rc_py)
  $body += ("- data update      : {0}" -f $rc_data)
  $body += ("- backtest 0.25    : {0}" -f $rc_bt1)
  $body += ("- backtest 0.50    : {0}" -f $rc_bt2)
  $body += ("- paper sim        : {0}" -f $rc_paper)
  $body += ("- paper yahoo      : {0}" -f $rc_paper_yahoo)
  $body += ("- live trade       : {0}" -f $rc_live)
  $body += ("- reconcile live   : {0}" -f $rc_reconcile)
  $body += ("- go/no-go         : {0}" -f $rc_gonogo)
  $body += ("- kill switch      : {0}" -f ([int]$killOn))
  $body += ""
  $body += "Log file"
  $body += ("- {0}" -f $logFile)
  $body += ""
  $body += "Log tail (last 120 lines)"
  $body += "----------------------------------------"
  $tail = Get-Content -LiteralPath $logFile -Tail 120 -ErrorAction SilentlyContinue
  foreach ($t in $tail) { $body += $t }
  # --- PaperTrade Summary (optional) ---
  $paperSummary = Join-Path $reportDir "paper_summary_latest.txt"
  if (Test-Path -LiteralPath $paperSummary) {
    $body += ""
    $body += "PaperTrade Summary"
    $body += "----------------------------------------"
    $body += (Get-Content -LiteralPath $paperSummary -ErrorAction SilentlyContinue)
  } else {
    $body += ""
    $body += "PaperTrade Summary"
    $body += "- (paper_summary_latest.txt not found)"
  }

  # --- PaperYahoo Summary (optional) ---
  $paperYahooSummary = Join-Path $reportDir "paper_yahoo_summary_latest.txt"
  if (Test-Path -LiteralPath $paperYahooSummary) {
    $body += ""
    $body += "PaperYahoo Summary"
    $body += "----------------------------------------"
    $body += (Get-Content -LiteralPath $paperYahooSummary -ErrorAction SilentlyContinue)
  } else {
    $body += ""
    $body += "PaperYahoo Summary"
    $body += "- (paper_yahoo_summary_latest.txt not generated)"
  }

  # --- Auth Smoke Summary (optional) ---
  $authSmokeSummary = Join-Path $reportDir "auth_smoke_latest.txt"
  if (Test-Path -LiteralPath $authSmokeSummary) {
    $body += ""
    $body += "Auth Smoke Summary"
    $body += "----------------------------------------"
    $body += (Get-Content -LiteralPath $authSmokeSummary -ErrorAction SilentlyContinue)
  } else {
    $body += ""
    $body += "Auth Smoke Summary"
    $body += "- (auth_smoke_latest.txt not generated)"
  }

  # --- Live Summary (optional) ---
  $liveSummary = Join-Path $reportDir "live_summary_latest.txt"
  if (Test-Path -LiteralPath $liveSummary) {
    $body += ""
    $body += "Live Summary"
    $body += "----------------------------------------"
    $body += (Get-Content -LiteralPath $liveSummary -ErrorAction SilentlyContinue)
  } else {
    $body += ""
    $body += "Live Summary"
    $body += "- (live_summary_latest.txt not generated)"
  }

  # --- Reconcile Summary (optional) ---
  $reconcileSummary = Join-Path $reportDir "reconcile_latest.txt"
  if (Test-Path -LiteralPath $reconcileSummary) {
    $body += ""
    $body += "Reconcile Summary"
    $body += "----------------------------------------"
    $body += (Get-Content -LiteralPath $reconcileSummary -ErrorAction SilentlyContinue)
  } else {
    $body += ""
    $body += "Reconcile Summary"
    $body += "- (reconcile_latest.txt not generated)"
  }

  # --- Go/No-Go Summary (optional) ---
  $gonogoSummary = Join-Path $reportDir "go_nogo_latest.txt"
  if (Test-Path -LiteralPath $gonogoSummary) {
    $body += ""
    $body += "Go/No-Go Summary"
    $body += "----------------------------------------"
    $body += (Get-Content -LiteralPath $gonogoSummary -ErrorAction SilentlyContinue)
  } else {
    $body += ""
    $body += "Go/No-Go Summary"
    $body += "- (go_nogo_latest.txt not generated)"
  }

  # --- Paper Execution Summary (optional) ---
  $paperExecSummary = Join-Path $reportDir "paper_exec_summary_latest.txt"
  if (Test-Path -LiteralPath $paperExecSummary) {
    $body += ""
    $body += "Paper Execution Summary"
    $body += "----------------------------------------"
    $body += (Get-Content -LiteralPath $paperExecSummary -ErrorAction SilentlyContinue)
  } else {
    $body += ""
    $body += "Paper Execution Summary"
    $body += "- (paper_exec_summary_latest.txt not generated)"
  }

  # --- Min Lot Live Go/No-Go Block ---
  $tempPy = Join-Path $env:TEMP "gonogo_temp.py"
  @"
import sys
sys.path.insert(0, `"$projectRoot`")
from trader.report_blocks import render_min_lot_live_gonogo_email
print(render_min_lot_live_gonogo_email())
"@ | Out-File -FilePath $tempPy -Encoding UTF8
  $gonogoBlock = try { & $python $tempPy 2>$null } catch { "" }
  Remove-Item $tempPy -ErrorAction SilentlyContinue
  Write-Log "gonogoBlock length: $($gonogoBlock.Length)"
  if ($gonogoBlock) {
    $body += ""
    $body += $gonogoBlock
  }

$text = ($body -join "`r`n")
  [System.IO.File]::WriteAllText($bodyFile, $text, (New-Object System.Text.UTF8Encoding($false)))
  Write-Log ("[INFO] Body file written: {0} exists={1}" -f $bodyFile, (Test-Path -LiteralPath $bodyFile))

  

    Write-Log "[STEP] ops_cleanup"
  try {
    $keepDays = 30
    $cutoff = (Get-Date).AddDays(-$keepDays)

    # logs cleanup
    $logDir = Join-Path $projectRoot "scripts\logs"
    if (Test-Path -LiteralPath $logDir) {
      Get-ChildItem -LiteralPath $logDir -Filter "daily_run_*.log" -File |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        Remove-Item -Force -ErrorAction SilentlyContinue
    }

    # mail body cleanup
    $repDir = Join-Path $projectRoot "reports"
    if (Test-Path -LiteralPath $repDir) {
      Get-ChildItem -LiteralPath $repDir -Filter "daily_body_*.txt" -File |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        Remove-Item -Force -ErrorAction SilentlyContinue
    }

    # rotate paper history if too large
    $paperHist = Join-Path $reportDir "paper_trades_history.csv"
    if (Test-Path -LiteralPath $paperHist) {
      $maxMB = 50
      $lenMB = (Get-Item -LiteralPath $paperHist).Length / 1MB
      if ($lenMB -gt $maxMB) {
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $arch = Join-Path $reportDir ("paper_trades_history_{0}.csv" -f $stamp)
        Move-Item -LiteralPath $paperHist -Destination $arch -Force
        Write-Log ("[GUARD] rotated paper history: {0} -> {1}" -f $paperHist, $arch)
      }
    }

    Write-Log "[GUARD] ops_cleanup done"
  } catch {
    Write-Log ("[GUARD] ops_cleanup failed: {0}" -f $_.Exception.Message)
  }

# ---- FINALIZE (robust) ----
  $rcs = @((To-Int $rc_py),(To-Int $rc_data),(To-Int $rc_bt1),(To-Int $rc_bt2),(To-Int $rc_paper),(To-Int $rc_paper_yahoo),(To-Int $rc_live),(To-Int $rc_reconcile),(To-Int $rc_gonogo),(To-Int $rc_mail))
  $final = 0
  foreach ($x in $rcs) { if ($x -ne 0) { $final = 1; break } }

  if (-not $NoMail) {
    $subject = "Daily Trader Report - 23:00"
    if ($final -ne 0) { $subject += " [FAIL]" }
    $rc_mail = Invoke-Exe "notify_gmail" $python @(
      "-m","trader.notify_gmail",
      "--to","takeshiminaminoshima1@gmail.com",
      "--subject",$subject,
      "--body-file",$bodyFile,
      "--body-encoding","utf-8"
    )
  }

  Write-Log ("[INFO] RC_SUMMARY: py={0} data={1} bt1={2} bt2={3} paper={4} paper_yahoo={5} live={6} reconcile={7} gonogo={8} mail={9} -> final={10}" -f $rcs[0],$rcs[1],$rcs[2],$rcs[3],$rcs[4],$rcs[5],$rcs[6],$rcs[7],$rcs[8],$rcs[9],$final)
  Write-Log ("[INFO] End   : {0}" -f (Get-Date))
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
  Write-Log ("[GUARD] lock released: {0}" -f $lockPath)
  exit $final
}
catch {
  Write-Log ""
  Write-Log "[FATAL] PowerShell exception"
  Write-Log ("[FATAL] Message: {0}" -f $_.Exception.Message)
  Write-Log ("[FATAL] Type   : {0}" -f $_.Exception.GetType().FullName)
  Write-Log ("[FATAL] Line   : {0}" -f $_.InvocationInfo.ScriptLineNumber)
  Write-Log ("[FATAL] Code   : {0}" -f $_.InvocationInfo.Line)
  Write-Output $_.Exception.Message
  exit 1
}

