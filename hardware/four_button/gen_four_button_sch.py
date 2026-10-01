#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# four_button module: four_button.kicad_sch の生成スクリプト(2026-10-01作成)。
# キーパッド(2x2グリッド)+サイモン(ひし形)統合基板。button/gen_button_sch.py の手法を踏襲
# (label方式の引き出し配線、lib_symbolsは検証済みブロックを転用、生成後に自動でワイヤー重なり・
#  ピン/ワイヤー端の内部一致をチェックする)。
# 実行: python gen_four_button_sch.py  → four_button.kicad_sch を上書きする。
import os
import uuid as uuidlib

def U():
    return str(uuidlib.uuid4())

T = "\t"
PROJECT = "four_button"
ROOT_UUID = "f4b7c1a0-6e5d-4c2b-9a8f-1d3e5c7b9a60"  # four_button.kicad_pro と一致させる

# ===========================================================================
# 1) Pico(Pico_TH40, 40ピンのみ)のピン配置(button/gen_button_sch.pyと同一)
# ===========================================================================
PICO_PINS = {
    1: (-17.78, 24.13),   2: (-17.78, 21.59),  3: (-17.78, 19.05),  4: (-17.78, 16.51),
    5: (-17.78, 13.97),   6: (-17.78, 11.43),  7: (-17.78, 8.89),   8: (-17.78, 6.35),
    9: (-17.78, 3.81),    10: (-17.78, 1.27),  11: (-17.78, -1.27), 12: (-17.78, -3.81),
    13: (-17.78, -6.35),  14: (-17.78, -8.89), 15: (-17.78, -11.43),16: (-17.78, -13.97),
    17: (-17.78, -16.51), 18: (-17.78, -19.05),19: (-17.78, -21.59),20: (-17.78, -24.13),
    21: (17.78, -24.13),  22: (17.78, -21.59), 23: (17.78, -19.05), 24: (17.78, -16.51),
    25: (17.78, -13.97),  26: (17.78, -11.43), 27: (17.78, -8.89),  28: (17.78, -6.35),
    29: (17.78, -3.81),   30: (17.78, -1.27),  31: (17.78, 1.27),   32: (17.78, 3.81),
    33: (17.78, 6.35),    34: (17.78, 8.89),   35: (17.78, 11.43),  36: (17.78, 13.97),
    37: (17.78, 16.51),   38: (17.78, 19.05),  39: (17.78, 21.59),  40: (17.78, 24.13),
}
PICO_NAMES = {
    1: "GPIO0", 2: "GPIO1", 3: "GND", 4: "GPIO2", 5: "GPIO3", 6: "GPIO4", 7: "GPIO5", 8: "GND",
    9: "GPIO6", 10: "GPIO7", 11: "GPIO8", 12: "GPIO9", 13: "GND", 14: "GPIO10", 15: "GPIO11",
    16: "GPIO12", 17: "GPIO13", 18: "GND", 19: "GPIO14", 20: "GPIO15", 21: "GPIO16", 22: "GPIO17",
    23: "GND", 24: "GPIO18", 25: "GPIO19", 26: "GPIO20", 27: "GPIO21", 28: "GND", 29: "GPIO22",
    30: "RUN", 31: "GPIO26_ADC0", 32: "GPIO27_ADC1", 33: "AGND", 34: "GPIO28_ADC2",
    35: "ADC_VREF", 36: "3V3", 37: "3V3_EN", 38: "GND", 39: "VSYS", 40: "VBUS",
}
GRID = 1.27
def G(n):
    return round(n * GRID, 4)

PICO_POS = (G(120), G(70))  # =(152.4, 88.9)、A3シートに全体を収める

def pico_abs(pin):
    lx, ly = PICO_PINS[pin]
    return (round(PICO_POS[0] + lx, 4), round(PICO_POS[1] - ly, 4))

CONN01X04_PINS = {1: (-5.08, 2.54), 2: (-5.08, 0.0), 3: (-5.08, -2.54), 4: (-5.08, -5.08)}
SW_PINS = {1: (-5.08, 0.0), 2: (5.08, 0.0)}          # ホットスワップソケット(汎用2端子として配線)
LED_PINS = {1: (-3.81, 0.0), 2: (3.81, 0.0)}          # pin1=K, pin2=A
R_PINS = {1: (0.0, 3.81), 2: (0.0, -3.81)}             # Device:R・Device:C共通(縦2端子)
# SK6812のピン番号配置はWS2812Bと物理位置(VDD上/DOUT右/VSS下/DIN左)は同じだが番号が違う
# (WS2812B: 1=VDD,2=DOUT,3=VSS,4=DIN / SK6812: 1=VSS,2=DIN,3=VDD,4=DOUT、KiCad標準ライブラリで実測確認)。
# 2026-10-01: ユーザー決定でWS2812B->SK6812に変更したため、このマッピングに合わせてある。
WS_PINS = {1: (0.0, -7.62), 2: (-7.62, 0.0), 3: (0.0, 7.62), 4: (7.62, 0.0)}  # 1=VSS,2=DIN,3=VDD,4=DOUT

def abs_pt(placement, local):
    return (round(placement[0] + local[0], 4), round(placement[1] - local[1], 4))

GND_PINS = [3, 8, 13, 18, 23, 28, 33, 38]
# 使用ピン: 1,2(UART) / 4,5,6,7(ボタン共用GP2-5) / 9(NeoPixelデータ GP6、SK6812 x4を1本で数珠つなぎ) /
# 14(状態LED GP10) / 15(モード選択 GP11)。GP7-9(旧LEDDRV_B/G/Y)はNeoPixel化で不要になり予備(未接続)。
USED_PINS = {1, 2, 4, 5, 6, 7, 9, 14, 15}
NC_PINS = [p for p in range(1, 41) if p not in USED_PINS and p not in GND_PINS and p not in (36, 39)]

# ===========================================================================
# 2) レイアウト定数
# ===========================================================================
PICO_LEFT_X = PICO_POS[0] - 17.78
PICO_RIGHT_X = PICO_POS[0] + 17.78
STUB = G(6)

