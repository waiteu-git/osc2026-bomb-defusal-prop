# -*- coding: utf-8 -*-
"""ワイヤーモジュールの回路図(wires.kicad_sch)生成スクリプト(2026-09-24新方針: 切る/端子台交換/NeoPixel)。

設計の中身は wires_design_notes.md の§4・§6。複雑ワイヤ担当の gen_complicated_wires_sch.py と同じ方式:
- 座標はすべて1.27mm格子の整数倍(内部では格子単位の整数で扱う)
- ワイヤーは常に2点、全ピンに「2.54mmのスタブ線+ラベル(または電源シンボル)」を付けて、ネット名で接続する
- ライブラリシンボルは検証済みの既存回路図とKiCad標準ライブラリから埋め込む(サブユニット名にライブラリ名を付けない)
使い方: python gen_wires_sch.py  (同じフォルダに wires.kicad_sch と expected_nets.json を書き出す)
"""
import math
import re
import sys
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
HW = HERE.parent
PROJECT = "wires"
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


PW = HW / "password" / "password.kicad_sch"
CW = HW / "complicated_wires" / "complicated_wires.kicad_sch"
LIBS = {
    "Connector_Generic:Conn_01x04": from_sch(PW, "Connector_Generic:Conn_01x04"),
    "Connector_Generic:Conn_01x02": from_sch(CW, "Connector_Generic:Conn_01x02"),
    "Device:LED": from_sch(PW, "Device:LED"),
    "Device:R": from_sch(PW, "Device:R"),
    "RPi_Pico:Pico": from_sch(PW, "RPi_Pico:Pico"),
    "power:+3.3V": from_sch(PW, "power:+3.3V"),
    "power:+5V": from_sch(PW, "power:+5V"),
    "power:GND": from_sch(PW, "power:GND"),
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
wires, labels, nocs, syms = [], [], [], []
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


def prop(name, val, x, y, hide=False, size=1.27):
    return ("\t\t(property \"%s\" \"%s\"\n\t\t\t(at %s %s 0)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n"
            "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size %.2f %.2f)\n\t\t\t\t)\n\t\t\t)\n\t\t)"
            % (name, val.replace('"', "'"), x, y, "\t\t\t(hide yes)\n" if hide else "", size, size))


def add_symbol(lib, ref, value, gx, gy, rot=0, footprint="", desc="", ref_off=(0, -3.81), val_off=(0, 3.81), hide_ref=False):
    """シンボルを置き、各ピンの絶対座標(格子単位)と外向きの向きを返す。ピンの絶対座標は (配置X+ローカルX, 配置Y-ローカルY)"""
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
             prop("Value", value, "%.2f" % (px + val_off[0]), "%.2f" % (py + val_off[1])),
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
        val_off = (0, 3.81 if kind == "GND" else -5.08)
    add_symbol("power:" + kind, ref, kind, p[0], p[1], power_rot(kind, d), "",
               "Power symbol creates a global label with name \"%s\"" % kind,
               ref_off=(0, 3.81), val_off=val_off, hide_ref=True)


def add_flag(p, d=(0, -1)):
    flg_n[0] += 1
    add_symbol("power:PWR_FLAG", "#FLG%02d" % flg_n[0], "PWR_FLAG", p[0], p[1], power_rot("+5V", d), "", "Power flag: marks this net as driven",
               ref_off=(0, -3.81), val_off=(d[0] * 7.62, -1.27) if d[0] else (0, -5.08), hide_ref=True)


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
    elif flag:
        far = (end[0] + 2 * d[0], end[1] + 2 * d[1])
        add_wire(end, far)
        add_flag(far, d)
    if net:
        add_label(net, end, d)
    return end


FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
FP_LED = "LED_THT:LED_D3.0mm"
FP_NEO = "LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm"
FP_TB = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"   # WJ141Vの仮フットプリント(実寸7.62x12.9x13.8mm、足は2.54mmピッチ)
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
    "1": "UART_TX", "2": "UART_RX",                                                     # GP0 / GP1(通信専用、予約)
    "4": "WIRE1", "5": "WIRE2", "6": "WIRE3", "7": "WIRE4", "9": "WIRE5", "10": "WIRE6",   # GP2〜GP7: 断線検出
    "11": "STATUS",                                                                     # GP8: 状態表示LED
    "12": "NEO_OUT",                                                                    # GP9: NeoPixelデータ
}
PICO_GND = ["3", "8", "13", "18", "23", "28", "33", "38", "42"]
PICO_NC = ["14", "15", "16", "17", "19", "20", "21", "22", "24", "25", "26", "27",
           "29", "30", "31", "32", "34", "35", "37", "40", "41", "43"]   # 未使用GPIO・RUN・ADC_VREF・3V3_EN・VBUS・SWCLK・SWDIO
