# Run all backups in the ai-agents repository
# This script runs release_backup.ps1 for each app and generates a report

# Set the repository root
$RepoRoot = Split-Path -Parent $PSScriptRoot

# Create reports directory if it doesn't exist
$ReportsDir = Join-Path $RepoRoot "reports\nightly"
if (-not (Test-Path $ReportsDir)) {
    New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null
}

# Initialize report
$ReportPath = Join-Path $ReportsDir "backup_run_latest.md"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$Report = @"
# Backup Run Report - $Timestamp
Repository: $RepoRoot

## Backup Results
"@
$TotalApps = 0
$PassedApps = 0
$FailedApps = 0
$SkippedApps = 0

# Find and run backup scripts for each app
$AppsDir = Join-Path $RepoRoot "apps"
if (Test-Path $AppsDir) {
    $AppDirs = Get-ChildItem $AppsDir -Directory
    foreach ($AppDir in $AppDirs) {
        $BackupScript = Join-Path $AppDir.FullName "scripts\release_backup.ps1"
        if (-not (Test-Path $BackupScript)) {
            # Generate release_backup.ps1
            $AppName = $AppDir.Name
            $BackupScriptContent = @"
# Backup script for $AppName
`$AppRoot = Split-Path -Parent `$PSScriptRoot
`$BackupDir = Join-Path `$AppRoot "backups"
if (-not (Test-Path `$BackupDir)) {
    New-Item -ItemType Directory -Path `$BackupDir -Force | Out-Null
}
`$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
`$ZipName = "$AppName`_backup_`$Timestamp.zip"
`$ZipPath = Join-Path `$BackupDir `$ZipName
`$SourceDir = `$AppRoot
# Compress excluding backups, venv, __pycache__
Compress-Archive -Path `$SourceDir\* -DestinationPath `$ZipPath -CompressionLevel Optimal -Exclude "backups\*", ".venv\*", "venv\*", "__pycache__\*" -ErrorAction Stop
Write-Host "Backup created: `$ZipPath"
exit 0
"@
            $ScriptsDir = Join-Path $AppDir.FullName "scripts"
            if (-not (Test-Path $ScriptsDir)) {
                New-Item -ItemType Directory -Path $ScriptsDir -Force | Out-Null
            }
            $BackupScriptContent | Out-File -FilePath $BackupScript -Encoding UTF8
        }
        if (Test-Path $BackupScript) {
            $TotalApps++
            $AppName = $AppDir.Name
            Write-Host "Running backup for $AppName..."
            $StartTime = Get-Date
            try {
                $Process = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$BackupScript`"" -Wait -PassThru -NoNewWindow -WorkingDirectory $AppDir.FullName
                $ExitCode = $Process.ExitCode
                $EndTime = Get-Date
                $Elapsed = $EndTime - $StartTime
                if ($ExitCode -eq 0) {
                    $Status = "PASS"
                    $PassedApps++
                } elseif ($ExitCode -eq 2) {
                    $Status = "SKIP"
                    $SkippedApps++
                } else {
                    $Status = "FAIL"
                    $FailedApps++
                }
                $Report += @"

### $AppName - Status: $Status - Exit Code: $ExitCode - Start Time: $StartTime - End Time: $EndTime - Elapsed: $($Elapsed.TotalSeconds) seconds

"@
            } catch {
                $EndTime = Get-Date
                $Elapsed = $EndTime - $StartTime
                $Report += @"

### $AppName - Status: ERROR - Error: $($_.Exception.Message) - Start Time: $StartTime - End Time: $EndTime - Elapsed: $($Elapsed.TotalSeconds) seconds

"@
                $FailedApps++
            }
        }
    }
}

# Add summary
$Report += @"

## Summary
- Total apps with backup scripts: $TotalApps
- Passed: $PassedApps
- Failed: $FailedApps
- Skipped: $SkippedApps

Report generated at $Timestamp
"@

# Write report to file
$Report | Out-File -FilePath $ReportPath -Encoding UTF8

# Set exit code
if ($FailedApps -gt 0) {
    exit 1
} else {
    exit 0
}