# Four-button module: four_button.kicad_pcb の生成スクリプト(2026-10-01)。KiCad付属のPythonで実行する:
#   "C:\Program Files\KiCad\10.0\bin\python.exe" gen_four_button_pcb.py
# button/gen_button_pcb.pyの手法を踏襲。80x80mm外形・取付穴H1〜H4・GNDベタ(表裏)、
# グリッド4+ひし形4のホットスワップソケットを座標案(four_button_coordinate_proposal.md)どおりに配置し、
# 残りの部品(NeoPixel LED x4・R10・状態LED・C1・J1・SW9・Pico)を仮配置する。Picoは横置き(cx=27.5,cy=37.5,
# USB側が盤面左寄り)で、ソケットの穴・パッドとも干渉しない(自前の幾何スキャンで検証、design_notes参照)。
import os
import re
import math

import pcbnew
from pcbnew import FromMM as mm, VECTOR2I

D = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(D, "four_button.kicad_pcb")
NETLIST = os.path.join(D, "four_button_netlist.net")
STOCK = "C:/Program Files/KiCad/10.0/share/kicad/footprints/"
LIBS = {
    "FourButton_Local": os.path.join(D, "FourButton_Local.pretty"),
    "OSC_Shared": os.path.join(D, "..", "shared_lib", "OSC_Shared.pretty"),
}
TIMER_PCB = os.path.join(D, "..", "timer", "timer.kicad_pcb")

txt = open(NETLIST, encoding="utf-8").read()
comps = {}
for m in re.finditer(r'\(comp\s*\(ref "([^"]+)"\)\s*\(value "([^"]*)"\)\s*\(footprint "([^"]*)"\)', txt):
    comps[m.group(1)] = dict(value=m.group(2), fp=m.group(3))
nets = {}
for m in re.finditer(r'\(net\s*\(code "\d+"\)\s*\(name "([^"]*)"\)\s*\(class "[^"]*"\)(.*?)\n\t\t\)\n', txt, re.S):
    nets[m.group(1)] = re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', m.group(2))
print(len(comps), "components,", len(nets), "nets")

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

pad_net = {}
for name, members in nets.items():
    for ref, pin in members:
        pad_net[(ref, pin)] = name

fps = {}
for ref, c in comps.items():
    fp = load_fp(c["fp"])
    fp.SetFPID(pcbnew.LIB_ID(*c["fp"].split(":")))
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    board.Add(fp)
    fps[ref] = fp

tb = pcbnew.LoadBoard(TIMER_PCB)
for i, (x, y) in enumerate([(9, 9), (71, 9), (9, 71), (71, 71)], start=1):
    src = tb.FindFootprintByReference(f"H{i}")
    h = pcbnew.FOOTPRINT(src)
    h.SetFPID(pcbnew.LIB_ID("FourButton_Local", "MountingHole_2.6mm"))
    h.SetReference(f"H{i}")
    h.SetPosition(VECTOR2I(mm(x), mm(y)))
    board.Add(h)

def rotate(fp, deg):
    fp.SetOrientationDegrees(deg)

def to_back(fp):
    """裏面へ移す(左右反転)。既に裏面ならFlipしない(べき等; place()をループ内で同じfpに複数回
    呼ぶと、Flipは相対トグルなので毎回呼ぶと前後が入れ替わり続けるバグを防ぐ)。"""
    if not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)

