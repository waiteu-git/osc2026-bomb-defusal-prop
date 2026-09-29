# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
from complicated_wires_layout80_check import build, P, KEEP, PARAMS, TERMINAL_GROUPS

CW, CH = 1.25, 2.5            # mm per column / per row (文字セルは縦横1:2なので縮尺どおりの図になる)
COLS, ROWS = int(P / CW), int(P / CH)   # 64 x 32
g = [[" "] * COLS for _ in range(ROWS)]


def c(x):
    return int(round(x / CW))


def r(y):
    return int(round(y / CH))


def put(row, col, s):
    for k, ch in enumerate(s):
        if 0 <= row < ROWS and 0 <= col + k < COLS:
            g[row][col + k] = ch


def box(x0, y0, x1, y1, label=None, fill=None):
    c0, c1, r0, r1 = c(x0), c(x1) - 1, r(y0), r(y1) - 1
    if c1 <= c0:
        c1 = c0 + 1
    if r1 <= r0:
        r1 = r0 + 1
    for rr in range(r0, r1 + 1):
        for cc in range(c0, c1 + 1):
            edge = rr in (r0, r1) or cc in (c0, c1)
            if edge:
                corner = rr in (r0, r1) and cc in (c0, c1)
                g[rr][cc] = "+" if corner else ("-" if rr in (r0, r1) else "|")
            elif fill:
                g[rr][cc] = fill
    if label:
        put((r0 + r1) // 2, (c0 + c1) // 2 - len(label) // 2 + (0 if len(label) % 2 else 1), label)


def render(p=PARAMS):
    parts, wire_len = build(p)
    kc, kr = int(KEEP / CW), int(KEEP / CH)
    for (c0, r0) in [(0, 0), (COLS - kc, 0), (0, ROWS - kr), (COLS - kc, ROWS - kr)]:
        for rr in range(r0, r0 + kr):
            for cc in range(c0, c0 + kc):
                g[rr][cc] = "/"
                xx = (cc + 0.5) * CW - (0 if c0 == 0 else (P - KEEP))
                yy = (rr + 0.5) * CH - (0 if r0 == 0 else (P - KEEP))
                if (xx - 7.5) ** 2 + (yy - 7.5) ** 2 <= 5.0 ** 2:
                    g[rr][cc] = "O"
    for i in range(1, 7):
        lane = parts[f"W{i} wire lane"]
        cc = c((lane[1] + lane[3]) / 2)
        for rr in range(r(lane[2]), r(lane[4])):
            put(rr, cc, ":")
    for group in TERMINAL_GROUPS:
        label = "".join(str(n) for n in group)
        s = next(v for n, v in parts.items() if n.startswith(f"S{label} signal"))
        gb = next(v for n, v in parts.items() if n.startswith(f"G{label} GND"))
        box(*s[1:], label="S" + label)
        box(*gb[1:], label="G" + label)
    for i in range(1, 7):
        box(*parts[f"W{i} Top NeoPixel"][1:], label="N")
        box(*parts[f"W{i} Star NeoPixel"][1:], label="N")
    st = parts["status LED (green)"]
    put(r(st[2]), c(st[1]) - 1, "(G)")
    out = ["     0        10        20        30        40        50        60        70       80 mm",
           "     +" + "-" * COLS + "+"]
    for rr in range(ROWS):
        label = f"{rr * CH:4.0f} " if rr % 4 == 0 else "     "
        out.append(label + "|" + "".join(g[rr]) + "|")
    out.append("     +" + "-" * COLS + "+")
    print("\n".join(out))
    print("visible wire length = %.1f mm" % wire_len)


if __name__ == "__main__":
    render()
