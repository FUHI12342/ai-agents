$ErrorActionPreference = "Stop"

# repo = ...\ai-agents
$repo = if ($PSScriptRoot -and $PSScriptRoot.Trim().Length -gt 0) {
  Split-Path -Parent $PSScriptRoot
} else {
  (Resolve-Path ".").Path
}

$appsDir     = Join-Path $repo "apps"
$reportsDir  = Join-Path $repo "reports\nightly"
$archiveDir  = Join-Path $reportsDir "archive"

New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null
New-Item -ItemType Directory -Force -Path $archiveDir | Out-Null

$ts    = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# Backup Audit Report - $ts")
$lines.Add("Repository: $repo")
$lines.Add("")
$lines.Add("| App | BackupDir | LatestArtifact | LastWriteTime | Status |")
$lines.Add("|---|---|---|---|---|")

if (!(Test-Path -LiteralPath $appsDir)) {
  $lines.Add("| (none) | $appsDir | - | - | MISSING_APPS_DIR |")
}
else {
  Get-ChildItem -LiteralPath $appsDir -Directory | Sort-Object Name | ForEach-Object {
    $appDir = $_
    $app  = $appDir.Name
    $bdir = Join-Path $appDir.FullName "backups"

    if (!(Test-Path -LiteralPath $bdir)) {
      $lines.Add("| $app | $bdir | - | - | MISSING_BACKUP_DIR |")
      return
    }

    $zipFiles = @(Get-ChildItem -LiteralPath $bdir -Force -File -ErrorAction SilentlyContinue |
      Where-Object { $_.Extension -in ".zip",".7z" })

    $dirBackups = @(Get-ChildItem -LiteralPath $bdir -Force -Directory -ErrorAction SilentlyContinue)

    if ($zipFiles.Count -eq 0 -and $dirBackups.Count -eq 0) {
      $lines.Add("| $app | $bdir | - | - | EMPTY |")
      return
    }

    $candidates = if ($zipFiles.Count -gt 0) { $zipFiles } else { $dirBackups }
    $latest = $candidates | Sort-Object LastWriteTime -Descending | Select-Object -First 1

    $name   = $latest.Name
    $lt     = $latest.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
    $status = if ($zipFiles.Count -gt 0) { "OK_ZIP" } else { "OK_DIR" }

    $lines.Add("| $app | $bdir | $name | $lt | $status |")
  }
}

$latestPath  = Join-Path $reportsDir "backup_audit_latest.md"
$archivePath = Join-Path $archiveDir ("backup_audit_{0}.md" -f $stamp)

$body = ($lines -join "`r`n") + "`r`n"
if ([string]::IsNullOrWhiteSpace($body)) { throw "body is empty" }

# ここは .NET の byte 経路を使わず Set-Content で確実に書く
Set-Content -LiteralPath $latestPath  -Value $body -Encoding UTF8
Set-Content -LiteralPath $archivePath -Value $body -Encoding UTF8

Write-Host "Wrote: $latestPath"
Write-Host "Archived: $archivePath"