J1_PIN_X = PICO_LEFT_X - G(30)
tx_abs = pico_abs(1)
rx_abs = pico_abs(2)
j1_place_y = round(tx_abs[1] + CONN01X04_PINS[1][1], 4)
j1_place_x = round(J1_PIN_X + 5.08, 4)
J1_POS = (j1_place_x, j1_place_y, 0)

# 左列(GP2-5): ボタン共用ネット BTN_R/BTN_B/BTN_G/BTN_Y (=グリッドA-D と ひし形Red/Blue/Green/Yellow を並列)
# GP6=NeoPixel(SK6812 x4直列)のデータ入力。GP7-9は未使用(予備)。
LEFT_STUBS = {4: "BTN_R", 5: "BTN_B", 6: "BTN_G", 7: "BTN_Y", 9: "NEOPIXEL_DATA",
              14: "STATUS_LED", 15: "MODE_SEL"}

# --- グリッド(キーパッド、対角±19mm)とひし形(サイモン、軸17mm)のソケット位置 ---
# 中心(0,0)基準の相対座標(mm)。実際のシート配置はブロックごとにオフセットして描く(格子1.27mm)。
GRID_SW = {"SW1": ("A(top-left)", -19, -19, "BTN_R"), "SW2": ("B(top-right)", 19, -19, "BTN_B"),
           "SW3": ("C(bottom-left)", -19, 19, "BTN_G"), "SW4": ("D(bottom-right)", 19, 19, "BTN_Y")}
# dref=SK6812参照符号、cref=隣の0.1uFデコップリングコンデンサ(Noneなら省略)。鎖の順序はdict順
# (Red->Blue->Green->Yellow)。2026-10-01: complicated_wiresモジュール(20個中1個だけ"(optional)"で
# デコップリング)に倣い、チェーン先頭のD1(Red)だけC2を残し、D2-D4は省略(ユーザー決定)。
DIAMOND_SW = {"SW5": ("Red(left)", -17, 0, "BTN_R", "Red", "D1", "C2"),
              "SW6": ("Blue(top)", 0, -17, "BTN_B", "Blue", "D2", None),
              "SW7": ("Green(bottom)", 0, 17, "BTN_G", "Green", "D3", None),
              "SW8": ("Yellow(right)", 17, 0, "BTN_Y", "Yellow", "D4", None)}

# シート上のブロック配置(格子G(n)、Picoから離れた場所にまとめて置き、ラベルで結ぶ)
GRID_BLOCK_X0 = G(250)
GRID_BLOCK_Y0 = G(40)
GRID_PITCH = G(20)
grid_place = {}
for i, ref in enumerate(["SW1", "SW2", "SW3", "SW4"]):
    col = i % 2
    row = i // 2
    grid_place[ref] = (round(GRID_BLOCK_X0 + col * GRID_PITCH, 4), round(GRID_BLOCK_Y0 + row * GRID_PITCH, 4), 0)

DIAMOND_BLOCK_X0 = G(320)
diamond_place = {}
for i, ref in enumerate(["SW5", "SW6", "SW7", "SW8"]):
    diamond_place[ref] = (round(DIAMOND_BLOCK_X0, 4), round(GRID_BLOCK_Y0 + i * GRID_PITCH, 4), 0)

# NeoPixel(SK6812)4個を横一列に、各LEDの下にデコップリングコンデンサ。GP6からR10(直列抵抗)経由で
# D1->D2->D3->D4の順に数珠つなぎ(DOUT->次のDIN)。
CHAIN_Y0 = G(140)
CHAIN_PITCH = G(16)
chain_place = {}
for i, swref in enumerate(DIAMOND_SW.keys()):
    cx = round(GRID_BLOCK_X0 + G(20) + i * CHAIN_PITCH, 4)
    # SK6812のピンはローカル中心から上下左右7.62mm伸びるため、コンデンサ(cのPIN2)は
    # VSS側(下、+7.62)からさらに十分離す(電源フラグの延長ぶんも込みで+G(10)=12.7mm追加)。
    chain_place[swref] = dict(d=(cx, CHAIN_Y0, 0), c=(cx, round(CHAIN_Y0 + G(24), 4), 0))
R10_POS = (GRID_BLOCK_X0, CHAIN_Y0, 0)

# 状態LED
STATUS_R_POS = (G(45), G(80), 0)
STATUS_LED_POS = (G(56), G(80), 0)

# モード選択スイッチ(GP11)
MODE_SW_POS = (G(45), G(95), 0)

# バルクコンデンサC1
C1_POS = (round(J1_PIN_X - 5.08, 4), round(abs_pt(J1_POS[:2], CONN01X04_PINS[3])[1] + 3.81, 4), 0)

# ===========================================================================
# 3) lib_symbols(button/simon/password の検証済みブロックを転用)
# ===========================================================================
KICAD_SYM = "C:/Program Files/KiCad/10.0/share/kicad/symbols/"

def _extract_stock(path, name, new_name):
    txt = open(path, encoding="utf-8").read()
    a = txt.index('\t(symbol "' + name + '"\n')
    depth = 0
    for i in range(a, len(txt)):
        if txt[i] == "(":
            depth += 1
        elif txt[i] == ")":
            depth -= 1
            if depth == 0:
                blk = txt[a:i + 1].strip("\t")
                assert blk.count(f'(symbol "{name}"') == 1
                return blk.replace(f'(symbol "{name}"', f'(symbol "{new_name}"', 1)

