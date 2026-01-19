param()

# Task Scheduler Hardening Script for ai-agents tasks
# Applies common settings: StartWhenAvailable, WakeToRun, Retry, etc.

Write-Host "Enumerating ai-agents tasks..."
$tasks = Get-ScheduledTask | Where-Object { $_.TaskName -like "ai-agents_*" }

if ($tasks.Count -eq 0) {
    Write-Host "No ai-agents tasks found."
    exit 0
}

foreach ($task in $tasks) {
    Write-Host "Processing task: $($task.TaskName)"

    # Get current settings
    $currentSettings = $task.Settings

    # Create new settings set
    $newSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 15) -ExecutionTimeLimit (New-TimeSpan -Hours 2)

    # Apply to task
    Set-ScheduledTask -TaskName $task.TaskName -Settings $newSettings

    # Refresh and display updated settings
    $updatedTask = Get-ScheduledTask -TaskName $task.TaskName
    Write-Host "Updated settings for $($task.TaskName):"
    Write-Host "  StartWhenAvailable: $($updatedTask.Settings.StartWhenAvailable)"
    Write-Host "  WakeToRun: $($updatedTask.Settings.WakeToRun)"
    Write-Host "  MultipleInstances: $($updatedTask.Settings.MultipleInstances)"
    Write-Host "  RestartCount: $($updatedTask.Settings.RestartCount)"
    Write-Host "  RestartInterval: $($updatedTask.Settings.RestartInterval)"
    Write-Host "  ExecutionTimeLimit: $($updatedTask.Settings.ExecutionTimeLimit)"
    Write-Host ""
}

Write-Host "All ai-agents tasks have been hardened."