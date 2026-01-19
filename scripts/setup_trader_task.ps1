param(
    [string]$TaskName = "TraderMorning",
    [string]$StartTime = "07:30",
    [string]$Session = "morning",
    [string]$ToAddr = "takeshiminaminoshima1@gmail.com",
    [string]$Symbols = "BTCUSDT,ETHUSDT",
    [string]$Preset = "good_20_100_risk_0_5",
    [string]$LlmMode = "auto",
    [switch]$UpdateData,
    [string]$RunAsUser = $env:USERNAME,
    [string]$RunAsPassword
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# repo root
$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$scriptPath = Join-Path $repo "scripts\run_session.ps1"

# 引数構築
$args = @(
    "-Session", $Session,
    "-ToAddr", $ToAddr,
    "-Symbols", $Symbols,
    "-Preset", $Preset,
    "-LlmMode", $LlmMode
)
if ($UpdateData) { $args += "-UpdateData" }

# コマンドライン
$taskToRun = "powershell.exe"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" " + ($args -join " ")

# schtasks 引数
$schtasksArgs = @(
    "/Create",
    "/TN", $TaskName,
    "/TR", "`"$taskToRun`"",
    "/SC", "DAILY",
    "/ST", $StartTime,
    "/RU", $RunAsUser
)

if ($RunAsPassword) {
    $schtasksArgs += "/RP", $RunAsPassword
} else {
    $schtasksArgs += "/IT"  # Interactive token
    Write-Host "WARNING: No -RunAsPassword specified. Task will run only when user is logged on." -ForegroundColor Yellow
}

# 実行
Write-Host "Creating task: $TaskName"
Write-Host "Command: schtasks $($schtasksArgs -join ' ')"
Write-Host "Arguments: $arguments"
& schtasks @schtasksArgs /F  # /F to overwrite

if ($LASTEXITCODE -ne 0) {
    throw "schtasks failed with exit code $LASTEXITCODE"
}

# 検証
Write-Host ""
Write-Host "=== Task Query ==="
schtasks /Query /TN $TaskName /V /FO LIST

# 警告
if ($arguments -match '-DryRun') {
    Write-Host "ERROR: -DryRun found in arguments!" -ForegroundColor Red
}
if ($ToAddr -eq 'test@example.com') {
    Write-Host "ERROR: Test email address detected!" -ForegroundColor Red
}