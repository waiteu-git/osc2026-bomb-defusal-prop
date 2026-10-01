# Button module: button.kicad_pcb の生成スクリプト(2026-09-30)。KiCad付属のPython(pcbnew)で実行する:
#   "C:\Program Files\KiCad\10.0\bin\python.exe" gen_button_pcb.py
# 回路図(button.kicad_sch)から出力したネットリスト(button_netlist.net)を読み、
#  - 部品(シンボルに割り当てたフットプリント)を読み込み、ネット名をパッドに割り当て、
#  - 80x80mmの外形・取付穴H1〜H4(Ø2.6、縁から9mm)・GNDベタ(表裏)を作り、部品を仮配置する。
# 配線(トラック)はまだ引いていない(ラッツネストのみ)。配置は仮で、キートップ機構が決まったら動かす前提。
import os
import re
import sys
import math

import pcbnew
from pcbnew import FromMM as mm, VECTOR2I

D = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(D, "button.kicad_pcb")
NETLIST = os.path.join(D, "button_netlist.net")
STOCK = "C:/Program Files/KiCad/10.0/share/kicad/footprints/"
LIBS = {
    "RPi_Pico": "C:/Users/ysou5/Documents/KiCad/10.0/3rdparty/KiCad-RP-Pico/RP-Pico Libraries/MCU_RaspberryPi_and_Boards.pretty",
    "Button_Local": os.path.join(D, "Button_Local.pretty"),
    "OSC_Shared": os.path.join(D, "..", "shared_lib", "OSC_Shared.pretty"),
}
TIMER_PCB = os.path.join(D, "..", "timer", "timer.kicad_pcb")   # 取付穴フットプリントの流用元(H1〜H4)

# ---------------------------------------------------------------- ネットリストの解析
txt = open(NETLIST, encoding="utf-8").read()
comps = {}
for m in re.finditer(r'\(comp\s*\(ref "([^"]+)"\)\s*\(value "([^"]*)"\)\s*\(footprint "([^"]*)"\)', txt):
    comps[m.group(1)] = dict(value=m.group(2), fp=m.group(3))
nets = {}
for m in re.finditer(r'\(net\s*\(code "\d+"\)\s*\(name "([^"]*)"\)\s*\(class "[^"]*"\)(.*?)\n\t\t\)\n', txt, re.S):
    nets[m.group(1)] = re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', m.group(2))
print(len(comps), "components,", len(nets), "nets")

# ---------------------------------------------------------------- 基板
board = pcbnew.CreateEmptyBoard()
board.SetCopperLayerCount(2)

def add_outline():
    pts = [(0, 0), (80, 0), (80, 80), (0, 80)]
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(VECTOR2I(mm(a[0]), mm(a[1])))
        s.SetEnd(VECTOR2I(mm(b[0]), mm(b[1])))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)

add_outline()

def load_fp(fpid):
    lib, name = fpid.split(":")
    path = LIBS.get(lib, STOCK + lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint not found: {fpid}")
    return fp

netobj = {}
def get_net(name):
    if name not in netobj:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        netobj[name] = n
    return netobj[name]

pad_net = {}   # (ref, pad number) -> net name
for name, members in nets.items():
    for ref, pin in members:
        pad_net[(ref, pin)] = name

fps = {}
for ref, c in comps.items():
    fp = load_fp(c["fp"])
    fp.SetFPID(pcbnew.LIB_ID(*c["fp"].split(":")))   # ライブラリ名つきにしないとKiCadの回路図等価性検査が不一致とみなす
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    board.Add(fp)
    fps[ref] = fp

# 取付穴H1〜H4: timer基板と同じフットプリント(NPTH Ø2.6)を流用
tb = pcbnew.LoadBoard(TIMER_PCB)
for i, (x, y) in enumerate([(9, 9), (71, 9), (9, 71), (71, 71)], start=1):
    src = tb.FindFootprintByReference(f"H{i}")
    h = pcbnew.FOOTPRINT(src)
    h.SetFPID(pcbnew.LIB_ID("Button_Local", "MountingHole_2.6mm"))
    h.SetReference(f"H{i}")
    h.SetPosition(VECTOR2I(mm(x), mm(y)))
    board.Add(h)

# ---------------------------------------------------------------- 配置ヘルパー
def rotate(fp, deg):
    fp.SetOrientationDegrees(deg)

def to_back(fp):
    """裏面へ移す(左右反転)。位置は反転の前後でフットプリント原点を保つ。"""
    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)

