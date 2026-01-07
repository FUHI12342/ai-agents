# scripts/housekeeping.ps1
# Housekeeping script to clean up old logs and reports

param(
    [string]$Root = ".",
    [switch]$DryRun,
    [int]$KeepDaysLogs = 30,
    [int]$KeepDaysReports = 30
)

# Assume python is in PATH, or use full path if needed
$pythonCmd = "python"

# Build arguments
$args = @("trader/housekeeping.py", "--root", $Root)
if ($DryRun) {
    $args += "--dry-run"
}
$args += "--keep-days-logs", $KeepDaysLogs
$args += "--keep-days-reports", $KeepDaysReports

# Run the Python script
& $pythonCmd $args

# Exit with the same code
exit $LASTEXITCODE