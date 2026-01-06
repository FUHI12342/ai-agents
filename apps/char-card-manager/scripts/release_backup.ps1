#!/usr/bin/env pwsh

# Release backup script for char-card-manager

Write-Host "Creating release backup for char-card-manager..."

# Change to the project root
Set-Location $PSScriptRoot\..

# Get current date and time
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

# Create backup directory if it doesn't exist
if (!(Test-Path backups)) {
    New-Item -ItemType Directory -Path backups
}

# Create zip archive
Compress-Archive -Path src/,tests/,scripts/,README.md,TODO.md,requirements.txt -DestinationPath "backups/release_$timestamp.zip"

Write-Host "Backup created: backups/release_$timestamp.zip"

# Update CHANGELOG_DEV.md
$changelogPath = "CHANGELOG_DEV.md"
if (Test-Path $changelogPath) {
    $currentDate = Get-Date -Format "yyyy-MM-dd"
    $entry = "`n## $currentDate`n- Release backup created: release_$timestamp.zip`n"
    Add-Content -Path $changelogPath -Value $entry
    Write-Host "CHANGELOG_DEV.md updated."
} else {
    Write-Host "CHANGELOG_DEV.md not found, skipping update."
}