LIB_CONN01X04 = _extract_stock(KICAD_SYM + "Connector_Generic.kicad_sym", "Conn_01x04", "Connector_Generic:Conn_01x04")
LIB_LED = _extract_stock(KICAD_SYM + "Device.kicad_sym", "LED", "Device:LED")
LIB_R = _extract_stock(KICAD_SYM + "Device.kicad_sym", "R", "Device:R")
LIB_C = _extract_stock(KICAD_SYM + "Device.kicad_sym", "C", "Device:C")
LIB_CP = _extract_stock(KICAD_SYM + "Device.kicad_sym", "C_Polarized", "Device:C_Polarized")
LIB_SK6812 = _extract_stock(KICAD_SYM + "LED.kicad_sym", "SK6812", "LED:SK6812")
LIB_SW = _extract_stock(KICAD_SYM + "Switch.kicad_sym", "SW_Push", "Switch:SW_Push")
LIB_SW_SPST = _extract_stock(KICAD_SYM + "Switch.kicad_sym", "SW_SPST", "Switch:SW_SPST")
LIB_GND = _extract_stock(KICAD_SYM + "power.kicad_sym", "GND", "power:GND")
LIB_3V3 = _extract_stock(KICAD_SYM + "power.kicad_sym", "+3.3V", "power:+3.3V")
LIB_5V = _extract_stock(KICAD_SYM + "power.kicad_sym", "+5V", "power:+5V")
LIB_PWRFLAG = _extract_stock(KICAD_SYM + "power.kicad_sym", "PWR_FLAG", "power:PWR_FLAG")
LIB_PICO = _extract_stock(
    "C:/Users/ysou5/OneDrive - 東京理科大学/ドキュメント/osc/hardware/shared_lib/OSC_Shared.kicad_sym",
    "Pico_TH40", "OSC_Shared:Pico_TH40")

# ローカル: ホットスワップソケット(daprice Kailh_socket_MX、2端子の汎用スイッチとして表現)
LIB_SOCKET = r'''(symbol "FourButton_Local:Kailh_socket_MX"
	(pin_numbers (hide yes))
	(pin_names (offset 1.016) (hide yes))
	(exclude_from_sim no)
	(in_bom yes)
	(on_board yes)
	(in_pos_files yes)
	(duplicate_pin_numbers_are_jumpers no)
	(property "Reference" "SW" (at 1.27 2.54 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)) (justify left)))
	(property "Value" "Kailh_socket_MX" (at 0 -1.524 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
	(property "Footprint" "FourButton_Local:Kailh_socket_MX" (at 0 5.08 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Datasheet" "" (at 0 5.08 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Description" "Kailh MX-compatible hotswap socket (daprice keyswitches.pretty). 2-terminal, no inherent GND/signal side." (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "ki_keywords" "switch hotswap kailh mx" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(symbol "Kailh_socket_MX_0_1"
		(circle (center -2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 0 1.27) (xy 0 3.048)) (stroke (width 0) (type default)) (fill (type none)))
		(circle (center 2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 2.54 1.27) (xy -2.54 1.27)) (stroke (width 0) (type default)) (fill (type none)))
		(pin passive line (at -5.08 0 0) (length 2.54) (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
		(pin passive line (at 5.08 0 180) (length 2.54) (name "2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
	)
	(embedded_fonts no)
)'''

LIB_SYMBOLS_ALL = [LIB_CONN01X04, LIB_LED, LIB_R, LIB_C, LIB_CP, LIB_SW, LIB_SW_SPST, LIB_PICO, LIB_SK6812,
                   LIB_SOCKET, LIB_GND, LIB_3V3, LIB_5V, LIB_PWRFLAG]

def reindent(block, base_tabs):
    lines = block.split("\n")
    out = []
    for ln in lines:
        out.append((T * base_tabs) + ln if ln.strip() else ln)
    return "\n".join(out)

# ===========================================================================
# 4) placed-symbol / wire / no_connect emitters(button/gen_button_sch.pyと同一)
# ===========================================================================
def prop_block(name, value, at, hide=False, justify=None, base_tabs=2):
    just = f' (justify {justify})' if justify else ''
    hide_s = '\n' + T*(base_tabs+1) + '(hide yes)' if hide else ''
    return (
        f'{T*base_tabs}(property "{name}" "{value}"\n'
        f'{T*(base_tabs+1)}(at {at[0]:g} {at[1]:g} {at[2] if len(at)>2 else 0})' + hide_s + '\n'
        f'{T*(base_tabs+1)}(show_name no)\n'
        f'{T*(base_tabs+1)}(do_not_autoplace no)\n'
        f'{T*(base_tabs+1)}(effects\n'
        f'{T*(base_tabs+2)}(font\n'
        f'{T*(base_tabs+3)}(size 1.27 1.27)\n'
        f'{T*(base_tabs+2)}){just}\n'
        f'{T*(base_tabs+1)})\n'
        f'{T*base_tabs})'
    )

def esc(s):
    return s.replace('\\', r'\\').replace('"', r'\"')

def placed_symbol(lib_id, ref, value, footprint, at, pins, description, ref_at=None, val_at=None, hide_value=False):
    x, y, angle = at
    body = []
    body.append(f'{T}(symbol')
    body.append(f'{T*2}(lib_id "{lib_id}")')
    body.append(f'{T*2}(at {x:g} {y:g} {angle})')
    body.append(f'{T*2}(unit 1)')
    body.append(f'{T*2}(body_style 1)')
    body.append(f'{T*2}(exclude_from_sim no)')
    body.append(f'{T*2}(in_bom yes)')
    body.append(f'{T*2}(on_board yes)')
    body.append(f'{T*2}(in_pos_files yes)')
    body.append(f'{T*2}(dnp no)')
    body.append(f'{T*2}(fields_autoplaced yes)')
    body.append(f'{T*2}(uuid "{U()}")')
    body.append(prop_block("Reference", ref, ref_at if ref_at else (x, y - 5.08, 0)))
    body.append(prop_block("Value", value, val_at if val_at else (x, y + 5.08, 0), hide=hide_value))
    body.append(prop_block("Footprint", footprint, (x, y, 0), hide=True))
    body.append(prop_block("Datasheet", "", (x, y, 0), hide=True))
    body.append(prop_block("Description", esc(description), (x, y, 0), hide=True))
    for p in pins:
        body.append(f'{T*2}(pin "{p}"')
        body.append(f'{T*3}(uuid "{U()}")')
        body.append(f'{T*2})')
    body.append(f'{T*2}(instances')
    body.append(f'{T*3}(project "{PROJECT}"')
    body.append(f'{T*4}(path "/{ROOT_UUID}"')
    body.append(f'{T*5}(reference "{ref}")')
    body.append(f'{T*5}(unit 1)')
    body.append(f'{T*4})')
    body.append(f'{T*3})')
    body.append(f'{T*2})')
    body.append(f'{T})')
    return "\n".join(body)

