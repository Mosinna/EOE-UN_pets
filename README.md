# EOE-柚恩桌宠2.0

A standalone Windows desktop pet for EOE 柚恩. The release package runs independently, so Codex does not need to be open.

## Features

- Transparent always-on-top pet window
- Click to wave, drag horizontally to move with running animations, drag vertically to trigger jumping
- Hover near the pet to reveal a resize handle
- Drag the handle for continuous resizing
- Right-click to open the action menu for looping actions, random-action toggle, folder access, and quit
- Hold right-click and drag to open the wardrobe wheel for the original outfit, suit with coat, and suit without coat
- Click outside popups to close them
- Optional idle-only random actions play two loops, then return to idle
- Saves position, size, outfit, and random-action preference
- Optional per-user Windows startup helper scripts

## Download

Download `EOE-UN-pet-2.0.zip` from the `EOE-柚恩桌宠2.0` GitHub Release, unzip it, then double-click `CodexPet.exe`.

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
- `dist\EOE-柚恩桌宠2.0.zip`

## License

Launcher code is MIT licensed. Pet artwork and character assets are included only for this standalone desktop pet package and may be subject to separate rights and usage permissions.
