param()

# Sanity check for noon report: Ensure it's not all zeros
# Generates noon report in dry-run mode and checks if all metrics are zero

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = $null
if ($PSCommandPath) { $scriptPath = $PSCommandPath }
elseif ($MyInvocation -and $MyInvocation.MyCommand -and $MyInvocation.MyCommand.Path) { $scriptPath = $MyInvocation.MyCommand.Path }
if (-not $scriptPath) { throw "Cannot determine script path." }

$scriptDir   = Split-Path -Parent $scriptPath
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
Set-Location -Path $projectRoot

$python    = Join-Path $projectRoot ".venv\Scripts\python.exe"
$reportDir = Join-Path $projectRoot "trader\reports"
$flagPath  = Join-Path $reportDir "noon_sanity_checked.flag"

# Check if already checked
if (Test-Path -LiteralPath $flagPath) {
    Write-Host "Already checked. PASS (exit 0)"
    exit 0
}

# Generate noon report (dry-run, no mail)
Write-Host "Generating noon report for sanity check..."
$symbols = "BTCUSDT,ETHUSDT"
$preset = "good_20_100_risk_0_5"

& $python -m trader.daily_report noon --symbols $symbols --preset $preset --llm-mode never --force
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: Report generation failed (exit 1)"
    exit 1
}

# Read the report
$dateStr = Get-Date -Format "yyyyMMdd"
$reportPath = "D:\ai-data\trader\logs\report_${dateStr}_noon_multi.txt"
if (-not (Test-Path -LiteralPath $reportPath)) {
    Write-Host "FAIL: Report file not found (exit 1)"
    exit 1
}

$content = Get-Content -LiteralPath $reportPath -Raw

# Check for all zeros pattern
# Look for lines like "Symbol | 0.00 | 0.00 | 0.00 | 0 | 0.00"
$lines = $content -split "`r`n"
$allZero = $true
foreach ($line in $lines) {
    if ($line -match "^\w+\s*\|\s*(-?\d+\.\d+)\s*\|\s*(-?\d+\.\d+)\s*\|\s*(-?\d+\.\d+)\s*\|\s*(\d+)\s*\|\s*(-?\d+\.\d+)$") {
        $returnPct = [double]$matches[1]
        $maxDd = [double]$matches[2]
        $sharpe = [double]$matches[3]
        $trades = [int]$matches[4]
        $final = [double]$matches[5]
        if ($returnPct -ne 0 -or $maxDd -ne 0 -or $sharpe -ne 0 -or $trades -ne 0 -or $final -ne 0) {
            $allZero = $false
            break
        }
    }
}

if ($allZero) {
    Write-Host "FAIL: All metrics are zero (exit 1)"
    exit 1
} else {
    Write-Host "PASS: Metrics are not all zero (exit 0)"
    # Create flag
    "" | Out-File -FilePath $flagPath -Encoding UTF8
    exit 0
}