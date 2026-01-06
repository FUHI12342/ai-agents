param(
    [Parameter(Mandatory=$true)]
    [string]$Session,

    [Parameter(Mandatory=$true)]
    [string]$ToAddr,

    [string]$Preset = "good_20_100_risk_0_5",
    [double]$RiskPct = 0.5,
    [int]$ShortWindow = 20,
    [int]$LongWindow = 100,
    [ValidateSet("auto","force","never")]
    [string]$LlmMode = "auto",
    [switch]$DryRun,
    [switch]$UpdateData,
    [string]$UpdateSymbol = "",
    [switch]$FailOnDataUpdateError,
    [string[]]$Symbols
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ✅ project root を確実に決める（scripts の1つ上）
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

# ✅ logs ディレクトリ作成
$LogsDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

# ✅ ログファイル名生成
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogsDir "run_session_${Timestamp}.log"

# ✅ ログ関数（コンソール＋ファイル）
function Write-Log {
    param([string]$Message)
    $Line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Write-Host $Line
    $Line | Out-File -FilePath $LogFile -Append -Encoding UTF8
}

# ✅ 実行引数出力
Write-Log "=== Run Session Start ==="
Write-Log "Session: $Session"
Write-Log "ToAddr: $ToAddr"
Write-Log "Preset: $Preset"
Write-Log "RiskPct: $RiskPct"
Write-Log "ShortWindow: $ShortWindow"
Write-Log "LongWindow: $LongWindow"
Write-Log "LlmMode: $LlmMode"
Write-Log "DryRun: $DryRun"
Write-Log "UpdateData: $UpdateData"
Write-Log "UpdateSymbol: $UpdateSymbol"
Write-Log "FailOnDataUpdateError: $FailOnDataUpdateError"

# ✅ python を安定化（venv優先）
$PythonExe = $null
$projectVenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $projectVenvPython) {
    $PythonExe = $projectVenvPython
    Write-Log "Using Python: $PythonExe"
} else {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
    Write-Log "Using Python: $PythonExe"
}
Write-Log "ProjectRoot: $ProjectRoot"
Write-Log "PWD: $(Get-Location)"

# ✅ Symbols 確定
$SymbolsNormalized = @()
if ($Symbols) {
    $SymbolsNormalized = $Symbols -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
} else {
    # 未指定なら従来どおり単一symbol（config/envから）
    $SymbolsNormalized = @("BTCUSDT")  # 仮定、configから取得すべきだが簡易
}

function Invoke-Python {
  param([string[]]$PyArgs)
  if ($PyArgs.Count -eq 0) { throw "PyArgs is empty, cannot invoke Python" }
  $command = "& $PythonExe " + ($PyArgs -join " ")
  Write-Log "Command: $command"
  try {
    & $PythonExe @PyArgs
    $code = $LASTEXITCODE
    if ($code -ne 0) { throw "Python failed (exit=$code): $command" }
  } catch {
    Write-Log "Exception: $($_.Exception.Message)"
    throw
  }
}

# データ更新（オプション、Symbols全件）
if ($UpdateData) {
    $symbolsJoined = ($SymbolsNormalized -join ",")
    Write-Log "UpdateData is enabled. Updating data for symbols: $symbolsJoined"
    try {
        Invoke-Python -PyArgs @("-m","trader.update_data","--symbols",$symbolsJoined,"--interval","1d")
    } catch {
        Write-Log "WARN: Data update failed: $($_.Exception.Message)"
        if ($FailOnDataUpdateError) { throw }
    }
}

# レポート生成（1回のみ、Symbolsまとめて）
Write-Log "Generating $Session report..."
Invoke-Python -PyArgs @(
    "-m","trader.daily_report",$Session,
    "--preset",$Preset,
    "--symbols",($SymbolsNormalized -join ","),
    "--llm-mode",$LlmMode
)

# DryRun は「送信だけスキップ」にする（生成は確認したいはず）
if ($DryRun) {
    Write-Log "[SKIP] Gmail send because -DryRun"
    exit 0
}

# ✅ User環境変数から GMAIL_USER / GMAIL_APP_PASSWORD を読み取り、$env にセット
$user = [Environment]::GetEnvironmentVariable("GMAIL_USER","User")
$pass = [Environment]::GetEnvironmentVariable("GMAIL_APP_PASSWORD","User")
if (-not $user -or -not $pass) {
    Write-Log "SKIP: missing creds (has_user=$($user -ne $null), pw_len=$($pass.Length))"
    exit 0
} else {
    $env:GMAIL_USER = $user
    $env:GMAIL_APP_PASSWORD = $pass
    Write-Log "Creds loaded from User env (has_user=True, pw_len=$($pass.Length))"
}

# Gmail送信
Write-Log "Sending $Session report to $ToAddr..."
$sendTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stdoutFile = Join-Path $LogsDir "send_${Session}_${sendTimestamp}_stdout.txt"
$stderrFile = Join-Path $LogsDir "send_${Session}_${sendTimestamp}_stderr.txt"
$process = Start-Process -FilePath $PythonExe -ArgumentList @("-m","trader.send_daily_report_gmail",$Session,"--to",$ToAddr) -NoNewWindow -PassThru -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile -Wait
$exitCode = $process.ExitCode
$stdoutContent = Get-Content $stdoutFile -Raw
$stderrContent = Get-Content $stderrFile -Raw
if ($exitCode -eq 0) {
    if ($stdoutContent -match "GMAIL_SEND_SUCCESS") {
        Write-Log "Gmail send success: GMAIL_SEND_SUCCESS"
    } else {
        Write-Log "Gmail send completed (exit=0)"
    }
} else {
    Write-Log "Gmail send failed (exit=$exitCode)"
    # stderr の末尾20行以内をログに追記
    $stderrLines = $stderrContent -split "`n" | Where-Object { $_ -ne "" }
    $lastLines = $stderrLines | Select-Object -Last 20
    foreach ($line in $lastLines) {
        Write-Log "STDERR: $line"
    }
}
Write-Log "Session $Session completed"
exit 0