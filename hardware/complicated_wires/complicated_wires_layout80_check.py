# -*- coding: utf-8 -*-
"""80mm角パネル(複雑ワイヤ)の配置チェック + ASCII描画用データ。
座標: mm、原点=左上、x右、y下。パネル=80x80。
ルール(ハブ連絡事項.md): 四隅の15mm角には部品を置かない(2026-09-29確定: 穴径2.6mm、中心はパネル縁から9mmインセット。
旧「穴径10mm・中心未確認」は撤回。15mm角キープアウト自体は根拠がはっきりするまで維持、縮小はユーザー判断待ち)。
部品寸法(確認済みのもの): 秋月WJ141V-2.54-02P 7.62(極方向)x12.9(奥行)x13.8(高さ) / SK6812MINI-E 3.2x2.8x1.78
配置方針: ワイヤーは縦(実物どおり上から下)、ピッチ8mm。

2026-09-27変更(3): ★マークの裏面バックライト方式(印刷ステンシル+単純LED)をやめ、上部LED・★の
両方をNeoPixel化してデイジーチェーン化。ユーザー指示。

2026-09-27変更(5): 「色」と「LED点灯」の2個のNeoPixelを、上部の1個に統合(ユーザー指示)。
中段の「色NeoPixel」の行が無くなり、可視ワイヤーが信号側端子台のすぐ下から始まるようになった。

2026-09-27変更(6): 端子台を1本=1端子台(6個/片側)から、**2極端子台5個/片側、中央の1個だけ
ワイヤー3・4の2本を1個で受ける(2極とも配線)、残り4個(ワイヤー1,2,5,6)は1極のみ配線**という
構成に変更(ユーザー指示「端子台、2極5つを上下で1セットずつ」の解釈。中央のワイヤー3・4だけを
まとめることで、5個中2箇所(1-2間、5-6間)の隙間は従来どおり0.38mmのままだが、中央2箇所
(2-中央間、中央-5間)の隙間は大きく改善する)。信号側・GND側とも同じ構成。
"""
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = 80.0
KEEP = 15.0
HOLE_R = 1.3    # 2026-09-29確定: 穴径2.6mm(旧仮値5.0mmから修正)
HOLE_INSET = 9.0   # 2026-09-29確定: 穴中心はパネル縁から9mm(旧: 未確認のため5-12mmを掃引していた)
EDGE_MARGIN = 3.0

PARAMS = {
    "tb_w": 7.62,       # WJ141V 極方向(x方向)。1極のみ配線でも2極のみ配線でも筐体幅は同じ
    "tb_d": 12.9,       # WJ141V 奥行き(y方向)
    "pix": 4.0,         # SK6812MINI-E(3.2x2.8mm)+周囲の占有 = 4x4。上部(色+LED点灯統合)/★とも同じ寸法
    "pitch": 8.0,       # ワイヤー列ピッチ(ワイヤーモジュールと同じ下限8mm)
    "gap": 1.0,         # 部品間の隙間
    "y_top": 3.0,       # 一番上の部品の上端(パネル縁からの余白)
    "y_bot": 77.0,      # 一番下の部品の下端
    "status_xy": (72.0, 22.0),
    "status_d": 5.8,
}

# 端子台のグルーピング(信号側・GND側とも共通)。各タプルは、その1個の端子台が受け持つワイヤー番号。
# (3,4)だけ2極とも配線、他は2極品の1極だけ配線。
TERMINAL_GROUPS = [(1,), (2,), (3, 4), (5,), (6,)]


def wire_xc(n, pitch):
    return 40.0 + (n - 1 - 2.5) * pitch


def build(p=PARAMS):
    parts = {}
    sx, sy = p["status_xy"]
    parts["status LED (green)"] = ("circle", sx, sy, p["status_d"] / 2)
    y_top0 = p["y_top"]
    y_top1 = y_top0 + p["pix"]
    y_tt0 = y_top1 + p["gap"]
    y_tt1 = y_tt0 + p["tb_d"]
    y_star1 = p["y_bot"]
    y_star0 = y_star1 - p["pix"]
    y_tb1 = y_star0 - p["gap"]
    y_tb0 = y_tb1 - p["tb_d"]
    wire_len = y_tb0 - y_tt1   # 信号側端子台の下端 -> GND側端子台の上端(色NeoPixelの行は廃止)
    for i in range(6):
        n = i + 1
        xc = wire_xc(n, p["pitch"])
        parts[f"W{n} Top NeoPixel"] = ("rect", xc - p["pix"] / 2, y_top0, xc + p["pix"] / 2, y_top1)
        parts[f"W{n} Star NeoPixel"] = ("rect", xc - p["pix"] / 2, y_star0, xc + p["pix"] / 2, y_star1)
        parts[f"W{n} wire lane"] = ("rect", xc - 0.5, y_tt1, xc + 0.5, y_tb0)
    for gi, group in enumerate(TERMINAL_GROUPS):
        xs = [wire_xc(n, p["pitch"]) for n in group]
        xc = sum(xs) / len(xs)
        label = "".join(str(n) for n in group)
        parts[f"S{label} signal terminal (wire {','.join(map(str, group))})"] = (
            "rect", xc - p["tb_w"] / 2, y_tt0, xc + p["tb_w"] / 2, y_tt1)
        parts[f"G{label} GND terminal (wire {','.join(map(str, group))})"] = (
            "rect", xc - p["tb_w"] / 2, y_tb0, xc + p["tb_w"] / 2, y_tb1)
    # 2026-09-28: 「接続状態インジケータLED」(EXTRA1-4検知回路とセット)はユーザーに否定され撤回。
    # 端子ごとNeoPixel20個(スタート10+ゴール10)の物理配置は未検証(design_notes.md §6・§8)。
    # ここではまだモデル化していない(次の作業でTop/Star NeoPixelバンドと合わせて見直す)。
    return parts, wire_len


