$ErrorActionPreference = "Stop"

$startup = [Environment]::GetFolderPath("Startup")
$linkPath = Join-Path $startup "Codex Pet Standalone.lnk"

if (Test-Path $linkPath) {
    Remove-Item $linkPath -Force
    Write-Host "Removed startup shortcut: $linkPath"
} else {
    Write-Host "Startup shortcut was not installed."
}
