$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")

function New-Shortcut {
    param (
        [string]$Name,
        [string]$TargetPath,
        [string]$Arguments = "",
        [string]$WorkingDirectory = $repoRoot,
        [string]$Description = ""
    )
    $shell = New-Object -ComObject WScript.Shell
    $shortcutPath = Join-Path $desktop "$Name.lnk"
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $TargetPath
    if ($Arguments) {
        $shortcut.Arguments = $Arguments
    }
    $shortcut.WorkingDirectory = $WorkingDirectory
    if ($Description) {
        $shortcut.Description = $Description
    }
    $shortcut.Save()
    Write-Host "Created shortcut: $shortcutPath"
}

# Ensure helper scripts exist
$textBat = Join-Path $repoRoot "scripts/Compack_Text.bat"
if (-not (Test-Path $textBat)) {
    Write-Host "Missing scripts/Compack_Text.bat" -ForegroundColor Yellow
}
$textVbs = Join-Path $repoRoot "scripts/Compack_Text.vbs"
if (-not (Test-Path $textVbs)) {
    Write-Host "Missing scripts/Compack_Text.vbs" -ForegroundColor Yellow
}

# Hidden launch via wscript
New-Shortcut -Name "Compack (Text)" -TargetPath "wscript.exe" -Arguments "`"$textVbs`"" -Description "Run Compack text mode (hidden console)"

# Debug/visible launch
New-Shortcut -Name "Compack (Text - Debug)" -TargetPath "cmd.exe" -Arguments "/c `"$textBat`"" -Description "Run Compack text mode with console"

Write-Host "Done. Shortcuts placed on Desktop." -ForegroundColor Green