for pn, net in PICO_NETS.items():
    stub(u1[pn], net=net)
    note(net, "U1", pn)
for pn in PICO_GND:
    stub(u1[pn], power="GND")
    note("GND", "U1", pn)
stub(u1["36"], power="+3.3V", flag=True)   # 3V3(OUT): 外付けプルアップの電源
note("+3.3V", "U1", "36")
stub(u1["39"], power="+5V")                # VSYS: ホストの5Vで動作
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

# 電源のコンデンサ(NeoPixel用。値は一般的な設計慣行で未検証)
c1 = add_symbol("Device:C_Polarized", "C1", "100uF/16V", 270, 33, 0, FP_CP, "NeoPixel supply bulk capacitor (insurance, value by convention)",
                ref_off=(5.08, -1.27), val_off=(6.35, 1.27))
stub(c1["1"], net="+5V_NEO"); note("+5V_NEO", "C1", "1")
stub(c1["2"], power="GND"); note("GND", "C1", "2")
c2 = add_symbol("Device:C", "C2", "0.1uF", 285, 33, 0, FP_C, "Decoupling near first NeoPixel (optional)",
                ref_off=(5.08, -1.27), val_off=(5.08, 1.27))
stub(c2["1"], net="+5V_NEO"); note("+5V_NEO", "C2", "1")
stub(c2["2"], power="GND"); note("GND", "C2", "2")

# NeoPixel電源の保険用ランド: 通常は0Ωジャンパー。WS2812Bの版によってVIHが変わる(0.63xVDD等)ため、
# 実機で3.3V直結が不安定なら1N4007(カソードをNeoPixel側)を実装してVDDを約0.7V下げる
r15 = add_symbol("Device:R", "R15", "0R (or 1N4007)", 268, 60, 90, FP_R,
                 "Insurance land between +5V and NeoPixel VDD: 0-ohm jumper by default; a 1N4007 (cathode to NeoPixel side) drops VDD about 0.7V if the 3.3V data input margin is insufficient")
stub(r15["1"], power="+5V"); note("+5V", "R15", "1")
stub(r15["2"], net="+5V_NEO", flag=True); note("+5V_NEO", "R15", "2")

# ---------------------------------------------------------------- 端子台とワイヤー検出
TB_X = 28
for k in range(3):
    s = add_symbol("Connector_Generic:Conn_01x02", "S%d" % (k + 1), "WJ141V-2.54-02P", TB_X, 20 + 10 * k, 0, FP_TB,
                   "Signal-side spring terminal (2 poles: wire %d and %d). Real part WJ141V-2.54-02P-146-00A" % (2 * k + 1, 2 * k + 2),
                   ref_off=(0, -3.81), val_off=(0, 6.35))
    stub(s["1"], net="WIRE%d_T" % (2 * k + 1)); note("WIRE%d_T" % (2 * k + 1), "S%d" % (k + 1), "1")
    stub(s["2"], net="WIRE%d_T" % (2 * k + 2)); note("WIRE%d_T" % (2 * k + 2), "S%d" % (k + 1), "2")
for k in range(3):
    gsym = add_symbol("Connector_Generic:Conn_01x02", "G%d" % (k + 1), "WJ141V-2.54-02P", TB_X, 60 + 10 * k, 0, FP_TB,
                      "GND-side spring terminal (2 poles: wire %d and %d, both GND). Real part WJ141V-2.54-02P-146-00A" % (2 * k + 1, 2 * k + 2),
                      ref_off=(0, -3.81), val_off=(0, 6.35))
    stub(gsym["1"], power="GND"); note("GND", "G%d" % (k + 1), "1")
    stub(gsym["2"], power="GND"); note("GND", "G%d" % (k + 1), "2")

RS_X, RPU_X = 72, 100
for k in range(6):
    y = 20 + 10 * k
    rs_ref, rpu_ref = "R%d" % (k + 1), "R%d" % (k + 7)
    rs = add_symbol("Device:R", rs_ref, "1k", RS_X, y, 90, FP_R, "Wire %d detect: series resistor (ESD protection for exposed terminal)" % (k + 1))
    rpu = add_symbol("Device:R", rpu_ref, "10k", RPU_X, y, 90, FP_R, "Wire %d detect: external pull-up to 3V3 (internal pull-up disabled)" % (k + 1))
    stub(rs["1"], net="WIRE%d_T" % (k + 1)); note("WIRE%d_T" % (k + 1), rs_ref, "1")
    # R_s右ピン -> スタブ端(ラベルWIREk) -> R_pu左ピン
    p_right = rs["2"][0]
    p_mid = (p_right[0] + 2, p_right[1])
    add_wire(p_right, p_mid)
    add_label("WIRE%d" % (k + 1), p_mid, (1, 0))
    add_wire(p_mid, rpu["1"][0])
    note("WIRE%d" % (k + 1), rs_ref, "2"); note("WIRE%d" % (k + 1), rpu_ref, "1")
    stub(rpu["2"], power="+3.3V"); note("+3.3V", rpu_ref, "2")

