#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""80mm x 80mm パネルの前面配置(モールス信号モジュール)。
座標: mm、原点=パネル左上、x右向き、y下向き。
検査(assert相当): パネル縁からの余裕、四隅12mm角の禁止領域との重なり、部品同士のすき間、
四隅の穴(Ø2.6、中心はパネル縁から9mm、2026-09-29確定)との重なり。合格したらASCII図と表を出力する。

    python tools/layout80.py                 # 標準出力に表示
    python tools/layout80.py out.md          # ファイルにも書く(設計メモ§2の図と表はこの出力)
"""
import math, sys

PANEL = 80.0
KEEP = 12.0               # ハブの規則: 四隅の12mm角に部品を置かない(2026-09-29確定、15mm角から縮小)
HOLE_D = 2.6              # 四隅のねじ穴(直径2.6mm、2026-09-29確定)
HOLE_INSET = 9.0          # 穴中心はパネル縁から9mm(=(80-62)/2、隣接穴間隔6.2cm、2026-09-29確定)
MIN_EDGE = 3.0            # このモジュールの規則: パネル縁から3mm以上
MIN_GAP = 2.0             # このモジュールの規則: 部品同士2mm以上

# 名前: (x0, y0, x1, y1, ラベル, 種別)  種別 'hw'=実部品 / 'print'=印刷のみ
parts = {
    "LAMP": (17.0,  8.0, 43.0, 18.0, "LAMP (amber tube 10x26)", "hw"),
    "STAT": (52.0,  8.0, 62.0, 18.0, "ST-LED", "hw"),
    "DISP": (14.85, 28.0, 65.15, 47.0, "4-digit 7seg OSL40562-IR 50.3x19", "hw"),
    "ARL":  (3.5,  33.0, 12.5, 42.0, "<", "hw"),
    "ARR":  (67.5, 33.0, 76.5, 42.0, ">", "hw"),
    "MHZ":  (54.0, 49.0, 65.0, 52.5, "MHz", "print"),
    "TX":   (30.0, 60.0, 50.0, 70.0, "TX (6mm tact)", "hw"),
}
corners = {
    "TL": (0.0, 0.0, KEEP, KEEP),
    "TR": (PANEL - KEEP, 0.0, PANEL, KEEP),
    "BL": (0.0, PANEL - KEEP, KEEP, PANEL),
    "BR": (PANEL - KEEP, PANEL - KEEP, PANEL, PANEL),
}


def overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return math.hypot(dx, dy)


def rect_circle_clearance(r, cx, cy, rad):
    px = min(max(cx, r[0]), r[2])
    py = min(max(cy, r[1]), r[3])
    return math.hypot(cx - px, cy - py) - rad


errors = []
for n, (x0, y0, x1, y1, *_r) in parts.items():
    m = min(x0, y0, PANEL - x1, PANEL - y1)
    if m < MIN_EDGE - 1e-9:
        errors.append("%s: パネル縁からの余裕 %.2f < %.1f" % (n, m, MIN_EDGE))
for n, p in parts.items():
    for cn, c in corners.items():
        if overlap(p[:4], c):
            errors.append("%s が四隅の禁止領域 %s に入っている" % (n, cn))
names = list(parts)
gaps = {}
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        a, b = parts[names[i]], parts[names[j]]
        g = gap(a[:4], b[:4])
        gaps[(names[i], names[j])] = g
        if g < MIN_GAP - 1e-9:
            errors.append("%s-%s のすき間 %.2f < %.1f" % (names[i], names[j], g, MIN_GAP))
hole_worst = {}
for n, p in parts.items():
    worst = 1e9
    for cx, cy in ((HOLE_INSET, HOLE_INSET), (PANEL - HOLE_INSET, HOLE_INSET),
                   (HOLE_INSET, PANEL - HOLE_INSET), (PANEL - HOLE_INSET, PANEL - HOLE_INSET)):
        worst = min(worst, rect_circle_clearance(p[:4], cx, cy, HOLE_D / 2))
    hole_worst[n] = worst
    if worst < 0:
        errors.append("%s が四隅の穴(縁から%.0fmm)と重なる %.2f" % (n, HOLE_INSET, worst))

if errors:
    print("配置エラー:")
    for e in errors:
        print("  ", e)
    sys.exit(1)

COLS, ROWS = int(PANEL), int(PANEL / 2)            # 横1文字=1mm、縦1行=2mm
grid = [[" "] * COLS for _ in range(ROWS)]

for r in range(ROWS):
    for c in range(COLS):
        x, y = c + 0.5, r * 2 + 1.0
        for k in corners.values():
            if k[0] <= x < k[2] and k[1] <= y < k[3]:
                grid[r][c] = ":"
        for cx, cy in ((HOLE_INSET, HOLE_INSET), (PANEL - HOLE_INSET, HOLE_INSET),
                       (HOLE_INSET, PANEL - HOLE_INSET), (PANEL - HOLE_INSET, PANEL - HOLE_INSET)):
            if math.hypot(x - cx, y - cy) <= HOLE_D / 2:
                grid[r][c] = "O"


def box(name):
    x0, y0, x1, y1, label, kind = parts[name]
    c0, c1 = int(round(x0)), int(round(x1)) - 1
    r0, r1 = int(round(y0 / 2)), int(round(y1 / 2)) - 1
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            edge_r, edge_c = r in (r0, r1), c in (c0, c1)
            if kind == "print":
                ch = "." if (edge_r or edge_c) else " "
            elif edge_r and edge_c:
                ch = "+"
            elif edge_r:
                ch = "-"
            elif edge_c:
                ch = "|"
            else:
                ch = " "
            grid[r][c] = ch
    inner = c1 - c0 - 1
    text = label[:inner]
    rr = (r0 + r1) // 2
    start = c0 + 1 + (inner - len(text)) // 2
    for i, chh in enumerate(text):
        grid[rr][start + i] = chh


for n in parts:
    box(n)

lines = ["      x(mm) " + "".join(str((c // 10) % 10) if c % 10 == 0 else "." if c % 5 == 0 else " " for c in range(COLS)),
         "            +" + "-" * COLS + "+"]
for r in range(ROWS):
    ylab = "%3d" % (r * 2) if (r * 2) % 10 == 0 else "   "
    lines.append("      y%s   |" % ylab + "".join(grid[r]) + "|")
lines.append("            +" + "-" * COLS + "+")
diagram = "\n".join(lines)

tbl = ["| 部品 | 種別 | X範囲(mm) | Y範囲(mm) | サイズ(mm) | パネル縁までの最小余裕 | 四隅の穴(Ø2.6、中心は縁から9mm)からの最小すき間 |",
       "|---|---|---|---|---|---:|---:|"]
for n, (x0, y0, x1, y1, label, kind) in parts.items():
    m = min(x0, y0, PANEL - x1, PANEL - y1)
    tbl.append("| %s | %s | %.2f〜%.2f | %.1f〜%.1f | %.1f×%.1f | %.1f | %.1f |" % (
        n, "実部品" if kind == "hw" else "印刷", x0, x1, y0, y1, x1 - x0, y1 - y0, m, hole_worst[n]))
gap_rows = ["| 部品の組 | すき間(mm) |", "|---|---:|"]
for (a, b), g in sorted(gaps.items(), key=lambda kv: kv[1])[:6]:
    gap_rows.append("| %s — %s | %.2f |" % (a, b, g))
hor = parts["DISP"][2] - parts["DISP"][0]
side_gap = parts["DISP"][0] - parts["ARL"][2]
budget = "横方向の収支: 表示器 %.2f + 矢印キャップ 9.0×2 + 表示器との隙間 %.2f×2 + パネル縁余裕 %.1f×2 = %.2f mm (= パネル幅 %.0f mm)" % (
    hor, side_gap, parts["ARL"][0], hor + 18 + 2 * side_gap + 2 * parts["ARL"][0], PANEL)

frag = """```text
%s
凡例:  :::  四隅12mm角の部品禁止領域   O  四隅の穴(Ø2.6、中心は縁から9mm、2026-09-29確定)
       +--+ 実部品(前面から見える大きさ)   ..... 印刷のみ(部品なし)
       縮尺: 横1文字=1mm、縦1行=2mm(文字が縦長のため、見た目はほぼ正方形になる)
```

%s

最も詰まっている部品間のすき間(小さい順):

%s

%s
""" % (diagram, "\n".join(tbl), "\n".join(gap_rows), budget)
if len(sys.argv) > 1:
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        f.write(frag)
print(frag)
print("配置の検査: 全て合格")
