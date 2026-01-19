# apps/roo-like/scripts/release_backup.ps1
$ErrorActionPreference = "Stop"

# scripts/ -> app root に移動
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appRoot   = Split-Path -Parent $scriptDir
Set-Location -LiteralPath $appRoot

# backup dir
$backupDir = Join-Path $appRoot "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$zip = Join-Path $backupDir "roo-like_release_$ts.zip"

# 存在するものだけバックアップ（無いものは無視）
$items = @(
  "src",
  "tests",
  "scripts",
  "README.md",
  "TODO.md",
  "pyproject.toml",
  "requirements.txt"
) | Where-Object { Test-Path $_ }

if ($items.Count -eq 0) {
  throw "No backup items found in $appRoot"
}

Compress-Archive -Path $items -DestinationPath $zip -Force
Write-Host "Backup created: $zip"
exit 0
