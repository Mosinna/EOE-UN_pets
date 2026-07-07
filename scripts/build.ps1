$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist"
$build = Join-Path $root "build"
$exe = Join-Path $dist "CodexPet.exe"
$releaseZipName = "EOE-" + [char]0x67DA + [char]0x6069 + [char]0x684C + [char]0x5BA0 + "2.0.zip"
$zip = Join-Path $dist $releaseZipName

if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
if (Test-Path $build) { Remove-Item $build -Recurse -Force }
New-Item -ItemType Directory -Path $dist | Out-Null

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name CodexPet `
    --exclude-module numpy `
    --exclude-module matplotlib `
    --exclude-module pandas `
    --exclude-module scipy `
    --exclude-module PIL.ImageQt `
    --exclude-module PyQt5 `
    --exclude-module PyQt6 `
    --exclude-module PySide2 `
    --exclude-module PySide6 `
    --add-data "$root\assets;assets" `
    --distpath $dist `
    --workpath $build `
    --specpath $build `
    "$root\CodexPet.pyw"

Copy-Item (Join-Path $root "README.md") (Join-Path $dist "README.md") -Force
Copy-Item (Join-Path $root "Install-Startup.ps1") (Join-Path $dist "Install-Startup.ps1") -Force
Copy-Item (Join-Path $root "Start-CodexPet.ps1") (Join-Path $dist "Start-CodexPet.ps1") -Force
Copy-Item (Join-Path $root "Uninstall-Startup.ps1") (Join-Path $dist "Uninstall-Startup.ps1") -Force

if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $dist "*") -DestinationPath $zip -Force

Write-Host "Built: $exe"
Write-Host "Packed: $zip"
