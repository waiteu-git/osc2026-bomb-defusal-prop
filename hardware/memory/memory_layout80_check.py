# -*- coding: utf-8 -*-
"""80mm-square panel layout check + ASCII render for the Memory module.
Coordinates: mm, origin top-left, x right, y down. Panel = 80 x 80.
"""
import math

P = 80.0
KEEP = 15.0          # hub rule: no parts in the 15x15 corner squares
HOLE_R = 5.0         # corner screw hole diameter 10mm
EDGE_MARGIN = 3.0    # my own assumption for enclosure wall / bezel

# --- parts as ("rect", x0,y0,x1,y1) or ("circle", cx,cy,r) ---
# Variant selection:  python memory_layout80_check.py [osl10326 | osl10391]
#   osl10391 : OSL10391-IRA  body 10.0 x 13.0 (pin pitch 2.54mm, row spacing 7.52mm)  <- ADOPTED (default), current schematic/BOM
#   osl10326 : OSL10326-IRA  body 7.0 x 11.0 (pin pitch 2.0mm -> does NOT fit 2.54mm boards) <- superseded, kept for comparison
import sys
VARIANT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("osl10326", "osl10391") else "osl10391"
DIG_W, DIG_H = (7.0, 11.0) if VARIANT == "osl10326" else (10.0, 13.0)
# vertical positions: bezel/lamp bar shift up by 2mm for the taller 13mm digit so the tile row keeps the same bottom edge
DY = 0.0 if VARIANT == "osl10326" else -2.0

parts = {}
LED_R = 1.5          # 3mm LED (5mm LED checked separately below)
parts["status LED (green)"] = ("circle", 60.0, 8.0, LED_R)
parts["main bezel"] = ("rect", 24.0, 11.0 + DY, 56.0, 29.0 + DY)
parts["main digit"] = ("rect", 40.0 - DIG_W / 2, 20.0 + DY - DIG_H / 2, 40.0 + DIG_W / 2, 20.0 + DY + DIG_H / 2)
parts["lamp bar"] = ("rect", 25.0, 31.0 + DY, 55.0, 36.0 + DY)
for i in range(5):
    parts[f"stage lamp {i+1}"] = ("circle", 28.0 + 6.0 * i, 33.5 + DY, 2.5)   # 5mm LED (BOM default); 3mm also fits

TILE_W, TILE_PITCH = 12.0, 13.5
x_first = 40.0 - (4 * TILE_W + 3 * (TILE_PITCH - TILE_W)) / 2
for i in range(4):
    x0 = x_first + TILE_PITCH * i
    cx = x0 + TILE_W / 2
    parts[f"btn{i+1} label digit"] = ("rect", cx - DIG_W / 2, 50.5 - 1.5 - DIG_H, cx + DIG_W / 2, 50.5 - 1.5)
    parts[f"btn{i+1} tact switch (12x12)"] = ("rect", x0, 50.5, x0 + TILE_W, 62.5)


def bbox(p):
    if p[0] == "rect":
        return p[1], p[2], p[3], p[4]
    _, cx, cy, r = p
    return cx - r, cy - r, cx + r, cy + r


def rect_circle_dist(rect, c, r):
    x0, y0, x1, y1 = rect
    cx, cy = c
    dx = max(x0 - cx, 0, cx - x1)
    dy = max(y0 - cy, 0, cy - y1)
    return math.hypot(dx, dy) - r   # >0 : clear gap


def part_hole_gap(p, d):
    """min gap between part p and the 4 corner holes whose centers sit d mm from both edges."""
    b = bbox(p)
    best = 1e9
    for (hx, hy) in [(d, d), (P - d, d), (d, P - d), (P - d, P - d)]:
        if p[0] == "rect":
            g = rect_circle_dist(b, (hx, hy), HOLE_R)
        else:
            g = math.hypot(hx - p[1], hy - p[2]) - p[3] - HOLE_R
        best = min(best, g)
    return best


def in_keepout(p):
    x0, y0, x1, y1 = bbox(p)
    for (kx0, ky0) in [(0, 0), (P - KEEP, 0), (0, P - KEEP), (P - KEEP, P - KEEP)]:
        if x0 < kx0 + KEEP and x1 > kx0 and y0 < ky0 + KEEP and y1 > ky0:
            return True
    return False


def overlap(a, b):
    ax0, ay0, ax1, ay1 = bbox(a)
    bx0, by0, bx1, by1 = bbox(b)
    return ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0


if __name__ == "__main__":
    print("variant:", VARIANT, " digit body %.1f x %.1f" % (DIG_W, DIG_H))
    print("== keep-out (15x15 corners) violations ==")
    bad = [n for n, p in parts.items() if in_keepout(p)]
    print(bad or "none")

    print("== edge margin (min distance to panel edge) ==")
    worst = min(min(bbox(p)[0], bbox(p)[1], P - bbox(p)[2], P - bbox(p)[3]) for p in parts.values())
    print("min edge distance = %.2f mm" % worst)

    print("== unexpected overlaps (excluding contained digit-in-bezel / lamp-in-bar) ==")
    names = list(parts)
    allowed = {("main bezel", "main digit OSL (7x11)"), ("lamp bar",)}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if overlap(parts[a], parts[b]):
                if a == "main bezel" and b == "main digit":
                    continue
                if a == "lamp bar" and b.startswith("stage lamp"):
                    continue
                print("OVERLAP:", a, "<->", b)
    print("(done)")

    print("== min gap to corner holes vs hole-center inset d ==")
    for d in [5, 6, 7, 7.5, 8, 9, 10, 11, 11.5, 12, 13, 15]:
        gaps = {n: part_hole_gap(p, d) for n, p in parts.items()}
        n, g = min(gaps.items(), key=lambda kv: kv[1])
        print("d=%5.1f  min gap=%6.2f mm  (closest: %s)" % (d, g, n))

    # find max d with gap >= 0 and gap >= 1mm
    for thr in (0.0, 1.0):
        dmax = None
        d = 5.0
        while d <= 20.0:
            if min(part_hole_gap(p, d) for p in parts.values()) >= thr:
                dmax = d
            d += 0.05
        print("max hole-center inset with gap >= %.1f mm : %.2f mm" % (thr, dmax))

    print("== 5mm status LED variant ==")
    p5 = ("circle", 60.0, 8.0, 2.5)
    print("keepout viol:", in_keepout(p5), " gap to hole at d=7.5: %.2f" % part_hole_gap(p5, 7.5),
          " overlap w/ bezel:", overlap(p5, parts["main bezel"]))
