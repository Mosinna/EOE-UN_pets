# v2.0.0

EOE-柚恩桌宠2.0 release.

- Added wardrobe wheel with original outfit, suit with coat, and suit without coat
- Added suit sprite sheets and outfit persistence
- Fixed suit waving animation scale so the pet no longer shrinks during the wave
- Fixed suit-without-coat review animation scale so the review loop stays consistent with idle
- Switched packaged atlases to clean PNG files validated with Hatch Pet, removing hidden transparent-pixel RGB residue from the old WebP assets
- Added an experimental macOS compatibility path that keeps Tkinter, skips Windows-only APIs on macOS, stores macOS settings under `~/Library/Application Support/EOE-UN-Pet/`, and supports unsigned `.app` packaging
- Added GitHub Actions package builds for Windows plus macOS Apple Silicon runners
- Improved menu/window layering and display recovery
- Keeps transparent always-on-top desktop pet behavior, drag interactions, resizing, random actions, and startup helper scripts

# v1.0.0

Initial standalone Windows release.

- Transparent always-on-top desktop pet window
- Click, drag, action menu, continuous resize handle
- Optional random action every minute
- User-level startup helper scripts
- Single-file `CodexPet.exe` package with bundled sprite resources
