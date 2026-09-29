# Password module: 80mm-square panel layout checker + ASCII diagram generator.
# password_design_notes.md 2章の座標・検証値(禁止域ヒット/穴中心の許容/文字ピッチ)はこのスクリプトの出力。
# 2026-09-29更新: 取付穴の実寸が確定(ハブ連絡事項.md)。直径2.6mm、中心はパネル縁から9mm
# (隣り合う穴の間隔62mmになるよう配置)。旧「直径10mm・中心未確認」は撤回。
# キープアウト15mm角は根拠(ねじ頭・座金寸法)待ちのため現状維持。
# 使い方: python panel_layout_check.py   (標準出力は日本語を含まないが、環境によっては PYTHONIOENCODING=utf-8 推奨)
#!/usr/bin/env python3
# 80mm-square panel layout check + ASCII diagram generator.
# Origin: top-left, x -> right, y -> down (mm).
import math

W = H = 80.0
KEEP = 15.0        # corner keep-out square (kept as-is pending screw-head/washer rationale, 2026-09-29)
HOLE_R = 1.3       # confirmed 2026-09-29: hole diameter 2.6mm -> radius 1.3mm
HOLE_INSET = 9.0   # confirmed 2026-09-29: hole centre is 9mm from panel edge (62mm between adjacent holes)
BTN = 6.2          # DTS-63 body
OLED_W, OLED_H = 27.0, 24.7   # Akizuki 112031 module outline
WIN_W, WIN_H = 21.7, 10.9     # typical 0.96in active area (NOT on Akizuki page; unverified)

def rect(cx, cy, w, h):
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

def build(pitch, up_y, down_y, oled_cy, sub_y, led=(58.0, 8.0)):
    xs = [W / 2 + pitch * k for k in (-2, -1, 0, 1, 2)]
    parts = {}
    for i, x in enumerate(xs, 1):
        parts[f"UP{i}"] = rect(x, up_y, BTN, BTN)
        parts[f"DOWN{i}"] = rect(x, down_y, BTN, BTN)
    parts["OLED"] = rect(W / 2, oled_cy, OLED_W, OLED_H)
    parts["SUBMIT"] = rect(W / 2, sub_y, BTN, BTN)
    parts["LED"] = rect(led[0], led[1], 5.0, 5.0)
    return parts

def keepout_hits(parts):
    ko = [(0, 0, KEEP, KEEP), (W - KEEP, 0, W, KEEP), (0, H - KEEP, KEEP, H), (W - KEEP, H - KEEP, W, H)]
    hits = []
    for n, (x0, y0, x1, y1) in parts.items():
        for k in ko:
            if x0 < k[2] and x1 > k[0] and y0 < k[3] and y1 > k[1]:
                hits.append((n, k))
    return hits

def dist_pt_rect(px, py, r):
    x0, y0, x1, y1 = r
    dx = max(x0 - px, 0, px - x1)
    dy = max(y0 - py, 0, py - y1)
    return math.hypot(dx, dy)

def c_max(parts):
    """largest symmetric hole-centre inset c (from both edges) such that every part clears the phi10 hole."""
    best = None
    c = 5.0
    while c <= 30.0:
        ok = True
        for (hx, hy) in [(c, c), (W - c, c), (c, H - c), (W - c, H - c)]:
            for n, r in parts.items():
                if dist_pt_rect(hx, hy, r) < HOLE_R:
                    ok = False
        if ok:
            best = c
        else:
            if best is not None and c > best + 0.5:
                pass
        c = round(c + 0.1, 3)
    return best

def c_first_fail(parts):
    c = 5.0
    while c <= 30.0:
        for (hx, hy) in [(c, c), (W - c, c), (c, H - c), (W - c, H - c)]:
            for n, r in parts.items():
                if dist_pt_rect(hx, hy, r) < HOLE_R:
                    return round(c, 1), n
        c = round(c + 0.1, 3)
    return None