# ---------------------------------------------------------------- NeoPixel(6個チェーン、ワイヤー1〜6の順)
NP_Y = 120
NP_X0, NP_DX = 60, 30
r13 = add_symbol("Device:R", "R13", "330", 24, NP_Y, 90, FP_R, "NeoPixel data series resistor (at the first pixel)")
stub(r13["1"], net="NEO_OUT"); note("NEO_OUT", "R13", "1")
prev = None
for k in range(6):
    ref = "D%d" % (k + 1)
    x = NP_X0 + NP_DX * k
    d = add_symbol("LED:WS2812B", ref, "WS2812B(V5)", x, NP_Y, 0, FP_NEO,
                   "Wire %d color pixel (WS2812B V5, akizuki g107915). Chain order = wire order" % (k + 1),
                   ref_off=(-8.89, -8.89), val_off=(-8.89, 8.89))
    stub(d["1"], net="+5V_NEO"); note("+5V_NEO", ref, "1")
    stub(d["3"], power="GND"); note("GND", ref, "3")
    if k == 0:
        add_wire(r13["2"][0], d["4"][0])
        note("NEO_DIN", "R13", "2"); note("NEO_DIN", ref, "4")
    else:
        add_wire(prev["2"][0], d["4"][0])
        net = "NP%d_DIN" % (k + 1)
        note(net, "D%d" % k, "2"); note(net, ref, "4")
    prev = d
add_nc(prev["2"][0])

# ---------------------------------------------------------------- 状態表示LED(共通仕様: OSG58A3131A + 47ohm、GP8)
r14 = add_symbol("Device:R", "R14", "47", 45, 152, 90, FP_R, "Status LED current-limiting resistor, 47ohm (common spec, all puzzle modules).")
led1 = add_symbol("Device:LED", "LED1", "OSG58A3131A", 55, 152, 180, FP_LED, "Status LED (green, lit while defused; common spec)",
                  ref_off=(-3.81, -3.81), val_off=(-3.81, 3.81))
stub(r14["1"], net="STATUS"); note("STATUS", "R14", "1")
add_wire(r14["2"][0], led1["2"][0])          # R -> LEDアノード(pin2)
note("LED1_A", "R14", "2"); note("LED1_A", "LED1", "2")
stub(led1["1"], power="GND"); note("GND", "LED1", "1")


# ---------------------------------------------------------------- 書き出し
def build_sheet():
    head = ["(kicad_sch", "\t(version 20260306)", "\t(generator \"eeschema\")", "\t(generator_version \"10.0\")",
            "\t(uuid \"%s\")" % SHEET_UUID, "\t(paper \"A3\")",
            "\t(title_block", "\t\t(title \"Wires module\")",
            "\t\t(comment 1 \"OSC2026 bomb defusal prop - Wires module (cut wires / WJ141V terminals / NeoPixel color)\")",
            "\t\t(comment 2 \"Generated by gen_wires_sch.py. Design: wires_design_notes.md\")", "\t)", "\t(lib_symbols"]
    lib_txt = []
    for lid, blk in LIBS.items():
        lib_txt.append("\t\t" + blk.replace("\n", "\n\t"))
    body = wires + labels + syms + nocs
    tail = ["\t(sheet_instances", "\t\t(path \"/\"", "\t\t\t(page \"1\")", "\t\t)", "\t)", "\t(embedded_fonts no)", ")"]
    return "\n".join(head) + "\n" + "\n".join(lib_txt) + "\n\t)\n" + "\n".join(body) + "\n" + "\n".join(tail) + "\n"


if __name__ == "__main__":
    out = HERE / (PROJECT + ".kicad_sch")
    out.write_text(build_sheet(), encoding="utf-8")
    print("wrote", out, "(%d wires, %d labels, %d symbols, %d no_connects)" % (len(wires), len(labels), len(syms), len(nocs)))
    import json
    (HERE / "expected_nets.json").write_text(json.dumps({k: sorted(v) for k, v in expected.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("expected nets:", len(expected))
