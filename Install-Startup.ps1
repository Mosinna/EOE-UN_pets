$ErrorActionPreference = "Stop"

$exe = Join-Path $PSScriptRoot "CodexPet.exe"
if (-not (Test-Path $exe)) {
    throw "CodexPet.exe was not found next to this script."
}

$startup = [Environment]::GetFolderPath("Startup")
$linkPath = Join-Path $startup "Codex Pet Standalone.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($linkPath)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.IconLocation = "$exe,0"
$shortcut.Description = "Start the standalone Codex desktop pet."
$shortcut.Save()

Write-Host "Installed startup shortcut: $linkPath"