# chosen layout: vertical block centred on y=40 -> symmetric 17.5mm from top/bottom edge
block_h = BTN + 4.0 + OLED_H + 4.0 + BTN     # 45.1
top = H / 2 - block_h / 2
up_y = top + BTN / 2
oled_cy = top + BTN + 4.0 + OLED_H / 2
down_y = top + BTN + 4.0 + OLED_H + 4.0 + BTN / 2
sub_y = 72.0
print(f"block_h={block_h:.1f} top={top:.2f} up_y={up_y:.2f} oled_cy={oled_cy:.2f} down_y={down_y:.2f} bottom={top+block_h:.2f}")

def part_limits(parts):
    res = {}
    for n, r in parts.items():
        lim = None
        c = 5.0
        while c <= 30.0:
            bad = any(dist_pt_rect(hx, hy, r) < HOLE_R for (hx, hy) in
                      [(c, c), (W - c, c), (c, H - c), (W - c, H - c)])
            if bad:
                lim = round(c - 0.1, 1); break
            c = round(c + 0.1, 3)
        res[n] = lim
    return res

for pitch in (16.0, 15.0, 14.0, 10.0):
    parts = build(pitch, up_y, down_y, oled_cy, sub_y)
    xs = [W / 2 + pitch * k for k in (-2, 2)]
    edge_margin = xs[0] - BTN / 2
    print(f"pitch {pitch}: outer button edge margin to panel edge = {edge_margin:.2f} mm, "
          f"body gap = {pitch-BTN:.1f} mm, keepout hits = {keepout_hits(parts)}, "
          f"hole-centre-inset limit per part (mm, None=ok to 30, phi2.6): "
          f"{ {k: v for k, v in part_limits(parts).items() if k in ('UP1','DOWN1','LED','SUBMIT','OLED')} }")

# ---- 2026-09-29: check against the now-confirmed hole model (phi2.6, inset 9mm) ----
parts16 = build(16.0, up_y, down_y, oled_cy, sub_y)
confirmed_holes = [(HOLE_INSET, HOLE_INSET), (W - HOLE_INSET, HOLE_INSET),
                    (HOLE_INSET, H - HOLE_INSET), (W - HOLE_INSET, H - HOLE_INSET)]
print(f"\n--- confirmed hole check (phi{2*HOLE_R}mm, inset {HOLE_INSET}mm from edge) ---")
worst_margin = None
for n, r in parts16.items():
    dmin = min(dist_pt_rect(hx, hy, r) for (hx, hy) in confirmed_holes)
    margin = dmin - HOLE_R
    if worst_margin is None or margin < worst_margin:
        worst_margin = margin
    if margin < 5.0:  # only print parts anywhere near a corner
        print(f"  {n}: clearance to nearest hole edge = {margin:.2f} mm "
              f"({'OK' if margin >= 0 else 'COLLISION'})")
print(f"  worst-case clearance across all parts = {worst_margin:.2f} mm "
      f"({'no collision' if worst_margin >= 0 else 'COLLISION FOUND'})")

parts = build(16.0, up_y, down_y, oled_cy, sub_y)
print("UP body y:", round(parts['UP1'][1], 2), round(parts['UP1'][3], 2))
print("OLED board y:", round(parts['OLED'][1], 2), round(parts['OLED'][3], 2), "x:", parts['OLED'][0], parts['OLED'][2])
print("DOWN body y:", round(parts['DOWN1'][1], 2), round(parts['DOWN1'][3], 2))
print("SUBMIT:", [round(v, 2) for v in parts['SUBMIT']])
print("LED:", [round(v, 2) for v in parts['LED']], "gap to right keep-out x=65:", round(65 - parts['LED'][2], 2))
print("gap UP->OLED:", round(parts['OLED'][1] - parts['UP1'][3], 2), " OLED->DOWN:", round(parts['DOWN1'][1] - parts['OLED'][3], 2))
win_top = oled_cy - WIN_H / 2
print("gap UP bottom -> visible window top (window centred on board):", round(win_top - parts['UP1'][3], 2))
print("letter pitch on 0.96in window:", round(WIN_W / 5, 2), "mm ; centres span:", round(WIN_W / 5 * 4, 1), "mm ; button centre span @16:", 64)

