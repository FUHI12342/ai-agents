$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $repo
& (Join-Path $repo "scripts\backup_audit.ps1")
exit $LASTEXITCODE
