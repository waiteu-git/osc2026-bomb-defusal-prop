# -*- coding: utf-8 -*-
"""複雑ワイヤモジュールの回路図(complicated_wires.kicad_sch)生成スクリプト。

設計の中身は complicated_wires_design_notes.md の§5(GPIO表・回路)。
- 座標はすべて1.27mm格子の整数倍(内部では格子単位の整数で扱う)
- ワイヤーは常に2点、全ピンに「2.54mmのスタブ線+ラベル(または電源シンボル)」を付けて、ネット名で接続する
- ライブラリシンボルは既存の回路図(password / wires)とKiCad標準ライブラリから埋め込む(サブユニット名にライブラリ名を付けない)
使い方: python gen_complicated_wires_sch.py  (同じフォルダに complicated_wires.kicad_sch を書き出す)
"""
import math
import re
import sys
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
HW = HERE.parent
PROJECT = "complicated_wires"
G = 1.27
KICAD_SYM = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")

SHEET_UUID = str(uuid.uuid4())


def u():
    return str(uuid.uuid4())


def fmt(g):
    return "%.2f" % (g * G)


# ---------------------------------------------------------------- ライブラリシンボル
def extract_block(text, name, indent):
    key = indent + '(symbol "%s"' % name
    i = text.find(key)
    if i < 0:
        raise SystemExit("symbol not found: " + name)
    i += len(indent)
    depth, j = 0, i
    while True:
        ch = text[j]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
        j += 1


def from_sch(path, name):
    return extract_block(Path(path).read_text(encoding="utf-8"), name, "\t\t")


def from_lib(libfile, name, new_name):
    blk = extract_block((KICAD_SYM / libfile).read_text(encoding="utf-8"), name, "\t")
    return blk.replace('(symbol "%s"' % name, '(symbol "%s"' % new_name, 1)


LIBS = {
    "Connector_Generic:Conn_01x04": from_sch(HW / "password" / "password.kicad_sch", "Connector_Generic:Conn_01x04"),
    "Connector_Generic:Conn_01x02": from_sch(HW / "wires" / "wires.kicad_sch", "Connector_Generic:Conn_01x02"),
    "Device:LED": from_sch(HW / "password" / "password.kicad_sch", "Device:LED"),
    "Device:R": from_sch(HW / "password" / "password.kicad_sch", "Device:R"),
    "RPi_Pico:Pico": from_sch(HW / "password" / "password.kicad_sch", "RPi_Pico:Pico"),
    "power:+3.3V": from_sch(HW / "password" / "password.kicad_sch", "power:+3.3V"),
    "power:+5V": from_sch(HW / "password" / "password.kicad_sch", "power:+5V"),
    "power:GND": from_sch(HW / "password" / "password.kicad_sch", "power:GND"),
    "LED:WS2812B": from_lib("LED.kicad_sym", "WS2812B", "LED:WS2812B"),
    "Device:C": from_lib("Device.kicad_sym", "C", "Device:C"),
    "Device:C_Polarized": from_lib("Device.kicad_sym", "C_Polarized", "Device:C_Polarized"),
    "power:PWR_FLAG": from_lib("power.kicad_sym", "PWR_FLAG", "power:PWR_FLAG"),
}

PIN_RE = re.compile(
    r'\(pin\s+(\w+)\s+(\w+)\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)\s*\(length\s+[-\d.]+\)\s*'
    r'\(name\s+"([^"]*)".*?\(number\s+"([^"]*)"', re.S)


def to_g(v):
    x = float(v) / G
    if abs(x - round(x)) > 1e-6:
        raise SystemExit("off-grid lib coordinate: %s" % v)
    return int(round(x))


PINS = {}
for lid, blk in LIBS.items():
    tbl = {}
    for m in PIN_RE.finditer(blk):
        tbl[m.group(7)] = (to_g(m.group(3)), to_g(m.group(4)), int(m.group(5)), m.group(6), m.group(1))
    PINS[lid] = tbl

# ---------------------------------------------------------------- 出力バッファ
wires, labels, nocs, syms, graphics = [], [], [], [], []
pwr_n = [0]
flg_n = [0]
DIRS = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}   # 画面上の向き(x右, y下)