def power_symbol_block(lib_id, at_xy, angle, ref, desc=None, hide_value=False):
    x, y = at_xy
    val = lib_id.split(":")[1]
    body = []
    body.append(f'{T}(symbol')
    body.append(f'{T*2}(lib_id "{lib_id}")')
    body.append(f'{T*2}(at {x:g} {y:g} {angle})')
    body.append(f'{T*2}(unit 1)')
    body.append(f'{T*2}(body_style 1)')
    body.append(f'{T*2}(exclude_from_sim no)')
    body.append(f'{T*2}(in_bom yes)')
    body.append(f'{T*2}(on_board yes)')
    body.append(f'{T*2}(in_pos_files yes)')
    body.append(f'{T*2}(dnp no)')
    body.append(f'{T*2}(fields_autoplaced yes)')
    body.append(f'{T*2}(uuid "{U()}")')
    body.append(prop_block("Reference", ref, (x, y - 3.81, 0), hide=True))
    body.append(prop_block("Value", val, (x + 2.54, y, 90), justify="left", hide=hide_value))
    body.append(prop_block("Footprint", "", (x, y, 0), hide=True))
    body.append(prop_block("Datasheet", "", (x, y, 0), hide=True))
    body.append(prop_block("Description", desc if desc else f'Power symbol creates a global label with name \\"{val}\\"', (x, y, 0), hide=True))
    body.append(f'{T*2}(pin "1"')
    body.append(f'{T*3}(uuid "{U()}")')
    body.append(f'{T*2})')
    body.append(f'{T*2}(instances')
    body.append(f'{T*3}(project "{PROJECT}"')
    body.append(f'{T*4}(path "/{ROOT_UUID}"')
    body.append(f'{T*5}(reference "{ref}")')
    body.append(f'{T*5}(unit 1)')
    body.append(f'{T*4})')
    body.append(f'{T*3})')
    body.append(f'{T*2})')
    body.append(f'{T})')
    return "\n".join(body)

def wire_block(p1, p2):
    return (
        f'{T}(wire\n'
        f'{T*2}(pts\n'
        f'{T*3}(xy {p1[0]:g} {p1[1]:g}) (xy {p2[0]:g} {p2[1]:g})\n'
        f'{T*2})\n'
        f'{T*2}(stroke (width 0) (type default))\n'
        f'{T*2}(uuid "{U()}")\n'
        f'{T})'
    )

def no_connect_block(pt):
    return (
        f'{T}(no_connect\n'
        f'{T*2}(at {pt[0]:g} {pt[1]:g})\n'
        f'{T*2}(uuid "{U()}")\n'
        f'{T})'
    )

def label_block(name, at_xy, angle):
    just = "right bottom" if angle == 180 else "left bottom"
    return "\n".join([
        f'{T}(label "{name}"',
        f'{T*2}(at {at_xy[0]:g} {at_xy[1]:g} {angle})',
        f'{T*2}(effects',
        f'{T*3}(font',
        f'{T*4}(size 1.27 1.27)',
        f'{T*3})',
        f'{T*3}(justify {just})',
        f'{T*2})',
        f'{T*2}(uuid "{U()}")',
        f'{T})',
    ])

def text_block(s, at_xy, size=1.905):
    return "\n".join([
        f'{T}(text "{esc(s)}"',
        f'{T*2}(exclude_from_sim no)',
        f'{T*2}(at {at_xy[0]:g} {at_xy[1]:g} 0)',
        f'{T*2}(effects',
        f'{T*3}(font',
        f'{T*4}(size {size:g} {size:g})',
        f'{T*3})',
        f'{T*3}(justify left bottom)',
        f'{T*2})',
        f'{T*2}(uuid "{U()}")',
        f'{T})',
    ])

# ===========================================================================
# 5) 組み立て
# ===========================================================================
lines = []
lines.append('(kicad_sch')
lines.append(f'{T}(version 20260306)')
lines.append(f'{T}(generator "eeschema")')
lines.append(f'{T}(generator_version "10.0")')
lines.append(f'{T}(uuid "{ROOT_UUID}")')
lines.append(f'{T}(paper "A3")')
lines.append(f'{T}(title_block')
lines.append(f'{T*2}(title "Four-button module (keypad + simon, hotswap-shared board)")')
lines.append(f'{T*2}(comment 1 "OSC2026 bomb defusal prop - shared board, grid+diamond hotswap sockets")')
lines.append(f'{T})')
lines.append(f'{T}(lib_symbols')
for blk in LIB_SYMBOLS_ALL:
    lines.append(reindent(blk, 2))
lines.append(f'{T})')

ALL_SEGMENTS = []

def wire(p1, p2, net):
    lines.append(wire_block(p1, p2))
    ALL_SEGMENTS.append((p1, p2, net))

LABELS = []

def stub(p_from, p_to, net, angle):
    wire(p_from, p_to, net)
    LABELS.append((net, p_to, angle))

# --- UART(J1): Picoへ直結 -------------------------------------------------
wire(abs_pt(J1_POS[:2], CONN01X04_PINS[1]), tx_abs, "UART0_TX")
wire(abs_pt(J1_POS[:2], CONN01X04_PINS[2]), rx_abs, "UART0_RX")

# --- Picoの左列: ボタン共用4本・LED駆動4本・状態LED・モード選択 --------------
for pin, net in LEFT_STUBS.items():
    p = pico_abs(pin)
    stub(p, (round(PICO_LEFT_X - STUB, 4), p[1]), net, 180)

# --- グリッドSW1-4: pin1=GND, pin2=共用ボタンネット -------------------------
component_pins = [(f"U1.{k}", pico_abs(k)) for k in range(1, 41)]
component_pins += [(f"J1.{k}", abs_pt(J1_POS[:2], CONN01X04_PINS[k])) for k in range(1, 5)]

for ref, (label, dx, dy, btn_net) in GRID_SW.items():
    place = grid_place[ref]
    p2 = abs_pt(place[:2], SW_PINS[2])
    p1 = abs_pt(place[:2], SW_PINS[1])
    stub(p2, (round(p2[0] + G(4), 4), p2[1]), btn_net, 0)
    component_pins += [(f"{ref}.1", p1), (f"{ref}.2", p2)]

