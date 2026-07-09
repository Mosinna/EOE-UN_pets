#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist-macos"
BUILD="$ROOT/build-macos"
PACKAGE="$BUILD/package"
APP_NAME="EOE-柚恩桌宠2.0"
ZIP_NAME="EOE-UN-pet-2.0-macOS-unsigned.zip"

rm -rf "$DIST" "$BUILD"
mkdir -p "$DIST" "$PACKAGE"

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --exclude-module numpy \
  --exclude-module matplotlib \
  --exclude-module pandas \
  --exclude-module scipy \
  --exclude-module PIL.ImageQt \
  --exclude-module PyQt5 \
  --exclude-module PyQt6 \
  --exclude-module PySide2 \
  --exclude-module PySide6 \
  --add-data "$ROOT/assets:assets" \
  --distpath "$DIST" \
  --workpath "$BUILD" \
  --specpath "$BUILD" \
  "$ROOT/CodexPet.pyw"

cp -R "$DIST/$APP_NAME.app" "$PACKAGE/"
cp "$ROOT/README.md" "$PACKAGE/README.md"
cp "$ROOT/RELEASE_NOTES.md" "$PACKAGE/RELEASE_NOTES.md"
cp "$ROOT/LICENSE" "$PACKAGE/LICENSE"
if [ -d "$ROOT/docs" ]; then
  cp -R "$ROOT/docs" "$PACKAGE/docs"
fi

(
  cd "$PACKAGE"
  /usr/bin/zip -r "$DIST/$ZIP_NAME" "$APP_NAME.app" README.md RELEASE_NOTES.md LICENSE docs
)

echo "Built: $DIST/$APP_NAME.app"
echo "Packed: $DIST/$ZIP_NAME"
