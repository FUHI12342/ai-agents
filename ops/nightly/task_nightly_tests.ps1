$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)  # ...\ops\nightly -> ...\ai-agents
Set-Location -LiteralPath $repo
& (Join-Path $repo "scripts\run_all_tests.ps1")
exit $LASTEXITCODE