# ---------------- ASCII diagram: 1 col = 1 mm, 1 line = 2 mm ----------------
cols, lines = 80, 40
g = [[" "] * cols for _ in range(lines)]

def put(col, line, s):
    for i, ch in enumerate(s):
        if 0 <= col + i < cols and 0 <= line < lines:
            g[line][col + i] = ch

def box(c0, l0, w, hgt, fill=None, border=("+", "-", "|")):
    corner, hor, ver = border
    for j in range(w):
        put(c0 + j, l0, hor); put(c0 + j, l0 + hgt - 1, hor)
    for i in range(hgt):
        put(c0, l0 + i, ver); put(c0 + w - 1, l0 + i, ver)
    for c in (c0, c0 + w - 1):
        for l in (l0, l0 + hgt - 1):
            put(c, l, corner)

# corner keep-out (drawn 16mm x 16mm: 2mm/line rounding, conservative)
for l in range(0, 8):
    for c in range(0, 15):
        put(c, l, "#")
        put(cols - 1 - c, l, "#")
        put(c, lines - 1 - l, "#")
        put(cols - 1 - c, lines - 1 - l, "#")
put(2, 3, "hole"); put(2, 4, "phi2.6")
put(cols - 8, 3, "hole"); put(cols - 8, 4, "phi2.6")
put(2, lines - 5, "hole"); put(2, lines - 4, "phi2.6")
put(cols - 8, lines - 5, "hole"); put(cols - 8, lines - 4, "phi2.6")

# buttons
def button(cx_mm, cy_mm, sym):
    c0 = int(round(cx_mm - 3)); l0 = int(round(cy_mm / 2 - 1.5))
    box(c0, l0, 6, 3)
    put(c0 + 2, l0 + 1, sym)

for k in range(5):
    x = 40 + 16 * (k - 2)
    button(x, 21, "^")
    button(x, 59, "v")
button(40, 71, "S")

# OLED board (28 cols x 12 lines ~ 27 x 24.7mm) + visible window (22 cols x 6 lines)
box(26, 14, 28, 12)
box(29, 17, 22, 6)
put(30, 19, " A   A   A   A   A  ")
put(30, 20, "                    ")
put(27, 15, "OLED board")

# status LED
put(57, 4, "(O)"); put(52, 4, "LED")

# JST candidate bands (undecided)
def dotted(c0, l0, w, hgt, label):
    for j in range(w):
        put(c0 + j, l0, "."); put(c0 + j, l0 + hgt - 1, ".")
    for i in range(hgt):
        put(c0, l0 + i, ":"); put(c0 + w - 1, l0 + i, ":")
    put(c0 + 2, l0 + 1, label)

dotted(20, 33, 12, 4, "JST? ")
dotted(48, 33, 12, 4, "JST? ")

out = []
ruler = [" "] * (cols + 2)
for xm in range(0, 81, 10):
    s = str(xm)
    start = xm + 1 if xm < 80 else xm + 1 - len(s) + 1
    for i, ch in enumerate(s):
        idx = start + i
        if idx < len(ruler):
            ruler[idx] = ch
out.append("".join(ruler).rstrip() + "   (x mm)")
out.append("+" + "-" * cols + "+")
for i, row in enumerate(g):
    y0 = i * 2
    tag = f" y={y0}" if y0 % 10 == 0 else ""
    out.append("|" + "".join(row) + "|" + tag)
out.append("+" + "-" * cols + "+ y=80")
print("\n".join(out))
