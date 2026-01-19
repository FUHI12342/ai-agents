param(
  [string]$Root = ".",
  [string]$EnvFile = ".\.env"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Say($s){ Write-Host $s }

$targets = @()
$potential_targets = @("trader", "scripts")
foreach ($t in $potential_targets) {
  $full_path = Join-Path $Root $t
  if (Test-Path $full_path) {
    $targets += $full_path
  }
}

$files = @()
foreach($t in $targets){
  $files += Get-ChildItem -Path $t -Recurse -File -Include *.py,*.ps1 -ErrorAction SilentlyContinue
}

# regex patterns to capture ENV KEY
$patterns = @(
  "os\.getenv\(\s*['""](?<k>[A-Z0-9_]+)['""]",
  "os\.environ\.get\(\s*['""](?<k>[A-Z0-9_]+)['""]"
)

$set = New-Object "System.Collections.Generic.HashSet[string]"
$hits = New-Object "System.Collections.Generic.List[string]"

foreach($f in $files){
  $text = Get-Content -Raw -LiteralPath $f.FullName -ErrorAction SilentlyContinue
  if (-not $text) { continue }

  foreach($pat in $patterns){
    foreach($m in [regex]::Matches($text, $pat)){
      $k = $m.Groups["k"].Value
      if ($k) { [void]$set.Add($k) }
    }
  }

  # For BINANCE/TESTNET: show file+line hits
  try {
    $lines = Get-Content -LiteralPath $f.FullName
    if ($lines -and $lines.Length -gt 0){
      for($i=0; $i -lt $lines.Length; $i++){
        $ln = $lines[$i]
        if ($ln -match "BINANCE|TESTNET"){
          $hits.Add(("{0}:{1}:{2}" -f $f.FullName, ($i+1), $ln.Trim())) | Out-Null
        }
      }
    }
  } catch {
    # Ignore
  }
}

# read .env keys
$envKeys = New-Object "System.Collections.Generic.HashSet[string]"
if (Test-Path $EnvFile){
  $envLines = Get-Content -LiteralPath $EnvFile -ErrorAction SilentlyContinue
  foreach($l in $envLines){
    if ($l -match "^\s*([A-Z0-9_]+)\s*="){
      [void]$envKeys.Add($Matches[1])
    }
  }
}

Say "=== ENV VARS referenced by code (os.getenv / os.environ.get) ==="
$all = [string[]]$set | Sort-Object
$all | ForEach-Object { Say $_ }

Say ""
Say "=== BINANCE/TESTNET raw hits (file:line:content) ==="
($hits | Sort-Object -Unique) | ForEach-Object { Say $_ }

Say ""
Say "=== Missing in .env (referenced by code, not present in .env) ==="
$missing = $all | Where-Object { -not $envKeys.Contains($_) } | Sort-Object
if ($missing.Count -eq 0){ Say "(none)" } else { $missing | ForEach-Object { Say $_ } }

Say ""
Say "=== Unused in code (present in .env, not detected in code scan) ==="
$unused = [string[]]$envKeys | Where-Object { -not ($set.Contains($_)) } | Sort-Object
if ($unused.Count -eq 0){ Say "(none)" } else { $unused | ForEach-Object { Say $_ } }

Say ""
Say "DONE. Run: powershell -ExecutionPolicy Bypass -File .\scripts\check_env_vars.ps1"