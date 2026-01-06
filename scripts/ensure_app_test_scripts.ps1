# ensure_app_test_scripts.ps1
# apps/* を列挙して、scripts/test.ps1 が無いアプリにだけ生成する

$ErrorActionPreference = "Stop"

# apps 配下のディレクトリを取得
$appsDir = ".\apps"
if (-not (Test-Path $appsDir)) {
    Write-Host "apps directory not found: $appsDir"
    exit 1
}

$apps = Get-ChildItem -Path $appsDir -Directory | Select-Object -ExpandProperty Name

$generated = @()

foreach ($app in $apps) {
    $testScriptPath = Join-Path $appsDir "$app\scripts\test.ps1"

    if (Test-Path $testScriptPath) {
        Write-Host "Skipping $app : test.ps1 already exists"
        continue
    }

    # scripts ディレクトリが存在するか確認
    $scriptsDir = Join-Path $appsDir "$app\scripts"
    if (-not (Test-Path $scriptsDir)) {
        New-Item -ItemType Directory -Path $scriptsDir | Out-Null
    }

    # test.ps1 のテンプレート
    $testContent = @"
# test.ps1 for $app
# 安全なテンプレート：tests ディレクトリが無ければ SKIP (exit 2)

param()

`$ErrorActionPreference = "Stop"

# RepoRoot 算出
`$RepoRoot = Split-Path -Parent (Split-Path -Parent `$PSScriptRoot)
`$app = Split-Path -Leaf (Split-Path -Parent `$PSScriptRoot)
`$testsDir = Join-Path `$RepoRoot "apps\`$app\tests"

# tests ディレクトリチェック
if (-not (Test-Path `$testsDir)) {
    Write-Host "No tests directory found for `$app - SKIP"
    exit 2
}

# python チェック
try {
    `$pythonVersion = python --version 2>&1
    if (`$LASTEXITCODE -ne 0) { throw "python not found" }
} catch {
    Write-Host "Python not available - FAIL"
    exit 1
}

# pytest 実行
Write-Host "Running pytest for `$app..."
`$result = python -m pytest -q `$testsDir
exit `$LASTEXITCODE
"@

    # ファイル書き込み
    $testContent | Out-File -FilePath $testScriptPath -Encoding UTF8
    Write-Host "Generated test.ps1 for $app : $testScriptPath"
    $generated += $app
}

if ($generated.Count -eq 0) {
    Write-Host "No new test.ps1 generated"
} else {
    Write-Host "Generated test.ps1 for: $($generated -join ', ')"
}