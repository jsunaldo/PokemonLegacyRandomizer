#!/usr/bin/env python3
"""
Remove a solid (border-connected) background from an image and save as a
transparent PNG.

Uses an edge flood-fill seeded from the four corners, so it only erases the
background that touches the image border — interior whites (logo text, the
rating box, Pikachu's belly, etc.) are preserved. Works for white OR black
or any uniform background (the corner colour is sampled automatically).

Usage:
    python3 remove_bg.py INPUT OUTPUT [threshold]

threshold (default 50) is how far a pixel's colour may differ from the
background and still be treated as background. Raise it if a halo remains;
lower it if it eats into the cartridge.
"""
import sys
from PIL import Image, ImageDraw


def remove_bg(inp, outp, thresh=50):
    im = Image.open(inp).convert("RGBA")
    w, h = im.size
    rgb = im.convert("RGB")
    SENT = (1, 254, 1)  # unlikely sentinel colour
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
                 (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        ImageDraw.floodfill(rgb, seed, SENT, thresh=thresh)
    flooded = rgb.load()
    src = im.load()
    out = Image.new("RGBA", (w, h))
    op = out.load()
    cleared = 0
    for y in range(h):
        for x in range(w):
            if flooded[x, y] == SENT:
                op[x, y] = (0, 0, 0, 0)
                cleared += 1
            else:
                op[x, y] = src[x, y]
    out.save(outp)
    pct = 100.0 * cleared / (w * h)
    print(f"{inp} -> {outp}  ({w}x{h}, {pct:.1f}% made transparent)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    th = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    remove_bg(sys.argv[1], sys.argv[2], th)
