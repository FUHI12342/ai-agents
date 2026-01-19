$ErrorActionPreference = "Stop"

$repo = Resolve-Path "$PSScriptRoot\..\..\.."
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Compack.lnk"
$target = Join-Path $repo "apps\compack\scripts\windows\Compack.bat"
$iconPath = Join-Path $repo "apps\compack\assets\compack.ico"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $repo
if (Test-Path $iconPath) {
    $shortcut.IconLocation = $iconPath
}
$shortcut.Save()

Write-Host "Shortcut created at $shortcutPath"
