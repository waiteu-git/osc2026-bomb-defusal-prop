#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSL40562-IR(4桁7セグ、アノードコモン)のデータシート「ピン機能図」を座標で解析し、
セグメント文字とピン番号の対応を導く。目視では母線の階段状の配線から断定できなかったため。

使い方(このフォルダで):
    pdftoppm -f 2 -l 2 -r 400 -png OSL40562-IR.pdf page      # → page-2.png (3400x4400)
    python decode_OSL40562-IR_pins.py
必要: numpy, scipy, Pillow。

解析の考え方:
  * 図の上段の黒い三角(ダイオード)32個 = 4桁 x (A,B,C,D,E,F,G,DP) の列。左から順に8個ずつが1桁。
  * 水平の母線が8本。母線と縦線の交点の黒点(ジャンクション)16個が、どの列に載っているかを調べる。
    全て「その母線と同じ文字の列」なら、母線 = 同じセグメントを4桁分まとめたもの。
  * 母線の下(最下段の母線より下)まで縦線が伸びている列 = 外部ピンへ降りる列。
    それが2桁目の8列だけなら、外部ピンは2桁目の列の真下にある。
  * 外部ピンの番号は図の下段の文字列(左から 11 7 4 2 1 10 5 3)。図の読み取りは
    OSL40562-IR_segment_pin_decode.png(2桁目の列に赤線を重ねた拡大図)で確認する。
"""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

PAGE = "page-2.png"
X0, Y0, X1, Y1 = 600, 2100, 2650, 2820          # 配線図の領域(400dpi)
LET = ["A", "B", "C", "D", "E", "F", "G", "DP"]
PIN_LABELS_LEFT_TO_RIGHT = [11, 7, 4, 2, 1, 10, 5, 3]   # 図の下段の数字(目視で読み取り)

crop = np.array(Image.open(PAGE).convert("L").crop((X0, Y0, X1, Y1)))
dark = crop < 110
er = ndi.binary_erosion(dark, structure=np.ones((7, 7)))     # 細い線は消え、塗りつぶしだけ残る
lab, n = ndi.label(er)
blobs = []
for i in range(1, n + 1):
    ys, xs = np.where(lab == i)
    blobs.append((xs.mean(), ys.mean(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1))
tri = sorted([b for b in blobs if b[2] > 14 and b[3] > 8 and b[1] < 300], key=lambda b: b[0])
dots = [b for b in blobs if b not in tri]
cols = [b[0] for b in tri]
assert len(cols) == 32 and len(dots) == 16, (len(cols), len(dots))

levels = []
for y in sorted(b[1] for b in dots):
    if not levels or y - levels[-1][-1] > 12:
        levels.append([y])
    else:
        levels[-1].append(y)
levels = [float(np.mean(l)) for l in levels]
assert len(levels) == 8

bad = 0
for b in dots:
    k = int(np.argmin([abs(b[1] - l) for l in levels]))          # 何番目の母線か(上から)
    j = int(np.argmin([abs(b[0] - c) for c in cols]))            # どの列か
    if LET[j % 8] != LET[k]:
        bad += 1
print("ジャンクション16個のうち、母線と文字が食い違うもの:", bad)
assert bad == 0

extent = {}
for d in range(4):
    for k in range(8):
        cx = int(round(cols[d * 8 + k]))
        strip = dark[:, cx - 2:cx + 3].any(axis=1)
        y = int(levels[-1]) + 5
        while y < crop.shape[0] and strip[y]:
            y += 1
        extent[(d + 1, LET[k])] = y - (int(levels[-1]) + 5)
down = sorted({d for (d, l), v in extent.items() if v > 15})
print("最下段の母線より下へ縦線が伸びている桁:", down)
assert down == [2]

print("\nセグメント → ピン番号(2桁目の列の真下の番号):")
for letter, pin in zip(LET, PIN_LABELS_LEFT_TO_RIGHT):
    print("  %-2s = pin%d" % (letter, pin))
print("桁選択(COM、図の上段の数字): DIG.1=pin12, DIG.2=pin9, DIG.3=pin8, DIG.4=pin6")
