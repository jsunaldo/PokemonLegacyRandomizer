#!/bin/bash
# Sync the latest Python source files into the .app bundle.
# Run this after making any code changes so the double-click app stays up to date.

SRC="$(cd "$(dirname "$0")" && pwd)"
BUNDLE="$SRC/CrystalLegacyRandomizer.app"
DEST="$BUNDLE/Contents/Resources/app"

if [ ! -d "$BUNDLE" ]; then
    echo "ERROR: App bundle not found at $BUNDLE"
    exit 1
fi

echo "Syncing source → bundle..."

for f in main.py launcher_gui.py \
          parser.py constants.py randomizer_engine.py writer.py \
          parser_yellow.py constants_yellow.py randomizer_engine_yellow.py writer_yellow.py \
          parser_emerald.py constants_emerald.py randomizer_engine_emerald.py writer_emerald.py \
          item_data.py trade_data.py static_data.py; do
    cp "$SRC/$f" "$DEST/$f" && echo "  ✓ $f"
done

# Sync static web UI
rsync -a --delete "$SRC/static/" "$DEST/static/" && echo "  ✓ static/"

touch "$BUNDLE"
echo ""
echo "Done. The app is ready to double-click."
