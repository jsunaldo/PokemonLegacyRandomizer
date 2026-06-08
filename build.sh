#!/bin/bash
# build.sh — Build the Pokemon Legacy Randomizer into a self-contained macOS .app
# Requires: pip3 install pyinstaller

set -e
cd "$(dirname "$0")"

APP_NAME="PokemonLegacyRandomizer"

echo "=== Cleaning previous build ==="
rm -rf build dist "${APP_NAME}.spec"

echo "=== Building .app with PyInstaller ==="
# Use full path since ~/Library/Python/3.9/bin may not be on PATH
PYINSTALLER="${HOME}/Library/Python/3.9/bin/pyinstaller"
"${PYINSTALLER}" \
  --name "${APP_NAME}" \
  --windowed \
  --add-data "static:static" \
  --hidden-import parser \
  --hidden-import randomizer_engine \
  --hidden-import writer \
  --hidden-import item_data \
  --hidden-import constants \
  --hidden-import constants_emerald \
  --hidden-import constants_yellow \
  --hidden-import static_data \
  --hidden-import trade_data \
  --hidden-import randomizer_engine_emerald \
  --hidden-import randomizer_engine_yellow \
  --hidden-import parser_emerald \
  --hidden-import parser_yellow \
  --hidden-import writer_emerald \
  --hidden-import writer_yellow \
  --hidden-import spoiler_log \
  --noconfirm \
  launcher_gui.py

echo "=== Creating release zip ==="
cd dist
zip -r "../${APP_NAME}.zip" "${APP_NAME}.app"
cd ..

echo ""
echo "Done! Built:"
echo "  dist/${APP_NAME}.app   — run locally to test"
echo "  ${APP_NAME}.zip        — upload this as a GitHub Release asset"