# --- ひし形SW5-8: pin1=GND, pin2=共用ボタンネット(グリッドと同名ネットで並列)---
for ref, (label, dx, dy, btn_net, color, dref, cref) in DIAMOND_SW.items():
    place = diamond_place[ref]
    p2 = abs_pt(place[:2], SW_PINS[2])
    p1 = abs_pt(place[:2], SW_PINS[1])
    stub(p2, (round(p2[0] + G(4), 4), p2[1]), btn_net, 0)
    component_pins += [(f"{ref}.1", p1), (f"{ref}.2", p2)]

# --- NeoPixel(SK6812 x4)の数珠つなぎ: GP6--R10(直列抵抗)-->D1.DIN->D1.DOUT->D2.DIN->...->D4.DOUT(終端、未接続) ---
# 各SK6812のVDD/VSSにはデコップリングコンデンサ(0.1uF)を1個ずつ並列配置。
r10_pin1 = abs_pt(R10_POS[:2], R_PINS[1])
r10_pin2 = abs_pt(R10_POS[:2], R_PINS[2])
stub(r10_pin1, (r10_pin1[0], round(r10_pin1[1] - G(4), 4)), "NEOPIXEL_DATA", 0)
component_pins += [("R10.1", r10_pin1), ("R10.2", r10_pin2)]

chain_refs = list(DIAMOND_SW.items())
prev_dout = r10_pin2  # R10の出口から鎖がスタート
for idx, (ref, (label, dx, dy, btn_net, color, dref, cref)) in enumerate(chain_refs):
    g = chain_place[ref]
    d_place = g["d"]
    vdd = abs_pt(d_place[:2], WS_PINS[3])
    dout = abs_pt(d_place[:2], WS_PINS[4])
    vss = abs_pt(d_place[:2], WS_PINS[1])
    din = abs_pt(d_place[:2], WS_PINS[2])
    wire(prev_dout, din, f"NEOPIXEL_D{idx}")
    # D・Cそれぞれに独立した電源シンボルを付ける(button/simon踏襲のadd_power_flag方式、下の電源セクション参照)。
    # 物理的な配線では繋がずnet名(+5V/GND)だけで結合するため、長距離配線のクロスを避けられる。
    component_pins += [
        (f"{dref}.1", vdd), (f"{dref}.2", dout), (f"{dref}.3", vss), (f"{dref}.4", din),
    ]
    if cref is not None:
        c_place = g["c"]
        c_pin1 = abs_pt(c_place[:2], R_PINS[1])
        c_pin2 = abs_pt(c_place[:2], R_PINS[2])
        component_pins += [(f"{cref}.1", c_pin1), (f"{cref}.2", c_pin2)]
    prev_dout = dout
# 鎖の終端(D4.DOUT)は未接続
lines.append(no_connect_block(prev_dout))

# --- 状態LED(緑) -----------------------------------------------------------
rstatus_pin1 = abs_pt(STATUS_R_POS[:2], R_PINS[1])
rstatus_pin2 = abs_pt(STATUS_R_POS[:2], R_PINS[2])
stub(rstatus_pin1, (rstatus_pin1[0], round(rstatus_pin1[1] - G(4), 4)), "STATUS_LED", 0)
led_status_anode = abs_pt(STATUS_LED_POS[:2], LED_PINS[2])
led_status_cathode = abs_pt(STATUS_LED_POS[:2], LED_PINS[1])
wire(rstatus_pin2, led_status_anode, "STATUS_LED_ANODE")

# --- モード選択スイッチ(GP11、内部プルアップ、GNDで「ひし形モード」) --------
mode_pin2 = abs_pt(MODE_SW_POS[:2], SW_PINS[2])
mode_pin1 = abs_pt(MODE_SW_POS[:2], SW_PINS[1])
stub(mode_pin2, (round(mode_pin2[0] + G(4), 4), mode_pin2[1]), "MODE_SEL", 0)

# ===========================================================================
# 部品配置
# ===========================================================================
lines.append(placed_symbol("OSC_Shared:Pico_TH40", "U1", "Pico 2 H", "OSC_Shared:RPi_Pico_TH_Headers",
                            (PICO_POS[0], PICO_POS[1], 0), list(range(1, 41)),
                            "Four-button module MCU (Raspberry Pi Pico 2 H on 2.54mm headers, floating ~2.5mm; "
                            "40 header pins only, hub decision 2026-09-30). GP2-5=button inputs (shared between "
                            "grid and diamond sockets, only one set populated at a time). GP6=NeoPixel data "
                            "(SK6812 x4 daisy-chained via R10, unused in grid/keypad mode). GP7-9=spare/unused "
                            "(freed up by the 2026-10-01 NeoPixel switch, previously LEDDRV_B/G/Y). GP10=status "
                            "LED. GP11=mode-select switch."))

lines.append(placed_symbol("Connector_Generic:Conn_01x04", "J1", "MODULE_JST_XH_4P",
                            "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", J1_POS, [1, 2, 3, 4],
                            "Host connector, JST XH 4-pole. Pin1=GPIO0(UART0 TX, module->host), "
                            "Pin2=GPIO1(UART0 RX, host->module), Pin3=VCC(5V, from host per-slot polyfuse "
                            "MF-RX030/72-0 0.3A hold), Pin4=GND. Common to all puzzle modules (see ハブ連絡事項.md).",
                            ref_at=(J1_POS[0], J1_POS[1] - 8.89, 0), val_at=(J1_POS[0], J1_POS[1] - 6.35, 0)))

for ref, (label, dx, dy, btn_net) in GRID_SW.items():
    place = grid_place[ref]
    lines.append(placed_symbol("FourButton_Local:Kailh_socket_MX", ref, "Kailh_socket_MX",
                                "FourButton_Local:Kailh_socket_MX", place, [1, 2],
                                f"Keypad-mode hotswap socket, grid position {label}, panel coords (relative to "
                                f"board centre, y-down) ({dx},{dy}) mm. Wired onto {btn_net} (shared with the "
                                f"diamond-mode socket on the same GPIO; only one set of switches is plugged in "
                                f"at a time -- see four_button_coordinate_proposal.md). Pin1=GND side, Pin2=GPIO side.",
                                ref_at=(place[0], place[1] - 5.08, 0), val_at=(place[0], place[1] + 5.08, 0),
                                hide_value=True))

