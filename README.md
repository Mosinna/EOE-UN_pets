# Codex Pet Standalone

A standalone Windows desktop pet extracted from Codex pet assets. The release package runs independently, so Codex does not need to be open.

## Features

- Transparent always-on-top pet window
- Click to wave, drag to move
- Hover near the pet to reveal a resize handle
- Drag the handle for continuous resizing
- Right-click rounded menu for actions, random-action toggle, folder access, and quit
- Saves position, size, and random-action preference
- Optional per-user Windows startup helper scripts

## Download

Download `CodexPetStandalone-share.zip` from GitHub Releases, unzip it, then double-click `CodexPet.exe`.

Optional helper scripts:

- `Install-Startup.ps1`: add a current-user startup shortcut
- `Uninstall-Startup.ps1`: remove the startup shortcut
- `Start-CodexPet.ps1`: start the pet manually

This is an unsigned Windows app, so SmartScreen may show a warning on first run.

## Run From Source

```powershell
python -m pip install -r requirements.txt
python .\CodexPet.pyw
```

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

Build outputs:

- `dist\CodexPet.exe`
- `dist\CodexPetStandalone-share.zip`

## License

Launcher code is MIT licensed. Pet artwork and character assets are included only for this standalone desktop pet package and may be subject to separate rights and usage permissions.
