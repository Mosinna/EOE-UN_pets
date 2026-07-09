# EOE-柚恩桌宠2.0

A standalone desktop pet for EOE 柚恩. The release package runs independently, so Codex does not need to be open.

柚恩桌宠是一只可以常驻在桌面上的轻量透明小助手。她会在桌面上陪你招手、工作、审阅和偶尔露出小失败表情，拖动时会切换奔跑动作，还能在原版、西装外套和西装背心三套造型之间切换。解压后直接运行，不需要打开 Codex，也不需要安装复杂依赖。

## Preview

下面是 2.0 新增两套西装造型的动图预览。GIF 使用浅色背景方便查看，实际运行时桌宠窗口是透明置顶的。

| 造型 | 招手 | 工作 | 审阅 | 失败 |
| --- | --- | --- | --- | --- |
| 西装外套 | ![西装外套招手](docs/previews/coat-on-waving.gif) | ![西装外套工作](docs/previews/coat-on-working.gif) | ![西装外套审阅](docs/previews/coat-on-review.gif) | ![西装外套失败](docs/previews/coat-on-failed.gif) |
| 西装背心 | ![西装背心招手](docs/previews/coat-off-waving.gif) | ![西装背心工作](docs/previews/coat-off-working.gif) | ![西装背心审阅](docs/previews/coat-off-review.gif) | ![西装背心失败](docs/previews/coat-off-failed.gif) |

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
- Windows startup helper scripts
- Experimental unsigned macOS app build

## Download

### Windows

Download `EOE-UN-pet-2.0.zip` from the `EOE-柚恩桌宠2.0` GitHub Release, unzip it, then double-click `CodexPet.exe`.

Optional helper scripts:

- `Install-Startup.ps1`: add a current-user startup shortcut
- `Uninstall-Startup.ps1`: remove the startup shortcut
- `Start-CodexPet.ps1`: start the pet manually

This is an unsigned Windows app, so SmartScreen may show a warning on first run.

### macOS

Use the unsigned Apple Silicon test package `EOE-UN-pet-2.0-macOS-unsigned.zip` when it is attached to a release or downloaded from a GitHub Actions build artifact. Unzip it, then open `EOE-柚恩桌宠2.0.app`.

This first macOS build is not signed or notarized. If Gatekeeper blocks the first launch, right-click the app, choose Open, then confirm. macOS settings and logs are stored in:

```text
~/Library/Application Support/EOE-UN-Pet/
```

## Run From Source

Windows:

```powershell
python -m pip install -r requirements.txt
python .\CodexPet.pyw
```

macOS Apple Silicon:

```bash
python3 -m pip install -r requirements.txt
python3 ./CodexPet.pyw
```

## Build

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

macOS Apple Silicon:

```bash
python3 -m pip install -r requirements.txt
bash ./scripts/build-macos.sh
```

Build outputs:

- Windows: `dist\CodexPet.exe`
- Windows zip: `dist\EOE-柚恩桌宠2.0.zip`
- macOS app: `dist-macos/EOE-柚恩桌宠2.0.app`
- macOS zip: `dist-macos/EOE-UN-pet-2.0-macOS-unsigned.zip`

## License

Launcher code is MIT licensed. Pet artwork and character assets are included only for this standalone desktop pet package and may be subject to separate rights and usage permissions.