def add_wire(a, b):
    assert a != b
    wires.append(
        "\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke (width 0) (type default))\n\t\t(uuid \"%s\")\n\t)"
        % (fmt(a[0]), fmt(a[1]), fmt(b[0]), fmt(b[1]), u()))


def add_label(name, p, direction):
    ang = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}[direction]
    just = "left bottom" if ang in (0, 90) else "right bottom"
    labels.append(
        "\t(label \"%s\"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n\t\t(uuid \"%s\")\n\t)"
        % (name, fmt(p[0]), fmt(p[1]), ang, just, u()))


def add_nc(p):
    nocs.append("\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid \"%s\")\n\t)" % (fmt(p[0]), fmt(p[1]), u()))


def add_graphic_line(a, b, width=0.254):
    """電気的に無関係な作図用の破線(polyline)。ERC・ネットリストには一切乗らない。
    実物のワイヤー(端子台間を渡す、着脱可能な部品)を示す注記専用。"""
    graphics.append(
        "\t(polyline\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width %.3f)\n\t\t\t(type dash)\n\t\t)\n"
        "\t\t(fill\n\t\t\t(type none)\n\t\t)\n\t\t(uuid \"%s\")\n\t)"
        % (fmt(a[0]), fmt(a[1]), fmt(b[0]), fmt(b[1]), width, u()))


def add_text(s, p, size=1.0, justify="left"):
    graphics.append(
        "\t(text \"%s\"\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %.2f %.2f)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n\t\t(uuid \"%s\")\n\t)"
        % (s.replace('"', "'"), fmt(p[0]), fmt(p[1]), size, size, justify, u()))


def prop(name, val, x, y, hide=False, size=1.27):
    return ("\t\t(property \"%s\" \"%s\"\n\t\t\t(at %s %s 0)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n"
            "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size %.2f %.2f)\n\t\t\t\t)\n\t\t\t)\n\t\t)"
            % (name, val.replace('"', "'"), x, y, "\t\t\t(hide yes)\n" if hide else "", size, size))


def add_symbol(lib, ref, value, gx, gy, rot=0, footprint="", desc="", ref_off=(0, -3.81), val_off=(0, 3.81), hide_ref=False, hide_val=False):
    """シンボルを置き、各ピンの絶対座標(格子単位)と外向きの向きを返す"""
    x, y = fmt(gx), fmt(gy)
    px = float(x)
    py = float(y)
    out = {}
    pin_lines = []
    for num, (lx, ly, pa, pname, ptype) in PINS[lib].items():
        th = math.radians(rot)
        c, s = int(round(math.cos(th))), int(round(math.sin(th)))
        rx, ry = lx * c - ly * s, lx * s + ly * c
        ax, ay = gx + rx, gy - ry
        outward = (pa + rot + 180) % 360
        out[num] = ((ax, ay), DIRS[outward], pname)
        pin_lines.append("\t\t(pin \"%s\"\n\t\t\t(uuid \"%s\")\n\t\t)" % (num, u()))
    lines = ["\t(symbol", "\t\t(lib_id \"%s\")" % lib, "\t\t(at %s %s %d)" % (x, y, rot), "\t\t(unit 1)", "\t\t(body_style 1)",
             "\t\t(exclude_from_sim no)", "\t\t(in_bom yes)", "\t\t(on_board yes)", "\t\t(in_pos_files yes)", "\t\t(dnp no)",
             "\t\t(fields_autoplaced yes)", "\t\t(uuid \"%s\")" % u(),
             prop("Reference", ref, "%.2f" % (px + ref_off[0]), "%.2f" % (py + ref_off[1]), hide=hide_ref),
             prop("Value", value, "%.2f" % (px + val_off[0]), "%.2f" % (py + val_off[1]), hide=hide_val),
             prop("Footprint", footprint, x, y, hide=True),
             prop("Datasheet", "", x, y, hide=True),
             prop("Description", desc, x, y, hide=True)]
    lines += pin_lines
    lines.append("\t\t(instances\n\t\t\t(project \"%s\"\n\t\t\t\t(path \"/%s\"\n\t\t\t\t\t(reference \"%s\")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)" % (PROJECT, SHEET_UUID, ref))
    lines.append("\t)")
    syms.append("\n".join(lines))
    return out