def pad_pos(fp, num):
    for p in fp.Pads():
        if p.GetNumber() == num:
            q = p.GetPosition()
            return (pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
    raise KeyError(num)

def place(ref, x, y, deg=0.0, back=False, anchor_pad=None):
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

def place_vertical(ref, x, y_top, back=True):
    for deg in (90, 270):
        place(ref, x, y_top, deg, back=back, anchor_pad="1")
        if pad_pos(fps[ref], "2")[1] > pad_pos(fps[ref], "1")[1]:
            return
    raise SystemExit(f"{ref}: cannot orient vertically")

# ---------------------------------------------------------------- 前面: ホットスワップソケット8個
# フットプリントはB.Cu(裏面)にパッドを持つ設計のため、反転しない(=前面配置のまま。switch本体は前面、
# 半田面は裏面という daprice の元々の意図どおり)。座標は four_button_coordinate_proposal.md の確定値。
cx = cy = 40.0
GRID_XY = {"SW1": (cx - 19, cy - 19), "SW2": (cx + 19, cy - 19), "SW3": (cx - 19, cy + 19), "SW4": (cx + 19, cy + 19)}
DIAMOND_XY = {"SW5": (cx - 17, cy), "SW6": (cx, cy - 17), "SW7": (cx, cy + 17), "SW8": (cx + 17, cy)}
for ref, (x, y) in {**GRID_XY, **DIAMOND_XY}.items():
    place(ref, x, y, 0)

# 状態LED(D5, R9): 両方ともy=6の水平一列(垂直配置だとR9の下側パッドがy=13.5以降のソケット
# (SW2/SW6)の領域まで伸びて穴間隔違反になったため、y=6に留めてソケット帯(y>=13.5)を完全に回避)。
place("D5", 52.0, 6.0, 0)
place("R9", 58.0, 6.0, 180, back=True)

# ---------------------------------------------------------------- 裏面: NeoPixel(WS2812B x4)+ R10 + J1/C1/SW9
# 2026-10-01: ユーザー決定でLED駆動をNPN+抵抗+単色LEDからWS2812B(アドレサブルRGB)4個の数珠つなぎへ変更。
# 「キーの窓位置に合わせず、キーのそばに置いて薄めのキートップ越しに光らせる」方針のため、各LEDはキー
# 近傍にSMDで直接実装(手配線なし、PCB上で完結)。手計算の仮配置(南5.08mm等)では毎回ソケット自身の
# 穴・Pico本体・ヘッダ列・SW9のいずれかと衝突したため、固定部品すべて(ソケット・Pico・SW9・J1/C1/R10・
# 取付穴)を障害物とした全方位スキャン(15度刻み・半径3-10mm)で各キーごとに最も近い安全地点を自動探索し、
# コンデンサも同様にLED自身を障害物に加えて別途スキャンした(スクリプト実行記録はdesign_notes参照)。
NEOPIXEL_XY = {"D1": (29.0, 40.0), "D2": (46.0, 23.0), "D3": (40.0, 61.0), "D4": (57.0, 44.0)}
NEOPIXEL_CAP_XY = {"C2": (30.04, 43.86), "C3": (42.46, 26.54), "C4": (36.0, 61.0), "C5": (58.04, 47.86)}
NEOPIXEL_CAP = {"D1": "C2", "D2": "C3", "D3": "C4", "D4": "C5"}
for dref, (x, y) in NEOPIXEL_XY.items():
    place(dref, x, y, 0, back=True)
for cref, (x, y) in NEOPIXEL_CAP_XY.items():
    place(cref, x, y, 0, back=True)

place("R10", 13.0, 6.0, 180, back=True)   # NeoPixelデータ線の直列抵抗、上帯の空き(旧Redチェーン跡)。
# deg=180が「前方(+x)」に伸びる向き(place()のrotate->flip順による既知の実測結果、deg=0だと後方に伸びて
# コーナーキープアウトに入る)。

# 下帯: J1 + C1(旧Blueチェーンがなくなったため、下帯の空きに単純配置。J1は取付穴H3(9,71)からの
# クリアランスを確保するため26に寄せた)
place("J1", 26.0, 74.0, 0, back=True)
place("C1", 40.0, 74.0, 0, back=True)

# モード選択SW9: 当初(40,40)盤面中央案はPico本体(横置き後のx:2-53,y:27.5-48)の真下に入り、
# (a)浮き2.5mmを超えると物理干渉、(b)収まってもケースを開けた時に指が届かず運用不可との
# ハブ指摘(2026-10-01)を受けて移動。Pico本体から4mm以上離し、全裏面部品・ソケット穴/パッドとの
# クリアランスも自前の幾何スキャンで確認済み(余裕6.2mm、下帯のすぐ上の空き)。
place("SW9", 40.5, 66.0, 0, back=True)

# ---------------------------------------------------------------- 裏面: Pico(浮き実装、横置き)
# 縦置き(x:0-21,y:12-63)だとソケットSW1/SW3/SW5のヘッダ穴と物理的に穴が重なり(hole_to_hole
# 0.00〜0.43mm、ハブの独立検証で判明)製造不可のため、ハブの幾何スキャン結果(ソケット8個の穴と
# 干渉しない帯: 横置きcx 25.5-54.5, cy 17.3-58.3)に基づき横置き(本体51x21mm)へ変更。
# さらにR10・J1/C1・SW9(40,40)とも干渉しない位置を選定(NeoPixel化で旧LED駆動チェーンは廃止)。
# deg=270でpad1/pad40(USB側)がPicoの左端に来る(実測確認済み)。cx=25.5は左端がほぼ盤面端(x=0)なので
# USBをケース外周に出しやすい。
PICO_X, PICO_Y, PICO_DEG = 27.5, 37.5, 270.0
place("U1", PICO_X, PICO_Y, PICO_DEG, back=True)
pico = fps["U1"]
p1 = pad_pos(pico, "1")
p20 = pad_pos(pico, "20")
bb = pico.GetBoundingBox(False)
wide = bb.GetWidth() > bb.GetHeight()
if not wide:
    raise SystemExit(f"Pico orientation check failed: bbox={pcbnew.ToMM(bb.GetWidth())}x{pcbnew.ToMM(bb.GetHeight())}")
print("Pico horizontal placement", "pad1(USB側)", p1, "pad20(GND側)", p20)

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

pcbnew.SaveBoard(PCB, board)
print("saved", PCB)
