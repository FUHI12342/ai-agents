# Run all tests in the ai-agents repository
# This script activates the virtual environment and runs pytest on all test directories

param(
    [string]$TestPath = ".",
    [string]$ReportFile = "reports\nightly\test_report_latest.md"
)

# Set the repository root
$RepoRoot = Split-Path -Parent $PSScriptRoot

# Activate virtual environment if it exists
$venvPath = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
} else {
    Write-Host "Virtual environment not found at $venvPath, running without activation"
}

# Run tests
Write-Host "Running all tests..."
pytest $TestPath --tb=short | Out-File -FilePath (Join-Path $RepoRoot $ReportFile) -Encoding UTF8

# Deactivate virtual environment if it was activated
if (Test-Path $venvPath) {
    deactivate
}