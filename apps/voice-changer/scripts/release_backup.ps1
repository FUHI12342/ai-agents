#!/usr/bin/env pwsh

# Release backup script for voice-changer

Write-Host "Creating release backup..."

# Change to the project root
Set-Location $PSScriptRoot\..

# Create timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Backup directory
$backupDir = "backups/backup_$timestamp"

# Copy src directory to backup
Copy-Item -Path "src" -Destination $backupDir -Recurse

Write-Host "Backup created at $backupDir"