def bbox(pt):
    if pt[0] == "rect":
        return pt[1], pt[2], pt[3], pt[4]
    _, cx, cy, r = pt
    return cx - r, cy - r, cx + r, cy + r


def rect_circle_dist(rect, c, r):
    x0, y0, x1, y1 = rect
    cx, cy = c
    dx = max(x0 - cx, 0, cx - x1)
    dy = max(y0 - cy, 0, cy - y1)
    return math.hypot(dx, dy) - r


def part_hole_gap(pt, d):
    b = bbox(pt)
    best = 1e9
    for (hx, hy) in [(d, d), (P - d, d), (d, P - d), (P - d, P - d)]:
        if pt[0] == "rect":
            g = rect_circle_dist(b, (hx, hy), HOLE_R)
        else:
            g = math.hypot(hx - pt[1], hy - pt[2]) - pt[3] - HOLE_R
        best = min(best, g)
    return best


def in_keepout(pt):
    x0, y0, x1, y1 = bbox(pt)
    for (kx0, ky0) in [(0, 0), (P - KEEP, 0), (0, P - KEEP), (P - KEEP, P - KEEP)]:
        if x0 < kx0 + KEEP and x1 > kx0 and y0 < ky0 + KEEP and y1 > ky0:
            return True
    return False


def overlap(a, b):
    ax0, ay0, ax1, ay1 = bbox(a)
    bx0, by0, bx1, by1 = bbox(b)
    return ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0


def report(p=PARAMS):
    parts, wire_len = build(p)
    print("== parameters ==")
    print(p)
    print("visible wire length (signal terminal bottom edge -> GND terminal top edge) = %.1f mm" % wire_len)
    print("== keep-out (15x15 corners) violations ==")
    print([n for n, q in parts.items() if in_keepout(q)] or "none")
    print("== min edge distance ==")
    print("%.2f mm" % min(min(bbox(q)[0], bbox(q)[1], P - bbox(q)[2], P - bbox(q)[3]) for q in parts.values()))
    print("== overlaps (incl. wire lanes) ==")
    names = list(parts)
    bad = [(a, b) for i, a in enumerate(names) for b in names[i + 1:] if overlap(parts[a], parts[b])]
    print(bad or "none")
    print("== min gap between neighbouring columns (Top / Star NeoPixel), mm ==")
    for kind in ("Top NeoPixel", "Star NeoPixel"):
        bb = [bbox(parts[f"W{k} {kind}"]) for k in range(1, 7)]
        print(kind, ["%.2f" % (bb[k + 1][0] - bb[k][2]) for k in range(5)])
    print("== gap between neighbouring terminal blocks (5 per side), mm ==")
    for prefix, side in (("S", "signal"), ("G", "GND")):
        bb = [bbox(v) for n, v in parts.items() if n.startswith(prefix) and side in n]
        gaps = ["%.2f" % (bb[k + 1][0] - bb[k][2]) for k in range(len(bb) - 1)]
        print(side, gaps)
    print("== min gap to corner holes (2026-09-29確定: 穴径2.6mm、中心インセット9.0mm) ==")
    gaps = {n: part_hole_gap(q, HOLE_INSET) for n, q in parts.items()}
    n, g = min(gaps.items(), key=lambda kv: kv[1])
    print("inset=%.1fmm  min gap=%.2f mm  (closest: %s)" % (HOLE_INSET, g, n))
    print("(参考: 旧未確定時の掃引値)")
    for d in [5, 6, 7, 7.5, 8, 9, 10, 12]:
        gaps = {n: part_hole_gap(q, d) for n, q in parts.items()}
        n, g = min(gaps.items(), key=lambda kv: kv[1])
        print("  d=%5.1f  min gap=%6.2f mm  (closest: %s)" % (d, g, n))
    return parts


if __name__ == "__main__":
    report()
    print()
    print("== variant: screw terminal g114217 (5.54 x 6.2) ==")
    q = dict(PARAMS)
    q["tb_w"], q["tb_d"] = 5.54, 6.2
    _, wl = build(q)
    print("visible wire length = %.1f mm" % wl)