def power_rot(kind, d):
    """シンボルの本体(GNDは下向き、+5V/+3.3V/フラグは上向きが既定)がスタブの外向きに伸びるように回転させる"""
    if kind == "GND":
        return {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[d]
    return {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[d]


def add_power(kind, p, d=(0, 1)):
    pwr_n[0] += 1
    ref = "#PWR%02d" % pwr_n[0]
    if d[0] != 0:
        val_off = (d[0] * 7.62, -1.27 if d[0] > 0 else -1.27)
    else:
        val_off = (0, d[1] * 5.08 if kind == "GND" else -d[1] * 5.08)
        val_off = (0, 3.81 if kind == "GND" else -5.08)
    add_symbol("power:" + kind, ref, kind, p[0], p[1], power_rot(kind, d), "",
               "Power symbol creates a global label with name \"%s\"" % kind,
               ref_off=(0, 3.81), val_off=val_off, hide_ref=True)


def add_flag(p, d=(0, -1)):
    flg_n[0] += 1
    add_symbol("power:PWR_FLAG", "#FLG%02d" % flg_n[0], "PWR_FLAG", p[0], p[1], power_rot("+5V", d), "", "Power flag: marks this net as driven",
               ref_off=(0, -3.81), val_off=(d[0] * 7.62, -1.27) if d[0] else (0, -5.08), hide_ref=True, hide_val=True)


def stub(pin, net=None, power=None, extend=0, flag=False):
    """ピンから2格子(2.54mm)のスタブ線を外向きに出し、端にラベル/電源シンボルを置く。端点(格子)を返す"""
    (p, d, _) = pin
    end = (p[0] + 2 * d[0], p[1] + 2 * d[1])
    add_wire(p, end)
    if power:
        far = end
        if flag:
            far = (end[0] + 2 * d[0], end[1] + 2 * d[1])
            add_wire(end, far)
            add_flag(far, d)
        add_power(power, end, d)
    if net:
        add_label(net, end, d)
    return end


FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
FP_LED = "LED_THT:LED_D5.0mm"
FP_NEO = "LED_SMD:LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount"
# 2026-09-29: WJ141V-2.54-02P(仮footprint)からAPF-142(秋月g108367)相当へ変更。
# KiCad標準ライブラリにAPF専用footprintは無いため、寸法がほぼ一致するMKDS-1,5-2-5.08で代用
# (実寸10.16x9.8mm、footprint記載10.2x9.8mm)。
FP_TB = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal"
FP_JST = "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical"
FP_CP = "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"
FP_C = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
FP_PICO = "RPi_Pico:RPi_Pico_SMD_TH"

expected = {}   # ネット名 -> {"REF.pin"}  (自己検証用)


def note(net, ref, pin):
    expected.setdefault(net, set()).add("%s.%s" % (ref, pin))


# ---------------------------------------------------------------- U1: Pico 2
U1 = (166, 79)   # 格子単位(210.82, 100.33mm)
u1 = add_symbol("RPi_Pico:Pico", "U1", "Pico2", U1[0], U1[1], 0, FP_PICO,
                "Module MCU (Raspberry Pi Pico 2, no wireless)", ref_off=(-13.97, -40.64), val_off=(0, -33.02))
PICO_NETS = {
    "1": "UART_TX", "2": "UART_RX",
    "4": "WIRE1", "5": "WIRE2", "6": "WIRE3", "7": "WIRE4", "9": "WIRE5", "10": "WIRE6",
    "11": "NEO_OUT",
    "12": "STATUS",
}
# 2026-09-28: EXTRA1-4検知回路・接続状態インジケータLED(2026-09-27追加分)は撤回。
# ユーザーの実際の意図は「各端子(スタート/ゴール)にNeoPixelを置き、光り方で複雑ワイヤの属性
# (色・★・LED点灯)を再現する」ことで、GPIO検知や専用ステータスLEDではなかった(ユーザー指摘
# 「接続状態LED?そんなものつけろとは言っていない」)。GP10-28は元どおり空きに戻す。
PICO_GND = ["3", "8", "13", "18", "23", "28", "33", "38", "42"]
PICO_NC = ["14", "15", "16", "17", "19", "20", "21", "22", "24", "25", "26", "27",
           "29", "30", "31", "32", "34", "35", "37", "40", "41", "43"]
for pn, net in PICO_NETS.items():
    stub(u1[pn], net=net)
    note(net, "U1", pn)
for pn in PICO_GND:
    stub(u1[pn], power="GND")
    note("GND", "U1", pn)
stub(u1["36"], power="+3.3V", flag=True)
note("+3.3V", "U1", "36")
stub(u1["39"], power="+5V")
note("+5V", "U1", "39")
for pn in PICO_NC:
    add_nc(u1[pn][0])
assert len(PICO_NETS) + len(PICO_GND) + 2 + len(PICO_NC) == 43

# ---------------------------------------------------------------- J1: JST XH(UART・電源)
j1 = add_symbol("Connector_Generic:Conn_01x04", "J1", "JST_XH_4P", 250, 25, 0, FP_JST,
                "Host connection: Pin1=UART0 TX (GP0), Pin2=UART0 RX (GP1), Pin3=5V, Pin4=GND", ref_off=(0, -8.89), val_off=(0, 10.16))
stub(j1["1"], net="UART_TX"); note("UART_TX", "J1", "1")
stub(j1["2"], net="UART_RX"); note("UART_RX", "J1", "2")
stub(j1["3"], power="+5V", flag=True); note("+5V", "J1", "3")
stub(j1["4"], power="GND", flag=True); note("GND", "J1", "4")

# 電源のコンデンサ(NeoPixel用)
c1 = add_symbol("Device:C_Polarized", "C1", "100uF/16V", 270, 33, 0, FP_CP, "NeoPixel supply bulk capacitor (datasheet: not required, insurance)",
                ref_off=(5.08, -1.27), val_off=(6.35, 1.27))
stub(c1["1"], power="+5V"); note("+5V", "C1", "1")
stub(c1["2"], power="GND"); note("GND", "C1", "2")
c2 = add_symbol("Device:C", "C2", "0.1uF", 285, 33, 0, FP_C, "Decoupling near first NeoPixel (optional)",
                ref_off=(5.08, -1.27), val_off=(5.08, 1.27))
stub(c2["1"], power="+5V"); note("+5V", "C2", "1")
stub(c2["2"], power="GND"); note("GND", "C2", "2")

# ---------------------------------------------------------------- 端子台とワイヤー検出
r_idx = [0]


def next_r():
    r_idx[0] += 1
    return "R%d" % r_idx[0]


TB_X = 28
s_pins = {}   # 実物ワイヤー番号 -> 信号側端子台のピン絶対座標(注記線を引くために保存)
g_pins = {}   # 同上、GND側
# 2026-09-27: 「2極品5個/片側、中央(ワイヤー3・4)だけ2極とも配線、残り4個は1極のみ配線」に変更
# (ユーザー指示「端子台、2極5つを上下で1セットずつ」)。5個中2箇所(1-2間、5-6間)の隙間は
# 8mmピッチで0.38mmのままだが、中央2箇所(2-中央間、中央-5間)は約4.4mmに改善する(design_notes.md §6)。
# 2026-09-28: EXTRA1-4検知回路は撤回(ユーザー指摘、上のPICO_NETSコメント参照)。単独グループの
# 第2極は、信号側はno_connectに戻す。GND側は元々両極ともGND(害がないためそのまま)。
TERMINAL_GROUPS = [(1,), (2,), (3, 4), (5,), (6,)]
EXTRA_WIRES = [1, 2, 5, 6]
EXTRA_IDX = {w: i + 1 for i, w in enumerate(EXTRA_WIRES)}


def add_terminal_row(prefix, y0, power_gnd):
    """TERMINAL_GROUPSに従って端子台を並べる。power_gnd=Trueならピンを直接GNDへ、
    Falseなら net=WIRE{n}_T のラベルに接続する(信号側)。単独グループの第2極はGND側なら直接GND、
    信号側はno_connect(予備、未使用)。
    WJ141V-2.54-02Pに1極品は存在しないため、1本のみ配線する端子台もシンボルはConn_01x02とする
    (ユーザー指示「全部2極端子台にして」)。(主極ピン座標dict, 予備極ピン座標dict)を返す。"""
    pins = {}
    extra = {}
    y = y0
    for group in TERMINAL_GROUPS:
        label = "".join(str(n) for n in group)
        ref = "%s%s" % (prefix, label)
        if len(group) == 1:
            n = group[0]
            s = add_symbol("Connector_Generic:Conn_01x02", ref, "WJ141V-2.54-02P", TB_X, y, 0, FP_TB,
                           "%s-side spring terminal for wire %d, pin 2 unused (WJ141V-2.54-02P, no 1-pole part exists)"
                           % ("Signal" if not power_gnd else "GND", n),
                           ref_off=(0, -3.81), val_off=(0, 6.35))
            pins[n] = s["1"][0]
            extra[n] = s["2"][0]
            if power_gnd:
                stub(s["1"], power="GND"); note("GND", ref, "1")
                stub(s["2"], power="GND"); note("GND", ref, "2")
            else:
                stub(s["1"], net="WIRE%d_T" % n); note("WIRE%d_T" % n, ref, "1")
                add_nc(s["2"][0])
            y += 12
        else:
            n1, n2 = group
            s = add_symbol("Connector_Generic:Conn_01x02", ref, "WJ141V-2.54-02P", TB_X, y, 0, FP_TB,
                           "%s-side spring terminal shared by wires %d and %d (both poles used, WJ141V-2.54-02P)"
                           % ("Signal" if not power_gnd else "GND", n1, n2),
                           ref_off=(0, -3.81), val_off=(0, 6.35))
            pins[n1] = s["1"][0]
            pins[n2] = s["2"][0]
            if power_gnd:
                stub(s["1"], power="GND"); note("GND", ref, "1")
                stub(s["2"], power="GND"); note("GND", ref, "2")
            else:
                stub(s["1"], net="WIRE%d_T" % n1); note("WIRE%d_T" % n1, ref, "1")
                stub(s["2"], net="WIRE%d_T" % n2); note("WIRE%d_T" % n2, ref, "2")
            y += 12
    return pins, extra


s_pins, s_extra = add_terminal_row("S", 20, power_gnd=False)
g_pins, g_extra = add_terminal_row("G", 80, power_gnd=True)

# 実物のワイヤー(S-G間を渡す、着脱可能な部品)を破線で注記する。
# ERC/ネットリストには乗らない作図要素(add_graphic_line)なので、切断/接続の電気的な表現(WIREn ⇔ GND経由の分圧)には影響しない。
for i, line in enumerate([
    "S1,S2,S34,S5,S6=信号側端子台、G1,G2,G34,G5,G6=GND側端子台(WJ141V-2.54-02P、5個/片側)。",
    "S34/G34だけワイヤー3・4の2極とも配線、他は2極品の1極目をWIRE1,2,5,6に使用(2極目は各pin2、未使用)。",
    "各ワイヤー(実物の被覆線、着脱可能)がS-G間を渡すことで導通する(破線)。電気的なワイヤーとしては描いていない。",
]):
    add_text(line, (TB_X - 19, 11 + 2 * i), size=1.0, justify="left")
for wn in range(1, 7):
    x_link = TB_X + 12 + 2 * (wn - 1)   # 6本を横にずらして並べる(ref/valueテキストの右側、重ならないように)
    add_graphic_line((x_link, s_pins[wn][1]), (x_link, g_pins[wn][1]))
    add_text("W%d" % wn, (x_link + 1, (s_pins[wn][1] + g_pins[wn][1]) / 2), size=1.0, justify="left")

RS_X, RPU_X = 72, 100
for k in range(6):
    y = 20 + 10 * k
    rs_ref, rpu_ref = "R%d" % (k + 1), "R%d" % (k + 7)
    rs = add_symbol("Device:R", rs_ref, "1k", RS_X, y, 90, FP_R, "Wire %d detect: series resistor (ESD protection for exposed terminal)" % (k + 1))
    rpu = add_symbol("Device:R", rpu_ref, "10k", RPU_X, y, 90, FP_R, "Wire %d detect: external pull-up to 3V3" % (k + 1))
    stub(rs["1"], net="WIRE%d_T" % (k + 1)); note("WIRE%d_T" % (k + 1), rs_ref, "1")
    # R_s右ピン -> スタブ端(ラベルWIREk) -> R_pu左ピン
    p_right = rs["2"][0]
    p_mid = (p_right[0] + 2, p_right[1])
    add_wire(p_right, p_mid)
    add_label("WIRE%d" % (k + 1), p_mid, (1, 0))
    add_wire(p_mid, rpu["1"][0])
    note("WIRE%d" % (k + 1), rs_ref, "2"); note("WIRE%d" % (k + 1), rpu_ref, "1")
    stub(rpu["2"], power="+3.3V"); note("+3.3V", rpu_ref, "2")

# ---------------------------------------------------------------- NeoPixel(20個デイジーチェーン、端子ごと)
# 2026-09-28確定(ユーザー指示): 「複雑ワイヤ」の属性(色・★・LED点灯)は、パネル端の別バンドに
# 置いた専用NeoPixelではなく、各ワイヤーが挿さる場所(端子)そのものに置いたNeoPixelの光り方
# (色・点滅など)で再現する。ワイヤーは信号側端子(スタート)とGND側端子(ゴール)の間を渡すので、
# 端子台の全10極×2側=20極それぞれにNeoPixelを1個ずつ置く(信号側10=スタート、GND側10=ゴール)。
# 端子台に空き極が無い(WJ141Vは2極品しかない)ので、実際の6本以外の4極×2側も含めて全20個。
# 電気的には端子のネット(WIREn_T/GND)とは無関係(NeoPixelは色データのGPIOチェーンのみ)。
# どの物理位置がどのチェーンindexかはDescriptionプロパティに明記(ファーム側の対応表のもと)。
SIGNAL_POLES, GND_POLES = [], []
for group in TERMINAL_GROUPS:
    label = "".join(str(n) for n in group)
    if len(group) == 1:
        n = group[0]
        SIGNAL_POLES.append(("S" + label, "1", n))
        SIGNAL_POLES.append(("S" + label, "2", None))
        GND_POLES.append(("G" + label, "1", n))
        GND_POLES.append(("G" + label, "2", None))
    else:
        n1, n2 = group
        SIGNAL_POLES.append(("S" + label, "1", n1))
        SIGNAL_POLES.append(("S" + label, "2", n2))
        GND_POLES.append(("G" + label, "1", n1))
        GND_POLES.append(("G" + label, "2", n2))

NP_X0, NP_DX = 24, 16
NP_Y0, NP_Y1 = 200, 230   # 既存内容(y<=170)から十分離した空き領域に配置(ユーザーの手動配置に干渉しないため)
r13 = add_symbol("Device:R", "R13", "330", NP_X0, NP_Y0 - 10, 90, FP_R, "NeoPixel data series resistor (chain of 20)")
stub(r13["1"], net="NEO_OUT"); note("NEO_OUT", "R13", "1")

CHAIN = [("start", ref, pole, n) for (ref, pole, n) in SIGNAL_POLES] + \
        [("goal", ref, pole, n) for (ref, pole, n) in GND_POLES]
prev = None
for i, (kind, term_ref, pole, n) in enumerate(CHAIN):
    ref = "D%d" % (i + 1)
    row, col = divmod(i, 10)
    x = NP_X0 + NP_DX * col
    y = NP_Y0 if row == 0 else NP_Y1
    what = ("wire %d" % n) if n is not None else "spare pole (no wire assigned)"
    d = add_symbol("LED:WS2812B", ref, "SK6812MINI-E", x, y, 0, FP_NEO,
                   "%s indicator, physically next to %s pin%s (%s). Lights to reproduce Complicated Wires attributes "
                   "(color/star/lit) via color+blink pattern; not electrically tied to the terminal's own net. "
                   "SK6812MINI-E, akizuki g115478, 3.2x2.8mm, pinout VDD/DOUT/GND/DIN same order as WS2812B. "
                   "CAUTION: datasheet VIH=0.7*VDD=3.5V@VDD=5V, marginal for 3.3V-direct drive, unverified until bring-up."
                   % ("Start" if kind == "start" else "Goal", term_ref, pole, what),
                   ref_off=(-8.89, -8.89), val_off=(-8.89, 8.89))
    stub(d["1"], power="+5V"); note("+5V", ref, "1")
    stub(d["3"], power="GND"); note("GND", ref, "3")
    if i == 0:
        add_wire(r13["2"][0], d["4"][0])
        note("NEO_DIN", "R13", "2"); note("NEO_DIN", ref, "4")
    elif col == 0:
        # 行をまたぐ接続は素直に配線すると縦横に長い線になるので、スタブ+同名ラベルでネットをつなぐ
        # (電気的には直結と同じ)。
        net = "NP%d_DIN" % (i + 1)
        stub(prev["2"], net=net); note(net, "D%d" % i, "2")
        stub(d["4"], net=net); note(net, ref, "4")
    else:
        add_wire(prev["2"][0], d["4"][0])
        net = "NP%d_DIN" % (i + 1)
        note(net, "D%d" % i, "2"); note(net, ref, "4")
    prev = d
add_nc(prev["2"][0])

# ---------------------------------------------------------------- 状態表示LED(緑、共通仕様。単純LEDのまま)
def led_row(x0, y, net, r_ref, r_val, led_ref, led_val, r_desc, led_desc):
    r = add_symbol("Device:R", r_ref, r_val, x0 + 5, y, 90, FP_R, r_desc)
    led = add_symbol("Device:LED", led_ref, led_val, x0 + 15, y, 180, FP_LED, led_desc, ref_off=(-3.81, -3.81), val_off=(-3.81, 3.81))
    stub(r["1"], net=net); note(net, r_ref, "1")
    add_wire(r["2"][0], led["2"][0])          # R -> LEDアノード(pin2)
    note("%s_A" % led_ref, r_ref, "2"); note("%s_A" % led_ref, led_ref, "2")
    stub(led["1"], power="GND"); note("GND", led_ref, "1")


led_row(NP_X0, NP_Y1 + 60, "STATUS", "R14", "47", "LED1", "OSG58A3131A",
        "Status LED current-limiting resistor, 47ohm (common spec, all puzzle modules).", "Status LED (green, lit while defused; common spec)")

# ---------------------------------------------------------------- 書き出し
def build_sheet():
    head = ["(kicad_sch", "\t(version 20260306)", "\t(generator \"eeschema\")", "\t(generator_version \"10.0\")",
            "\t(uuid \"%s\")" % SHEET_UUID, "\t(paper \"A3\")",
            "\t(title_block", "\t\t(title \"Complicated Wires module\")",
            "\t\t(comment 1 \"OSC2026 bomb defusal prop - Complicated Wires module (cut wires / WJ141V terminals / NeoPixel color)\")",
            "\t\t(comment 2 \"Generated by gen_complicated_wires_sch.py. Design: complicated_wires_design_notes.md\")", "\t)", "\t(lib_symbols"]
    lib_txt = []
    for lid, blk in LIBS.items():
        lib_txt.append("\t\t" + blk.replace("\n", "\n\t"))
    body = wires + labels + syms + nocs + graphics
    tail = ["\t(sheet_instances", "\t\t(path \"/\"", "\t\t\t(page \"1\")", "\t\t)", "\t)", "\t(embedded_fonts no)", ")"]
    return "\n".join(head) + "\n" + "\n".join(lib_txt) + "\n\t)\n" + "\n".join(body) + "\n" + "\n".join(tail) + "\n"


if __name__ == "__main__":
    out = HERE / (PROJECT + ".kicad_sch")
    out.write_text(build_sheet(), encoding="utf-8")
    print("wrote", out, "(%d wires, %d labels, %d symbols, %d no_connects)" % (len(wires), len(labels), len(syms), len(nocs)))
    import json
    (HERE / "expected_nets.json").write_text(json.dumps({k: sorted(v) for k, v in expected.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("expected nets:", len(expected))
