# Schedule nightly tasks for ai-agents repository
# This script creates scheduled tasks for automated testing and backup auditing

$repo = "C:\Users\FHiro\Projects\ai-agents"

# Delete existing tasks if they exist
$tasksToDelete = @(
    "\AI-Agents Nightly Tests",
    "\AI-Agents Backup Audit",
    "\AI-Agents\Nightly Tests",
    "\AI-Agents\Backup Run",
    "\AI-Agents\Backup Audit"
)
foreach ($task in $tasksToDelete) {
    try {
        schtasks /Delete /TN $task /F 2>$null
        Write-Host "Deleted existing task: $task"
    } catch {
        # Ignore errors if task doesn't exist
    }
}

# /TR 生成関数
function Make-Tr([string]$scriptPath) {
  $cmd = "cd `"$repo`"; & `"$scriptPath`""
  return "powershell -NoProfile -ExecutionPolicy Bypass -Command '$cmd'"
}

$tr1 = Make-Tr ".\scripts\run_all_tests.ps1"
$tr2 = Make-Tr ".\scripts\backup_run_all.ps1"
$tr3 = Make-Tr ".\scripts\backup_audit.ps1"

# Create task for running all tests at 02:00
schtasks /Create /TN "\AI-Agents\Nightly Tests" /SC DAILY /ST 02:00 /TR "$tr1" /F

# Create task for backup run at 02:15
schtasks /Create /TN "\AI-Agents\Backup Run" /SC DAILY /ST 02:15 /TR "$tr2" /F

# Create task for backup audit at 02:30
schtasks /Create /TN "\AI-Agents\Backup Audit" /SC DAILY /ST 02:30 /TR "$tr3" /F

# Query scheduled tasks
Write-Host "Scheduled tasks created:"
schtasks /Query /TN "\AI-Agents\Nightly Tests"
schtasks /Query /TN "\AI-Agents\Backup Run"
schtasks /Query /TN "\AI-Agents\Backup Audit"

# Optional: Run tasks immediately for testing
# schtasks /Run /TN "AI-Agents Nightly Tests"
# schtasks /Run /TN "AI-Agents Backup Audit"

# Verification commands (copy and paste to verify)
# schtasks /Query /TN "\AI-Agents\Nightly Tests" /V /FO LIST
# schtasks /Query /TN "\AI-Agents\Backup Run" /V /FO LIST
# schtasks /Query /TN "\AI-Agents\Backup Audit" /V /FO LIST
# powershell -NoProfile -Command "Get-ScheduledTask -TaskPath '\AI-Agents\' | ft TaskPath,TaskName,State"
# powershell -NoProfile -Command "Get-ScheduledTaskInfo -TaskPath '\AI-Agents\' -TaskName 'Nightly Tests'; Get-ScheduledTaskInfo -TaskPath '\AI-Agents\' -TaskName 'Backup Run'; Get-ScheduledTaskInfo -TaskPath '\AI-Agents\' -TaskName 'Backup Audit'"

# Manual run commands (copy and paste to test)
# schtasks /Run /TN "\AI-Agents\Nightly Tests"
# powershell -NoProfile -Command "Start-Sleep -Seconds 5"
# schtasks /Run /TN "\AI-Agents\Backup Run"
# powershell -NoProfile -Command "Start-Sleep -Seconds 5"
# schtasks /Run /TN "\AI-Agents\Backup Audit"
# powershell -NoProfile -Command "Start-Sleep -Seconds 5"

# Operational log check
# powershell -NoProfile -Command "Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -MaxEvents 300 | ? { $_.Message -match 'Nightly Tests|Backup Run|Backup Audit|\\AI-Agents\\' } | select TimeCreated,Id,LevelDisplayName,Message | fl"

# Optional: Delete tasks
# schtasks /Delete /TN "\AI-Agents\Nightly Tests" /F
# schtasks /Delete /TN "\AI-Agents\Backup Run" /F
# schtasks /Delete /TN "\AI-Agents\Backup Audit" /F