for ref, (label, dx, dy, btn_net, color, dref, cref) in DIAMOND_SW.items():
    place = diamond_place[ref]
    lines.append(placed_symbol("FourButton_Local:Kailh_socket_MX", ref, "Kailh_socket_MX",
                                "FourButton_Local:Kailh_socket_MX", place, [1, 2],
                                f"Simon-mode hotswap socket, diamond position {label}, panel coords (relative to "
                                f"board centre, y-down) ({dx},{dy}) mm. Wired onto {btn_net} (shared with the "
                                f"grid-mode socket on the same GPIO). Pin1=GND side, Pin2=GPIO side.",
                                ref_at=(place[0], place[1] - 5.08, 0), val_at=(place[0], place[1] + 5.08, 0),
                                hide_value=True))

lines.append(placed_symbol("Device:R", "R10", "330",
                            "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
                            R10_POS, [1, 2],
                            "Series/damping resistor on the NeoPixel data line (GP6 -> D1.DIN), common WS2812x "
                            "practice to limit ringing/reflection on the one-wire protocol line. ~300-500R typical.",
                            ref_at=(R10_POS[0] + 3.81, R10_POS[1] - 1.27, 0),
                            val_at=(R10_POS[0] + 3.81, R10_POS[1] + 1.27, 0)))

for ref, (label, dx, dy, btn_net, color, dref, cref) in DIAMOND_SW.items():
    g = chain_place[ref]
    lines.append(placed_symbol("LED:SK6812", dref, f"SK6812 {color}", "LED_SMD:LED_SK6812_PLCC4_5.0x5.0mm_P3.2mm",
                                g["d"], [1, 2, 3, 4],
                                f"Addressable RGB LED (NeoPixel-compatible), {color} key. Replaces the discrete "
                                f"LED+2SC1815+resistor driver. 2026-10-01: initially chose WS2812B 5050 SMD over "
                                f"SK6812MINI-E (the latter used in complicated_wires but hard to hand-solder); "
                                f"later changed to the full-size SK6812 5050 (same PLCC4 5.0x5.0mm package/footprint "
                                f"as WS2812B, same physical pin layout, but KiCad's stock SK6812 symbol numbers the "
                                f"pins differently -- pin1=VSS,2=DIN,3=VDD,4=DOUT vs WS2812B's 1=VDD,2=DOUT,3=VSS,"
                                f"4=DIN; verified against both stock library symbols before wiring). Daisy-chained "
                                f"GP6->R10->D1->D2->D3->D4 (chain order = dict order Red/Blue/Green/Yellow); "
                                f"firmware addresses each LED by chain position, colour is software-assigned (not "
                                f"fixed by the LED itself). Pin1=VSS(GND), pin2=DIN, pin3=VDD(+5V), pin4=DOUT. "
                                f"Placed near the {label} key (not aligned to the switch's LED window -- user "
                                f"decision: thin keycap + indirect lighting, see four_button_design_notes.md).",
                                ref_at=(g["d"][0], g["d"][1] - 5.08, 0),
                                val_at=(g["d"][0], g["d"][1] + 5.08, 0)))
    if cref is not None:
        lines.append(placed_symbol("Device:C", cref, "100nF",
                                    "Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm",
                                    g["c"], [1, 2],
                                    f"Local decoupling capacitor for {dref} (VDD-VSS). WS2812x datasheet reference "
                                    f"circuit puts one per LED, but 2026-10-01 user decision (matching "
                                    f"complicated_wires' precedent of a single 'optional' cap on a 20-LED chain) "
                                    f"keeps only this one, on the chain's first/most signal-sensitive LED; "
                                    f"D2-D4 omit theirs.",
                                    ref_at=(g["c"][0] + 3.81, g["c"][1] - 1.27, 0),
                                    val_at=(g["c"][0] + 3.81, g["c"][1] + 1.27, 0)))

lines.append(placed_symbol("Device:R", "R9", "47", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
                            STATUS_R_POS, [1, 2], "Status LED current-limiting resistor, 47ohm (common spec, "
                                            "all puzzle modules).",
                            ref_at=(STATUS_R_POS[0] + 3.81, STATUS_R_POS[1] - 1.27, 0),
                            val_at=(STATUS_R_POS[0] + 3.81, STATUS_R_POS[1] + 1.27, 0)))
lines.append(placed_symbol("Device:LED", "D5", "LED status green OSG58A3131A", "LED_THT:LED_D3.0mm",
                            STATUS_LED_POS, [1, 2],
                            "Module status LED, green = solved (manual p.4). Panel position (60,6) absolute "
                            "(centre-relative +20,-34) -- see four_button_coordinate_proposal.md sec.3.",
                            ref_at=(STATUS_LED_POS[0], STATUS_LED_POS[1] + 3.81, 0),
                            val_at=(STATUS_LED_POS[0], STATUS_LED_POS[1] + 6.35, 0)))

lines.append(placed_symbol("Switch:SW_SPST", "SW9", "Mode select", "FourButton_Local:SW_Slide_2P",
                            MODE_SW_POS, [1, 2],
                            "Hardware mode-select switch (2-position slide/toggle, proposal per hub discussion "
                            "2026-10-01): GP11 internal pull-up, GND = one mode (e.g. diamond/Simon), open = the "
                            "other (grid/Keypad). Lets one firmware image serve both modes; final adoption is a "
                            "software-team decision (re-flashing per mode is the hardware-free alternative).",
                            ref_at=(MODE_SW_POS[0], MODE_SW_POS[1] - 5.08, 0),
                            val_at=(MODE_SW_POS[0], MODE_SW_POS[1] + 5.08, 0)))

lines.append(placed_symbol("Device:C_Polarized", "C1", "100uF/16V", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
                            C1_POS, [1, 2],
                            "Bulk capacitor on the 5V input (JST Pin3-Pin4), hub common rule 2026-09-27: "
                            "100uF/16V or larger electrolytic, one per module. Pin1(+)=+5V, pin2(-)=GND.",
                            ref_at=(C1_POS[0] - 5.08, C1_POS[1] - 1.27, 0), val_at=(C1_POS[0] - 5.08, C1_POS[1] + 1.27, 0)))