def pad_pos(fp, num):
    for p in fp.Pads():
        if p.GetNumber() == num:
            q = p.GetPosition()
            return (pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
    raise KeyError(num)

def place(ref, x, y, deg=0.0, back=False, anchor_pad=None):
    """anchor_padを指定すると、そのパッドが(x,y)に来るようにする(回転・反転後に平行移動で合わせる)。"""
    fp = fps[ref]
    fp.SetPosition(VECTOR2I(mm(0), mm(0)))
    rotate(fp, deg)
    if back:
        to_back(fp)
    if anchor_pad is not None:
        px, py = pad_pos(fp, anchor_pad)
        fp.SetPosition(VECTOR2I(mm(x - px), mm(y - py)))
    else:
        fp.SetPosition(VECTOR2I(mm(x), mm(y)))
    return fp

def flip_side_fix(ref):
    pass

# ---------------------------------------------------------------- 仮配置(座標は基板座標、mm)

# --- 前面(F.Cu): LED・タクト・表示器コネクタ
place("LED9", 55.0, 5.5, 0)
sw_centers = {"SW1": (29.0, 32.0)}     # Kailh MXホットスワップソケット1個(キートップ真下、仮。four_buttonと同じソケット)
for ref, (cx, cy) in sw_centers.items():
    place(ref, cx, cy, 0)                  # Kailh_socket_MXの原点=スイッチ中心(パッドは裏面側)
place("J2", 20.0, 47.0, 90)                 # 1x08ヘッダを横向き(pin1が左)。12mmタクトの下側(仮)

# --- 裏面(B.Cu): Pico・J1・C1・抵抗・トランジスタ
place("J1", 24.0, 15.0, 0, back=True)
place("C1", 33.0, 15.0, 0, back=True)
place("R9", 47.0, 5.5, 0, back=True)
def place_vertical(ref, x, y_top):
    """縦置き(裏面)。pad1が上(y_top)、pad2が下(y_top+7.62)になる向きを選ぶ(裏面は左右反転するので90°か270°かは実測で決める)。"""
    for deg in (90, 270):
        place(ref, x, y_top, deg, back=True, anchor_pad="1")
        if pad_pos(fps[ref], "2")[1] > pad_pos(fps[ref], "1")[1]:
            return
    raise SystemExit(f"{ref}: cannot orient vertically")

# 
# NeoPixel NP1〜NP6(前面、縦一列・ピッチ7mm=約4.2cm、右端付近)と、データ直列抵抗R10(裏面、縦置き)
for i in range(6):
    place(f"NP{i + 1}", 70.0, 22.0 + 7.0 * i, 0)
place_vertical("R10", 62.0, 12.0)

# Pico(裏面、横向き): GPIO0〜15側の列(pin1..20)を上、GPIO16以降側を下にする
pico = fps["U1"]
best = None
for deg in (0, 90, 180, 270):
    place("U1", 40.0, 67.9, deg, back=True)
    p1 = pad_pos(pico, "1")
    p21 = pad_pos(pico, "21")
    # 長軸が横(x方向に広い)で、pin1の列が上にある向きを選ぶ
    cx, cy = 40.0, 67.9
    bb = pico.GetBoundingBox(False)
    wide = bb.GetWidth() > bb.GetHeight()
    if wide and p1[1] < p21[1]:
        best = deg
        break
if best is None:
    raise SystemExit("could not find a Pico orientation (wide + pin1 row on top)")
place("U1", 40.0, 67.9, best, back=True)
print("Pico orientation", best, "pad1", pad_pos(pico, "1"), "pad21", pad_pos(pico, "21"))

# WS2812Bフットプリントのピン1マーク(シルクの"1"、高さ0.8mm)は共通ルールの最小文字高さ1.0mmを下回るので、1.0mmに直す
for ref in fps:
    if ref.startswith("NP"):
        for g in fps[ref].GraphicalItems():
            if isinstance(g, pcbnew.PCB_TEXT) and g.GetText() == "1":
                g.SetTextSize(VECTOR2I(mm(1.0), mm(1.0)))

# ---------------------------------------------------------------- ネット割り当て
for ref, fp in fps.items():
    for pad in fp.Pads():
        nm = pad_net.get((ref, pad.GetNumber()))
        if nm:
            pad.SetNet(get_net(nm))

# ---------------------------------------------------------------- GNDベタ(表裏)
gnd = get_net("GND")
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(gnd)
    z.SetIsFilled(False)
    o = z.Outline()
    o.NewOutline()
    for (x, y) in [(0.5, 0.5), (79.5, 0.5), (79.5, 79.5), (0.5, 79.5)]:
        o.Append(mm(x), mm(y))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.3))
    z.SetThermalReliefSpokeWidth(mm(0.5))
    z.SetLocalClearance(mm(0.3))
    board.Add(z)

# SaveBoardは同名の.kicad_pro/.kicad_prlを初期値で作り直してしまい、ハブ共通のデザインルールが消える。保存前の内容を退避して戻す。
_keep = {}
for ext in (".kicad_pro", ".kicad_prl"):
    f = PCB.replace(".kicad_pcb", ext)
    if os.path.exists(f):
        _keep[f] = open(f, "rb").read()
pcbnew.SaveBoard(PCB, board)
for f, data in _keep.items():
    open(f, "wb").write(data)
print("saved", PCB)
