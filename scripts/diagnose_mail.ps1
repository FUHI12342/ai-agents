param(
  [string]$TaskName = "\TraderMorning"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-FirstMatchValue {
  param(
    [string[]]$Lines,
    [string[]]$Patterns
  )
  foreach ($p in $Patterns) {
    $m = $Lines | Select-String -Pattern $p | Select-Object -First 1
    if ($null -ne $m -and $m.Matches.Count -gt 0) {
      return $m.Matches[0].Groups[1].Value.Trim()
    }
  }
  return ""
}

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Write-Host "Repo: $repo"
Write-Host ""

Write-Host "=== schtasks /Query (Verbose) ==="
$lines = schtasks /Query /TN $TaskName /V /FO LIST 2>&1
$lines | ForEach-Object { $_ }

# 日本語/英語どちらでも拾う
$cmdline = Get-FirstMatchValue -Lines $lines -Patterns @(
  '^\s*実行するタスク:\s*(.*)$',
  '^\s*Task To Run:\s*(.*)$'
)

$lastRun = Get-FirstMatchValue -Lines $lines -Patterns @(
  '^\s*前回の実行時刻:\s*(.*)$',
  '^\s*Last Run Time:\s*(.*)$'
)

$lastRes = Get-FirstMatchValue -Lines $lines -Patterns @(
  '^\s*前回の結果:\s*(.*)$',
  '^\s*Last Run Result:\s*(.*)$'
)

$nextRun = Get-FirstMatchValue -Lines $lines -Patterns @(
  '^\s*次回の実行時刻:\s*(.*)$',
  '^\s*Next Run Time:\s*(.*)$'
)

$runAs = Get-FirstMatchValue -Lines $lines -Patterns @(
  '^\s*ユーザーとして実行:\s*(.*)$',
  '^\s*Run As User:\s*(.*)$'
)

$logonMode = Get-FirstMatchValue -Lines $lines -Patterns @(
  '^\s*ログオン モード:\s*(.*)$',
  '^\s*Logon Mode:\s*(.*)$'
)

Write-Host ""
Write-Host "=== Extracted ==="
Write-Host "TaskName       : $TaskName"
Write-Host "CommandLine    : $cmdline"
Write-Host "Run As User    : $runAs"
Write-Host "Logon Mode     : $logonMode"
Write-Host "Last Run Time  : $lastRun"
Write-Host "Last Run Result: $lastRes"
Write-Host "Next Run Time  : $nextRun"

# よくある未着原因を自動判定
Write-Host ""
if ($cmdline -match '(?i)\s-DryRun\b') {
  Write-Host "WARNING: -DryRun found (mail will NEVER send)." -ForegroundColor Red
}
if ($cmdline -match '(?i)test@example\.com') {
  Write-Host "WARNING: test@example.com found (sending to test address)." -ForegroundColor Red
}
if ($cmdline -notmatch '(?i)run_session\.ps1') {
  Write-Host "WARNING: run_session.ps1 not found in command." -ForegroundColor Yellow
}
if ($logonMode -match '対話型のみ|Interactive only') {
  Write-Host "NOTE: Task runs only when user is logged on (ログオン中のみ実行)." -ForegroundColor Yellow
}

# TaskScheduler Operational の直近イベント（失敗理由の痕跡）
Write-Host ""
Write-Host "=== TaskScheduler Operational (recent for this task) ==="
$logName = "Microsoft-Windows-TaskScheduler/Operational"
try {
  $events = Get-WinEvent -LogName $logName -MaxEvents 1500 |
    ForEach-Object {
      $x = [xml]$_.ToXml()
      $d = $x.Event.EventData.Data
      $tn = ($d | Where-Object { $_.Name -eq "TaskName" })."#text"
      if ($tn -ne $TaskName) { return }
      [pscustomobject]@{
        TimeCreated = $_.TimeCreated
        Id          = $_.Id
        Level       = $_.LevelDisplayName
        ResultCode  = ($d | Where-Object { $_.Name -eq "ResultCode" })."#text"
        ActionName  = ($d | Where-Object { $_.Name -eq "ActionName" })."#text"
        Message     = ($_.Message -replace "`r`n"," " )
      }
    } |
    Sort-Object TimeCreated -Descending |
    Select-Object -First 20

  $events | Format-Table -Auto
} catch {
  Write-Host "Cannot read event log: $($_.Exception.Message)" -ForegroundColor Yellow
  Write-Host "Enable TaskScheduler Operational log: wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true" -ForegroundColor Cyan
}

# run_session ログの最新を表示（ここが一番強い証拠）
Write-Host ""
Write-Host "=== Latest run_session log (tail) ==="
$logDir = Join-Path $repo "scripts\logs"
if (Test-Path $logDir) {
  $latest = Get-ChildItem $logDir -Filter "run_session_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($null -ne $latest) {
    Write-Host "Log: $($latest.FullName)"
    Get-Content $latest.FullName -Tail 120
  } else {
    Write-Host "No run_session_*.log found in $logDir"
  }
} else {
  Write-Host "No log dir: $logDir"
}
