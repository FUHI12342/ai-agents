# Backup script for healthhub app
# Creates a zip archive of the app's main assets

# Get the app directory (script is run from app root)
$AppDir = Get-Location
$AppName = Split-Path $AppDir -Leaf

# Create backups directory if it doesn't exist
$BackupDir = Join-Path $AppDir "backups"
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

# Generate timestamp
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ZipName = "${AppName}_backup_${Timestamp}.zip"
$ZipPath = Join-Path $BackupDir $ZipName

# Define files and directories to include
$IncludeItems = @(
    "src",
    "tests",
    "scripts",
    "README.md",
    "TODO.md",
    "pyproject.toml",
    "requirements*.txt",
    "CHANGELOG_DEV.md"
)

# Create temporary directory for staging
$TempDir = Join-Path $env:TEMP "backup_temp_$AppName"
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

try {
    # Copy items to temp directory
    foreach ($Item in $IncludeItems) {
        $SourcePath = Join-Path $AppDir $Item
        if (Test-Path $SourcePath) {
            if ((Get-Item $SourcePath).PSIsContainer) {
                Copy-Item $SourcePath $TempDir -Recurse -Force
            } else {
                Copy-Item $SourcePath $TempDir -Force
            }
        }
    }

    # Create zip archive
    Compress-Archive -Path (Join-Path $TempDir "*") -DestinationPath $ZipPath -Force

    Write-Host "Backup created: $ZipPath"
    exit 0
} catch {
    Write-Host "Error creating backup: $($_.Exception.Message)"
    exit 1
} finally {
    # Clean up temp directory
    if (Test-Path $TempDir) {
        Remove-Item $TempDir -Recurse -Force
    }
}