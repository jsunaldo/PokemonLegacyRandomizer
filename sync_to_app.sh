#!/bin/bash
# Syncs all randomizer source files into the .app bundle(s).
# Run this after any code change.

SRC="/Users/jsun/Library/CloudStorage/Dropbox/Gambling/Dan Green/Mario Baseball/Claude/crystal_legacy_randomizer"

# All known app locations — add new ones here if the app is copied elsewhere
APPS=(
  "$SRC/PokemonLegacyRandomizer.app/Contents/Resources/app"
  "/Users/jsun/Desktop/Test Randomizer/PokemonLegacyRandomizer.app/Contents/Resources/app"
)

FILES=(
  parser.py
  randomizer_engine.py
  writer.py
  item_data.py
  main.py
  constants.py
  constants_emerald.py
  constants_yellow.py
  static_data.py
  trade_data.py
  spoiler_log.py
  randomizer_engine_emerald.py
  randomizer_engine_yellow.py
  parser_emerald.py
  parser_yellow.py
  writer_emerald.py
  writer_yellow.py
  launcher_gui.py
)

for APP in "${APPS[@]}"; do
  if [ ! -d "$APP" ]; then
    echo "  [SKIP] Not found: $APP"
    continue
  fi
  echo "Syncing to: $APP"
  for f in "${FILES[@]}"; do
    if [ -f "$SRC/$f" ]; then
      cp "$SRC/$f" "$APP/$f"
      echo "  ✓ $f"
    fi
  done
  for html in crystal.html emerald.html yellow.html index.html; do
    if [ -f "$SRC/static/$html" ]; then
      cp "$SRC/static/$html" "$APP/static/$html"
      echo "  ✓ static/$html"
    fi
  done
done

echo "Sync complete."