# ===========================================================================
# 6) 電源(PWR_FLAG)
# ===========================================================================
pwr_counter = [0]
def next_pwr_ref():
    pwr_counter[0] += 1
    return f"#PWR{pwr_counter[0]:02d}"

flg_counter = [0]
def next_flg_ref():
    flg_counter[0] += 1
    return f"#FLG{flg_counter[0]:02d}"

def add_power_flag(lib_id, target_xy, angle, offset, hide_value=False):
    flag_xy = (round(target_xy[0] + offset[0], 4), round(target_xy[1] + offset[1], 4))
    ref = next_pwr_ref()
    lines.append(power_symbol_block(lib_id, flag_xy, angle, ref, hide_value=hide_value))
    lines.append(wire_block(target_xy, flag_xy))
    net = lib_id.split(":")[1]
    ALL_SEGMENTS.append((target_xy, flag_xy, net))

LEFT_COL_OFFSET = (-2.54, 0.0)
for pin in (3, 8, 13, 18):
    add_power_flag("power:GND", pico_abs(pin), 180, LEFT_COL_OFFSET, hide_value=True)

RIGHT_COL_OFFSET = (2.54, 0.0)
for pin in (23, 28, 33, 38):
    add_power_flag("power:GND", pico_abs(pin), 0, RIGHT_COL_OFFSET, hide_value=True)
add_power_flag("power:+3.3V", pico_abs(36), 0, RIGHT_COL_OFFSET)
add_power_flag("power:+5V", pico_abs(39), 0, RIGHT_COL_OFFSET)

# +3.3V用の追加PWR_FLAG(button/gen_button_sch.pyと同じ手法: +3.3Vシンボルの位置からさらに枝を伸ばす)
v33_sym = (round(pico_abs(36)[0] + 2.54, 4), pico_abs(36)[1])
flag33 = (round(v33_sym[0] + 2.54, 4), v33_sym[1])
wire(v33_sym, flag33, "+3.3V")
lines.append(power_symbol_block("power:PWR_FLAG", flag33, 0, next_flg_ref(), desc="Special symbol for telling ERC where power comes from", hide_value=True))

c1_plus = abs_pt(C1_POS[:2], (0.0, 3.81))
c1_minus = abs_pt(C1_POS[:2], (0.0, -3.81))
j1_p3 = abs_pt(J1_POS[:2], CONN01X04_PINS[3])
j1_p4 = abs_pt(J1_POS[:2], CONN01X04_PINS[4])

wire(j1_p3, c1_plus, "+5V")
v5_sym = (round(c1_plus[0] - 2.54, 4), c1_plus[1])
wire(c1_plus, v5_sym, "+5V")
lines.append(power_symbol_block("power:+5V", v5_sym, 90, next_pwr_ref()))
flag5 = (c1_plus[0], round(c1_plus[1] - 2.54, 4))
wire(c1_plus, flag5, "+5V")
lines.append(power_symbol_block("power:PWR_FLAG", flag5, 0, next_flg_ref(), desc="Special symbol for telling ERC where power comes from", hide_value=True))

bend_x = round(c1_plus[0] + 2.54, 4)
wire(j1_p4, (bend_x, j1_p4[1]), "GND")
wire((bend_x, j1_p4[1]), (bend_x, c1_minus[1]), "GND")
wire((bend_x, c1_minus[1]), c1_minus, "GND")
gnd_sym = (round(c1_minus[0] - 2.54, 4), c1_minus[1])
wire(c1_minus, gnd_sym, "GND")
lines.append(power_symbol_block("power:GND", gnd_sym, 270, next_pwr_ref()))
flagg = (c1_minus[0], round(c1_minus[1] + 2.54, 4))
wire(c1_minus, flagg, "GND")
lines.append(power_symbol_block("power:PWR_FLAG", flagg, 180, next_flg_ref(), desc="Special symbol for telling ERC where power comes from", hide_value=True))

# グリッドSW pin1(GND)
GRID_GND_OFFSET = (-5.08, 0.0)
for ref in GRID_SW:
    p1 = abs_pt(grid_place[ref][:2], SW_PINS[1])
    add_power_flag("power:GND", p1, 0, GRID_GND_OFFSET, hide_value=True)
    component_pins.append((f"{ref}.1flag", p1))

# ひし形SW pin1(GND)
for ref in DIAMOND_SW:
    p1 = abs_pt(diamond_place[ref][:2], SW_PINS[1])
    add_power_flag("power:GND", p1, 0, GRID_GND_OFFSET, hide_value=True)

# NeoPixel各LED(SK6812)のVDD/VSS、およびデコップリングコンデンサ両端 -> +5V/GND
# (D-C間は直接配線せず、net名だけで結合: 両者とも独立した電源シンボルを持つ。button/simon踏襲の方式。)
for ref, (label, dx, dy, btn_net, color, dref, cref) in DIAMOND_SW.items():
    g = chain_place[ref]
    vdd = abs_pt(g["d"][:2], WS_PINS[3])
    vss = abs_pt(g["d"][:2], WS_PINS[1])
    add_power_flag("power:+5V", vdd, 90, (0.0, -2.54))
    add_power_flag("power:GND", vss, 270, (0.0, 2.54), hide_value=True)
    if cref is not None:
        c_pin1 = abs_pt(g["c"][:2], R_PINS[1])
        c_pin2 = abs_pt(g["c"][:2], R_PINS[2])
        add_power_flag("power:+5V", c_pin1, 90, (0.0, 2.54))
        add_power_flag("power:GND", c_pin2, 270, (0.0, -2.54), hide_value=True)

# 状態LEDカソード -> GND
add_power_flag("power:GND", led_status_cathode, 270, (0.0, -2.54), hide_value=True)

# モード選択スイッチ pin1(GND)
add_power_flag("power:GND", mode_pin1, 0, GRID_GND_OFFSET, hide_value=True)

# no_connects
for pin in NC_PINS:
    lines.append(no_connect_block(pico_abs(pin)))

for name, xy, angle in LABELS:
    lines.append(label_block(name, xy, angle))

