param(
    [string]$ReportPath = "reports\nightly\test_report_latest.md"
)

$ErrorActionPreference = "Stop"
$repo = if ($PSScriptRoot -and $PSScriptRoot.Trim().Length -gt 0) { Split-Path -Parent $PSScriptRoot } else { (Resolve-Path '.').Path }
Set-Location -LiteralPath $repo

if (!(Test-Path -LiteralPath (Join-Path $repo 'pytest.ini'))) { throw "pytest.ini not found in repo root: $repo" }
Write-Host ("rootdir: " + $repo)

# Define apps with tests
$apps = @(
    "apps/char-card-manager",
    "apps/speckit",
    "apps/trend-illustrator",
    "apps/voice-changer",
    "apps/healthhub",
    "apps/ideaminer",
    "apps/netdefender",
    "apps/roo-like",
    "apps/watch-connector"
)

$allResults = @()
$overallExitCode = 0
$oldPyPath = $env:PYTHONPATH

foreach ($app in $apps) {
    $appPath = Join-Path $repo $app
    $testPath = Join-Path $appPath "tests"

    if (Test-Path $testPath) {
        Write-Host "Running tests for $app..."

        # Set PYTHONPATH to include the app's src directory
        $srcPath = Join-Path $appPath "src"
        $env:PYTHONPATH = $srcPath
        if ($oldPyPath) { $env:PYTHONPATH += ";" + $oldPyPath }

        # Run pytest in the app directory
        $pytestOutput = & python -m pytest --tb=short $testPath 2>&1
        $exitCode = $LASTEXITCODE

        Write-Host "Exit code for ${app}: $exitCode"
        Write-Host "Output for ${app}: $pytestOutput"

        $result = @{
            App = $app
            ExitCode = $exitCode
            Output = $pytestOutput
        }

        $allResults += $result

        if ($exitCode -ne 0) {
            $overallExitCode = 1
        }
    } else {
        Write-Host "No tests directory found for $app"
    }
}
$env:PYTHONPATH = $oldPyPath

# Generate report
$reportContent = @"
============================= test session starts =============================
platform win32 -- Python 3.10.6, pytest-9.0.2, pluggy-1.6.0
rootdir: $repo
configfile: pytest.ini
plugins: anyio-3.7.1

"@

$totalTests = 0
$totalErrors = 0
$totalFailures = 0
$totalPassed = 0

foreach ($result in $allResults) {
    $reportContent += "Results for $($result.App):`n"
    $reportContent += $result.Output
    $reportContent += "`n"

    # Parse output for summary (simplified parsing)
    $outputStr = $result.Output -join "`n"
    if ($outputStr -match "(\d+) passed, (\d+) failed, (\d+) errors") {
        $passed = [int]$matches[1]
        $failed = [int]$matches[2]
        $errors = [int]$matches[3]
        $totalPassed += $passed
        $totalFailures += $failed
        $totalErrors += $errors
        $totalTests += $passed + $failed + $errors
    }
}

$reportContent += "=========================== short test summary info ===========================`n"
foreach ($result in $allResults) {
    if ($result.ExitCode -ne 0) {
        $reportContent += "ERROR $($result.App)`n"
    }
}

$reportContent += "============================= $totalTests tests, $totalPassed passed, $totalFailures failed, $totalErrors errors in $([math]::Round((Get-Date).Subtract((Get-Date).AddSeconds(-1)).TotalSeconds, 2))s =============================="

# Write report
$reportContent | Out-File -FilePath $ReportPath -Encoding UTF8

# Write to console
Write-Host $reportContent

# Exit with overall exit code
exit $overallExitCode