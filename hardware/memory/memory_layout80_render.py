# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from memory_layout80_check import parts, P, KEEP

CW, CH = 1.25, 2.5            # mm per column / per row  (char cell is 1:2, so the picture is to scale)
COLS, ROWS = int(P / CW), int(P / CH)   # 64 x 32
g = [[" "] * COLS for _ in range(ROWS)]

def c(x): return int(round(x / CW))
def r(y): return int(round(y / CH))

def put(row, col, s):
    for k, ch in enumerate(s):
        if 0 <= row < ROWS and 0 <= col + k < COLS:
            g[row][col + k] = ch

def box(x0, y0, x1, y1, fill=None):
    c0, c1, r0, r1 = c(x0), c(x1) - 1, r(y0), r(y1) - 1
    if r1 <= r0: r1 = r0 + 1
    for rr in range(r0, r1 + 1):
        for cc in range(c0, c1 + 1):
            edge = rr in (r0, r1) or cc in (c0, c1)
            if edge:
                corner = rr in (r0, r1) and cc in (c0, c1)
                g[rr][cc] = "+" if corner else ("-" if rr in (r0, r1) else "|")
            elif fill:
                g[rr][cc] = fill
    return c0, c1, r0, r1

# corner keep-out (15x15 = 12 cols x 6 rows) : hatch + assumed hole centre (7.5mm inset)
kc, kr = int(KEEP / CW), int(KEEP / CH)
for (c0, r0) in [(0, 0), (COLS - kc, 0), (0, ROWS - kr), (COLS - kc, ROWS - kr)]:
    for rr in range(r0, r0 + kr):
        for cc in range(c0, c0 + kc):
            g[rr][cc] = "/"
    # hole d=10mm (8 cols x 4 rows) centred 7.5mm from both edges
    hc = c0 + (kc // 2 - 1) if c0 == 0 else c0 + kc // 2 - 1
    hr = r0 + kr // 2 - 1
    hx = 7.5 / CW; hy = 7.5 / CH
    for rr in range(r0, r0 + kr):
        for cc in range(c0, c0 + kc):
            xx = (cc + 0.5) * CW - (0 if c0 == 0 else (P - KEEP)); yy = (rr + 0.5) * CH - (0 if r0 == 0 else (P - KEEP))
            # local coords inside the 15x15 square; hole centre at (7.5,7.5)
            if (xx - 7.5) ** 2 + (yy - 7.5) ** 2 <= 5.0 ** 2:
                g[rr][cc] = "O"

# parts
b = parts["main bezel"];       box(*b[1:], fill=None)
put(r(b[2]) + 1, c(24) + 2, "MAIN")
d = parts["main digit"]; box(*d[1:], fill=None)
put(r(d[2]) + 2, c(d[1]) + 3, "8")

bar = parts["lamp bar"]; box(*bar[1:])
for i in range(5):
    cx = 28.0 + 6.0 * i
    put(r(parts["stage lamp 1"][2]), c(cx) - 0, "o")

for i in range(4):
    dg = parts[f"btn{i+1} label digit"]; sw = parts[f"btn{i+1} tact switch (12x12)"]
    cx = (sw[1] + sw[3]) / 2
    ccen = int(round(cx / CW))
    # fixed widths so equal parts look equal: switch cap 10 cols (~12.5mm), digit body 8 cols (~10mm)
    sc0 = 11 + 11 * i; sc1 = sc0 + 9
    dc0, dc1 = sc0 + 1, sc0 + 8     # digit body 10mm = 8 cols, centred on the 10-col switch cap
    r0s, r1s = r(sw[2]), r(sw[4]) - 1
    r0d, r1d = r(dg[2]), r(dg[4]) - 1
    for (a0, a1, b0, b1) in [(sc0, sc1, r0s, r1s), (dc0, dc1, r0d, r1d)]:
        for rr in range(b0, b1 + 1):
            for cc in range(a0, a1 + 1):
                edge = rr in (b0, b1) or cc in (a0, a1)
                if edge:
                    corner = rr in (b0, b1) and cc in (a0, a1)
                    g[rr][cc] = "+" if corner else ("-" if rr in (b0, b1) else "|")
    put(r0d + 2, dc0 + 3, "8")
    put(r0s + 1, sc0 + 3, f"B{i+1}")

put(r(8), c(60) - 1, "(G)")

# panel frame
out = []
out.append("     0        10        20        30        40        50        60        70       80 mm")
out.append("     +" + "-" * COLS + "+")
for rr in range(ROWS):
    label = f"{rr*CH:4.0f} " if rr % 4 == 0 else "     "
    out.append(label + "|" + "".join(g[rr]) + "|")
out.append("     +" + "-" * COLS + "+")
print("\n".join(out))