TITLES = [
    ("J1: host link (UART0 + 5V), bulk cap C1", (J1_PIN_X - 12.7, j1_place_y - 12.7)),
    ("Grid sockets SW1-4 (keypad mode, diagonal +-19mm)", (GRID_BLOCK_X0 - 5.08, GRID_BLOCK_Y0 - 12.7)),
    ("Diamond sockets SW5-8 (simon mode, axis 17mm)", (DIAMOND_BLOCK_X0 - 5.08, GRID_BLOCK_Y0 - 12.7)),
    ("NeoPixel chain (SK6812 x4, red/blue/green/yellow), GP6 via R10", (GRID_BLOCK_X0 - 5.08, CHAIN_Y0 - 12.7)),
    ("Status LED (GP10) / Mode select SW9 (GP11)", (STATUS_R_POS[0] - 12.7, STATUS_R_POS[1] - 15.24)),
]
for s_, xy in TITLES:
    lines.append(text_block(s_, xy, 1.905))

lines.append(f'{T}(sheet_instances')
lines.append(f'{T*2}(path "/"')
lines.append(f'{T*3}(page "1")')
lines.append(f'{T*2})')
lines.append(f'{T})')
lines.append(f'{T}(embedded_fonts no)')
lines.append(')')

# ===========================================================================
# 7) 事後検証(button/gen_button_sch.pyと同じ手法)
# ===========================================================================
def seg_overlap_1d(a0, a1, b0, b1):
    lo1, hi1 = min(a0, a1), max(a0, a1)
    lo2, hi2 = min(b0, b1), max(b0, b1)
    lo = max(lo1, lo2)
    hi = min(hi1, hi2)
    return hi - lo

problems = []
n = len(ALL_SEGMENTS)
for i in range(n):
    p1, p2, net1 = ALL_SEGMENTS[i]
    for j in range(i + 1, n):
        q1, q2, net2 = ALL_SEGMENTS[j]
        if net1 == net2:
            continue
        if p1[0] == p2[0] == q1[0] == q2[0]:
            ov = seg_overlap_1d(p1[1], p2[1], q1[1], q2[1])
            if ov > 0:
                problems.append(f"OVERLAP (vertical x={p1[0]}) {net1} vs {net2}: {p1}-{p2} / {q1}-{q2}")
        if p1[1] == p2[1] == q1[1] == q2[1]:
            ov = seg_overlap_1d(p1[0], p2[0], q1[0], q2[0])
            if ov > 0:
                problems.append(f"OVERLAP (horizontal y={p1[1]}) {net1} vs {net2}: {p1}-{p2} / {q1}-{q2}")
        pts_i = {p1, p2}
        pts_j = {q1, q2}
        shared = pts_i & pts_j
        if shared:
            problems.append(f"SHARED ENDPOINT {shared} between nets {net1} and {net2}")

if problems:
    print("=== SEGMENT OVERLAP PROBLEMS ===")
    for p in problems:
        print(p)
else:
    print(f"No segment overlaps/shorts found among {n} segments.")

EPS = 1e-6
def strictly_inside(pt, p1, p2):
    x, y = pt
    if abs(p1[0] - p2[0]) < EPS and abs(p1[0] - x) < EPS:
        return min(p1[1], p2[1]) + EPS < y < max(p1[1], p2[1]) - EPS
    if abs(p1[1] - p2[1]) < EPS and abs(p1[1] - y) < EPS:
        return min(p1[0], p2[0]) + EPS < x < max(p1[0], p2[0]) - EPS
    return False

pin_problems = []
for label, pt in component_pins:
    for (q1, q2, net) in ALL_SEGMENTS:
        if strictly_inside(pt, q1, q2):
            pin_problems.append(f"PIN {label} at {pt} lies on the interior of wire {q1}-{q2} (net {net})")
for i, (p1, p2, net1) in enumerate(ALL_SEGMENTS):
    for j, (q1, q2, net2) in enumerate(ALL_SEGMENTS):
        if i == j:
            continue
        for end in (p1, p2):
            if strictly_inside(end, q1, q2):
                pin_problems.append(f"WIRE END {end} of {net1} lies on the interior of wire {q1}-{q2} (net {net2})")
if pin_problems:
    print("=== PIN/WIRE-END ON WIRE INTERIOR ===")
    for pr in pin_problems:
        print(pr)
else:
    print(f"No pin or wire end lies on a wire interior ({len(component_pins)} component pins, {len(ALL_SEGMENTS)} wires).")

doc = "\n".join(lines) + "\n"

D = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(D, "FourButton_Local.pretty"), exist_ok=True)
SYM_OUT = os.path.join(D, "FourButton_Local.kicad_sym")
_blk_sock = LIB_SOCKET.replace('(symbol "FourButton_Local:Kailh_socket_MX"', '(symbol "Kailh_socket_MX"', 1)
with open(SYM_OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write('(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "gen_four_button_sch")\n\t(generator_version "10.0")\n')
    f.write(reindent(_blk_sock, 1) + "\n)\n")
with open(os.path.join(D, "sym-lib-table"), "w", encoding="utf-8", newline="\n") as f:
    f.write('(sym_lib_table\n\t(version 7)\n'
            '\t(lib (name "FourButton_Local") (type "KiCad") (uri "${KIPRJMOD}/FourButton_Local.kicad_sym") (options "") (descr "Four-button module local symbols"))\n'
            '\t(lib (name "OSC_Shared") (type "KiCad") (uri "${KIPRJMOD}/../shared_lib/OSC_Shared.kicad_sym") (options "") (descr "OSC2026 shared symbols"))\n'
            ')\n')
with open(os.path.join(D, "fp-lib-table"), "w", encoding="utf-8", newline="\n") as f:
    f.write('(fp_lib_table\n\t(version 7)\n'
            '\t(lib (name "FourButton_Local") (type "KiCad") (uri "${KIPRJMOD}/FourButton_Local.pretty") (options "") (descr "Four-button module local footprints"))\n'
            '\t(lib (name "OSC_Shared") (type "KiCad") (uri "${KIPRJMOD}/../shared_lib/OSC_Shared.pretty") (options "") (descr "OSC2026 shared footprints"))\n'
            ')\n')

OUT = os.path.join(D, "four_button.kicad_sch")
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(doc)
print("Wrote", OUT, len(doc), "bytes")
print("Root sheet uuid:", ROOT_UUID)
