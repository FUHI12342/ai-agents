cd C:\Users\FHiro\Projects\ai-agents

## 0) 事前に、現在の同名/旧名タスクを全削除（存在しなくてもOK）
# 旧方式（ルート直下に "AI-Agents Nightly Tests" 等）がある可能性があるので両方消す
$names = @(
  "\AI-Agents\Nightly Tests",
  "\AI-Agents\Backup Run",
  "\AI-Agents\Backup Audit",
  "\AI-Agents Nightly Tests",
  "\AI-Agents Backup Run",
  "\AI-Agents Backup Audit",
  "AI-Agents Nightly Tests",
  "AI-Agents Backup Run",
  "AI-Agents Backup Audit"
)
foreach ($n in $names) {
  schtasks /Delete /TN "$n" /F 2>$null | Out-Null
}

## 1) Task Scheduler にフォルダ "\AI-Agents\" を作成（無ければ）
powershell -NoProfile -Command @'
$svc = New-Object -ComObject "Schedule.Service"
$svc.Connect()
$root = $svc.GetFolder("\")
try { $null = $root.GetFolder("AI-Agents") } catch { $null = $root.CreateFolder("AI-Agents") }
'@

## 2) /TR 用のコマンドを「クォート崩れしない形」で組み立てる
$RepoRoot = "C:\Users\FHiro\Projects\ai-agents"
$TestsScript  = Join-Path $RepoRoot "scripts\run_all_tests.ps1"
$BackupRun    = Join-Path $RepoRoot "scripts\backup_run_all.ps1"
$BackupAudit  = Join-Path $RepoRoot "scripts\backup_audit.ps1"

function Make-Tr([string]$scriptPath) {
  # powershell.exe -Command "Set-Location '...'; & '...'"
  # ※ ; を含むので、外側は schtasks が解釈できるように全体をダブルクォートで守る
  $cmd = "Set-Location -LiteralPath ""$RepoRoot""; & ""$scriptPath"""
  return "powershell -NoProfile -ExecutionPolicy Bypass -Command `"$cmd`""
}

$TR_Tests = Make-Tr $TestsScript
$TR_Run   = Make-Tr $BackupRun
$TR_Audit = Make-Tr $BackupAudit

## 3) タスクを \AI-Agents\ 配下に作成（毎日 02:00/02:15/02:30）
schtasks /Create /F /TN "\AI-Agents\Nightly Tests" /SC DAILY /ST 02:00 /TR "$TR_Tests"
schtasks /Create /F /TN "\AI-Agents\Backup Run"   /SC DAILY /ST 02:15 /TR "$TR_Run"
schtasks /Create /F /TN "\AI-Agents\Backup Audit" /SC DAILY /ST 02:30 /TR "$TR_Audit"

## 4) “存在確認” （schtasks と Get-ScheduledTask の両方）
schtasks /Query /TN "\AI-Agents\Nightly Tests" /V /FO LIST
schtasks /Query /TN "\AI-Agents\Backup Run" /V /FO LIST
schtasks /Query /TN "\AI-Agents\Backup Audit" /V /FO LIST

Get-ScheduledTask -TaskPath "\AI-Agents\" | Format-Table TaskPath, TaskName, State

## 5) 手動で Run → reports が更新されるか確認
# （順番に実行。各5秒待つ）
schtasks /Run /TN "\AI-Agents\Nightly Tests"
powershell -NoProfile -Command "Start-Sleep -Seconds 5"
schtasks /Run /TN "\AI-Agents\Backup Run"
powershell -NoProfile -Command "Start-Sleep -Seconds 5"
schtasks /Run /TN "\AI-Agents\Backup Audit"
powershell -NoProfile -Command "Start-Sleep -Seconds 5"

## 6) LastRunTime / LastTaskResult を確認
Get-ScheduledTaskInfo -TaskPath "\AI-Agents\" -TaskName "Nightly Tests"
Get-ScheduledTaskInfo -TaskPath "\AI-Agents\" -TaskName "Backup Run"
Get-ScheduledTaskInfo -TaskPath "\AI-Agents\" -TaskName "Backup Audit"

## 7) reports/nightly の更新確認（時刻と中身）
if (-not (Test-Path ".\reports\nightly")) { Write-Host "reports\nightly not found"; exit 1 }
dir .\reports\nightly | Sort-Object LastWriteTime -Descending
Get-Content .\reports\nightly\test_report_latest.md -TotalCount 120
Get-Content .\reports\nightly\backup_run_latest.md -TotalCount 200
Get-Content .\reports\nightly\backup_audit_latest.md -TotalCount 200

## 8) TaskScheduler Operational log から直近2時間の該当イベント抽出（証跡）
powershell -NoProfile -Command @'
$start=(Get-Date).AddHours(-2)
Get-WinEvent -FilterHashtable @{LogName="Microsoft-Windows-TaskScheduler/Operational"; StartTime=$start} |
  Where-Object { $_.Message -match "AI-Agents\\Nightly Tests|AI-Agents\\Backup Run|AI-Agents\\Backup Audit|run_all_tests\.ps1|backup_run_all\.ps1|backup_audit\.ps1" } |
  Select-Object TimeCreated, Id, LevelDisplayName, Message |
  Format-List
'@

# Report format (must):
# - changed files list（この手順は原則コード変更なし）
# - executed commands and results（0〜8）
# - verification:
#   - schtasks /Query が3つとも成功
#   - Get-ScheduledTask -TaskPath "\AI-Agents\" で3つ見える
#   - 手動Run後に Get-ScheduledTaskInfo の LastRunTime / LastTaskResult が更新
#   - reports/nightly の LastWriteTime が更新
#   - Operational log に該当イベントが出る
# End. ここで停止（ループしない）