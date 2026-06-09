#!/usr/bin/env python3
"""
Remove a solid (border-connected) background from an image and save as a
transparent PNG.

Uses an edge flood-fill seeded from the four corners, so it only erases the
background that touches the image border — interior whites (logo text, the
rating box, Pikachu's belly, etc.) are preserved. Works for white OR black
or any uniform background (the corner colour is sampled automatically).

After the flood fill, only the largest connected opaque region is kept by
default, which removes detached leftovers like reflection/shadow lines from
product photos. Pass --no-clean to skip that step.

Usage:
    python3 remove_bg.py INPUT OUTPUT [threshold] [--no-clean]

threshold (default 50) is how far a pixel's colour may differ from the
background and still be treated as background. Raise it if a halo remains;
lower it if it eats into the subject.
"""
import sys
from collections import deque

from PIL import Image, ImageDraw


def remove_bg(inp, outp, thresh=50, clean=True):
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

    stray = 0
    if clean:
        stray = _keep_largest_blob(out)

    out.save(outp)
    pct = 100.0 * cleared / (w * h)
    msg = f"{inp} -> {outp}  ({w}x{h}, {pct:.1f}% made transparent"
    msg += f", {stray} stray px cleaned)" if clean else ")"
    print(msg)


def _keep_largest_blob(im):
    """Erase every opaque region except the largest connected one.
    Returns the number of stray pixels cleared."""
    w, h = im.size
    px = im.load()
    opaque = [[px[x, y][3] > 0 for x in range(w)] for y in range(h)]
    seen = [[False] * w for _ in range(h)]
    best = []
    for y in range(h):
        for x in range(w):
            if opaque[y][x] and not seen[y][x]:
                comp = []
                dq = deque([(x, y)])
                seen[y][x] = True
                while dq:
                    cx, cy = dq.popleft()
                    comp.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and opaque[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = True
                            dq.append((nx, ny))
                if len(comp) > len(best):
                    best = comp
    keep = set(best)
    cleared = 0
    for y in range(h):
        for x in range(w):
            if opaque[y][x] and (x, y) not in keep:
                px[x, y] = (0, 0, 0, 0)
                cleared += 1
    return cleared


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--no-clean"]
    clean = "--no-clean" not in sys.argv
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    th = int(args[2]) if len(args) > 2 else 50
    remove_bg(args[0], args[1], th, clean)
