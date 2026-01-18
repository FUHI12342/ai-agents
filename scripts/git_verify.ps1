$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Compack Git Verification ==="

$repoRoot = git rev-parse --show-toplevel
$branch = git rev-parse --abbrev-ref HEAD
Write-Host "Repo: $repoRoot"
Write-Host "Branch: $branch"

Write-Host "`nStatus:"
git status -sb

Write-Host "`nLast commit:"
git log -1 --oneline

Write-Host "`nFetching remotes (may fail if offline)..."
git fetch --all --prune | Out-Null

$aheadBehind = git rev-list --left-right --count HEAD...@{u} 2>$null
if ($LASTEXITCODE -eq 0 -and $aheadBehind) {
    $parts = $aheadBehind -split "\s+"
    Write-Host "Ahead: $($parts[0]) Behind: $($parts[1])"
} else {
    Write-Host "No upstream configured."
}

$diffFiles = git diff --name-only
$outside = @()
foreach ($f in $diffFiles) {
    if (-not $f) { continue }
    if ($f -like "apps/compack/*" -or $f -like "docs/*" -or $f -like "scripts/*" -or $f -eq "README.md") {
        continue
    }
    $outside += $f
}

if ($outside.Count -gt 0) {
    Write-Host "`n[FAIL] Diff contains files outside allowed scope:" -ForegroundColor Red
    $outside | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    exit 1
}

if ($diffFiles) {
    Write-Host "`nDiff files:" 
    $diffFiles | ForEach-Object { Write-Host " - $_" }
} else {
    Write-Host "`nNo local diff."
}

Write-Host "`n[PASS] Git verification completed." -ForegroundColor Green
exit 0
