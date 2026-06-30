$ErrorActionPreference = "Stop"

$exe = Join-Path $PSScriptRoot "CodexPet.exe"
if (-not (Test-Path $exe)) {
    throw "CodexPet.exe was not found next to this script."
}

Start-Process -FilePath $exe -WorkingDirectory $PSScriptRoot
