# App Scripts Inventory Script for ai-agents repository
# This script inventories scripts and directories for each app

# Set the repository root
$RepoRoot = Split-Path -Parent $PSScriptRoot

# Create reports directory if it doesn't exist
$ReportsDir = Join-Path $RepoRoot "reports\nightly"
if (-not (Test-Path $ReportsDir)) {
    New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null
}

# Initialize report
$ReportPath = Join-Path $ReportsDir "app_scripts_inventory_latest.md"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$Report = @"
# App Scripts Inventory Report - $Timestamp
Repository: $RepoRoot

## Apps Inventory

| App Name | test.ps1 | release_backup.ps1 | tests/ | backups/ | Latest Backup | Backup Files |
|----------|----------|-------------------|--------|----------|---------------|--------------|
"@

# Scan apps directory
$AppsDir = Join-Path $RepoRoot "apps"
if (Test-Path $AppsDir) {
    $AppDirs = Get-ChildItem $AppsDir -Directory | Sort-Object Name
    foreach ($AppDir in $AppDirs) {
        $AppName = $AppDir.Name

        # Check for scripts
        $TestScript = Join-Path $AppDir.FullName "scripts\test.ps1"
        $BackupScript = Join-Path $AppDir.FullName "scripts\release_backup.ps1"
        $TestScriptExists = if (Test-Path $TestScript) { "✓" } else { "✗" }
        $BackupScriptExists = if (Test-Path $BackupScript) { "✓" } else { "✗" }

        # Check for directories
        $TestsDir = Join-Path $AppDir.FullName "tests"
        $BackupsDir = Join-Path $AppDir.FullName "backups"
        $TestsDirExists = if (Test-Path $TestsDir) { "✓" } else { "✗" }
        $BackupsDirExists = if (Test-Path $BackupsDir) { "✓" } else { "✗" }

        # Get backup info
        $LatestBackup = "N/A"
        $BackupFiles = 0
        if (Test-Path $BackupsDir) {
            $BackupItems = Get-ChildItem $BackupsDir -Recurse -File
            $BackupFiles = $BackupItems.Count
            if ($BackupItems) {
                $LatestBackup = ($BackupItems | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            }
        }

        $Report += "| $AppName | $TestScriptExists | $BackupScriptExists | $TestsDirExists | $BackupsDirExists | $LatestBackup | $BackupFiles |`n"
    }
}

$Report += @"

## Summary
- Total apps: $($AppDirs.Count)
- Generated at: $Timestamp
"@

# Write report
$Report | Out-File -FilePath $ReportPath -Encoding UTF8
Write-Host "Inventory report generated: $ReportPath"