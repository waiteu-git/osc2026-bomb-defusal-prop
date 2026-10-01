#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Button module: button.kicad_sch の生成スクリプト(2026-09-27作成、C案=単色LED+NPNローサイド駆動。2026-09-30: 面LED撤去、キートップ表示器=カラー液晶GC9A01のSPI 8ピンコネクタJ2)。
# password/simon の生成手法(password/gen_password_sch.py)を踏襲: 全部品angle=0固定、abs_pt()はY反転のみ
# (回転は考慮しない)、生成後に自動でワイヤー重なり・ピン/ワイヤー端の内部一致をチェックする。
# 実行: python gen_button_sch.py  → button.kicad_sch を上書きする。
# 生成後は必ず check_button_sch.py(ERC + ネットリストの機械照合)を実行すること。
import os
import uuid as uuidlib

def U():
    return str(uuidlib.uuid4())

T = "\t"
PROJECT = "button"
ROOT_UUID = "b7e4a1c2-6f3d-4a9e-9c1b-2d5f8a3e7c60"  # button.kicad_pro と一致させて固定

# ===========================================================================
# 1) Pico symbol / pin table (password/gen_password_sch.py と同一定義)
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
    41: (-2.54, -29.21),  42: (0.0, -29.21),   43: (2.54, -29.21),
}
PICO_NAMES = {
    1: "GPIO0", 2: "GPIO1", 3: "GND", 4: "GPIO2", 5: "GPIO3", 6: "GPIO4", 7: "GPIO5", 8: "GND",
    9: "GPIO6", 10: "GPIO7", 11: "GPIO8", 12: "GPIO9", 13: "GND", 14: "GPIO10", 15: "GPIO11",
    16: "GPIO12", 17: "GPIO13", 18: "GND", 19: "GPIO14", 20: "GPIO15", 21: "GPIO16", 22: "GPIO17",
    23: "GND", 24: "GPIO18", 25: "GPIO19", 26: "GPIO20", 27: "GPIO21", 28: "GND", 29: "GPIO22",
    30: "RUN", 31: "GPIO26_ADC0", 32: "GPIO27_ADC1", 33: "AGND", 34: "GPIO28_ADC2",
    35: "ADC_VREF", 36: "3V3", 37: "3V3_EN", 38: "GND", 39: "VSYS", 40: "VBUS",
    41: "SWCLK", 42: "GND", 43: "SWDIO",
}
GRID = 1.27
def G(n):
    return round(n * GRID, 4)

PICO_POS = (G(120), G(70))  # =(152.4, 88.9)。A3シートに全体を収めるため、長距離配線は使わず名前付きラベルで結ぶ。

def pico_abs(pin):
    lx, ly = PICO_PINS[pin]
    return (round(PICO_POS[0] + lx, 4), round(PICO_POS[1] - ly, 4))

CONN01X04_PINS = {1: (-5.08, 2.54), 2: (-5.08, 0.0), 3: (-5.08, -2.54), 4: (-5.08, -5.08)}
SW_PUSH_PINS = {1: (-5.08, 0.0), 2: (5.08, 0.0)}
LED_PINS = {1: (-3.81, 0.0), 2: (3.81, 0.0)}   # pin1=K(cathode), pin2=A(anode)
R_PINS = {1: (0.0, 3.81), 2: (0.0, -3.81)}
Q_PINS = {1: (2.54, -5.08), 2: (2.54, 5.08), 3: (-5.08, 0.0)}  # 1=E, 2=C, 3=B (Transistor_BJT:2SC1815)

def abs_pt(placement, local):
    return (round(placement[0] + local[0], 4), round(placement[1] - local[1], 4))

GND_PINS = [3, 8, 13, 18, 23, 28, 33, 38]
# 使用するPico物理ピン: 1,2(UART) 6(ボタン押下) 12,14,15,16(ストリップLED4ch) 20(状態LED)
# 22,24,25,26,27,29(キートップ表示器SPI0: GP17 CS, GP18 SCK, GP19 MOSI, GP20 DC, GP21 RST, GP22 BL)
USED_PINS = {1, 2, 6, 12, 20, 22, 24, 25, 26, 27, 29}   # 12=GP9(NeoPixelデータ)
NC_PINS = [p for p in range(1, 41) if p not in USED_PINS and p not in GND_PINS
           and p not in (36, 39)]  # 36=3V3, 39=VSYSはPWR_FLAGで処理(no_connectにしない)

# ===========================================================================
# 2) レイアウト定数(すべてG(n)=n*1.27で格子に厳密整列させる)
#    可読性のため、Picoの各ピンからは短い引き出し線+名前付きラベルで各ブロックへ結ぶ
#    (UARTのJ1だけは従来どおり直結)。ブロック: J1/C1(左上)、ストリップLED4ch(下)、
#    押下スイッチ(右下)、状態LED(左)、J2 表示器コネクタ(右上)。
# ===========================================================================
PICO_LEFT_X = PICO_POS[0] - 17.78   # GP0-15側の列(左列)
PICO_RIGHT_X = PICO_POS[0] + 17.78  # GP16以降の列(右列)
STUB = G(6)                         # 引き出し線の長さ(7.62mm)

J1_PIN_X = PICO_LEFT_X - G(30)      # UARTコネクタ(GP0/1)。直結
STATUS_ANCHOR_X = G(45)             # 状態LED用抵抗の列
CHANNEL_PITCH_X = G(38)             # =48.26mm。1ch分の幅(約36mm)より余裕を持たせる
CHANNEL_X0 = G(28)                  # ストリップLED4chの左端(ch0=白 ... ch3=黄、右へ並ぶ)
CHANNEL_ROW_Y = G(135)              # ストリップLEDチャンネルの基準行(Pico下端より十分下)
SW_X = G(250)                       # 押下スイッチSW1の列(右下)
SW_Y0 = G(105)
STATUS_R_X = STATUS_ANCHOR_X

# ピン名→ラベル(左列: GP0-15側 / 右列: GP16以降側)
LEFT_STUBS = {6: "BTN", 12: "NEO_DIN", 20: "STATUS_LED"}
RIGHT_STUBS = {22: "LCD_CS", 24: "LCD_CLK", 25: "LCD_DIN", 26: "LCD_DC", 27: "LCD_RST", 29: "LCD_BL"}

tx_abs = pico_abs(1)
rx_abs = pico_abs(2)
j1_place_y = round(tx_abs[1] + CONN01X04_PINS[1][1], 4)
j1_place_x = round(J1_PIN_X + 5.08, 4)
J1_POS = (j1_place_x, j1_place_y, 0)

# --- J2: キートップ表示器(Waveshare 1.28インチ丸型 GC9A01)の8ピンSPIコネクタ ---------
J2_PIN_X = G(200)
J2_Y0 = G(45)
J2_PINS8 = {i: (-5.08, round(7.62 - 2.54 * (i - 1), 4)) for i in range(1, 9)}
J2_POS = (round(J2_PIN_X + 5.08, 4), round(J2_Y0 + 7.62, 4), 0)   # pin1が(J2_PIN_X, J2_Y0)に来る
# 信号: J2ピン番号 -> (Pico物理ピン, GPIO名, ネット名)。ピン順はWaveshare付属ケーブル(VCC,GND,DIN,CLK,CS,DC,RST,BL)
LCD_SIGNALS = {
    3: (25, "GP19", "LCD_DIN"),   # MOSI
    4: (24, "GP18", "LCD_CLK"),   # SCK
    5: (22, "GP17", "LCD_CS"),
    6: (26, "GP20", "LCD_DC"),
    7: (27, "GP21", "LCD_RST"),
    8: (29, "GP22", "LCD_BL"),
}

# --- ボタン押下スイッチ(SW1、GP4に並列。各スイッチのpin2から同名ラベル"BTN"で結ぶ) ----
SW_REFS = ["SW1"]
sw_defs = {ref: dict(place=(SW_X, round(SW_Y0 + G(10) * i, 4), 0)) for i, ref in enumerate(SW_REFS)}

# --- ストリップLEDチャンネル(4ch: White/Blue/Red/Yellow) --
# 2026-09-30: 面LED4色は、キートップにカラー液晶(GC9A01)を載せて色と文言を液晶に任せるため撤去した。
# 2026-09-30: 側面ストリップはNeoPixel(WS2812系)に変更。単色LED4ch+NPN(Q1-4/RB/R)は撤去。
CHANNELS = []
RBASE_REFS = ["RB1", "RB2", "RB3", "RB4"]
STRIP_LABELS = {12: "STRIP_W", 14: "STRIP_B", 15: "STRIP_R", 16: "STRIP_Y"}

# --- NeoPixel: GP9 -> R10(330) -> NP1.DIN、NP1.DOUT -> NP2.DIN ... (WS2812B 5050 x6、縦に約4cm分。2026-10-01、J3は廃止) ---
NEO_X = CHANNEL_X0
NP_REFS = [f"NP{i}" for i in range(1, 7)]
NP_PINS = {1: (0.0, 7.62), 2: (7.62, 0.0), 3: (0.0, -7.62), 4: (-7.62, 0.0)}   # 1=VDD(上) 2=DOUT(右) 3=VSS(下) 4=DIN(左)
NP_PITCH = G(16)
R10_POS = (NEO_X, CHANNEL_ROW_Y + R_PINS[1][1], 0)
r10_pin1 = abs_pt(R10_POS[:2], R_PINS[1])
r10_pin2 = abs_pt(R10_POS[:2], R_PINS[2])
r10_label_pt = (NEO_X, round(CHANNEL_ROW_Y - G(4), 4))
NP_X0 = round(NEO_X + G(8) + 7.62, 4)       # NP1のDINがR10のpin2から右へ10.16mmの位置に来る
NP_POS = {ref: (round(NP_X0 + i * NP_PITCH, 4), r10_pin2[1], 0) for i, ref in enumerate(NP_REFS)}

ch_geo = {}
for k, (qref, rref, lref, gpio_name, pin, color, part, rval, desc) in enumerate(CHANNELS):
    cx = CHANNEL_X0 + k * CHANNEL_PITCH_X
    # R_base: pin1のYがCHANNEL_ROW_Yに一致するよう配置(上へ短い枝を出してラベルSTRIP_*につなぐ)
    rb_place = (cx, CHANNEL_ROW_Y + R_PINS[1][1], 0)
    rb_pin1 = abs_pt(rb_place[:2], R_PINS[1])   # = (cx, CHANNEL_ROW_Y)
    rb_pin2 = abs_pt(rb_place[:2], R_PINS[2])   # = (cx, CHANNEL_ROW_Y + 7.62)
    rb_label_pt = (cx, round(CHANNEL_ROW_Y - G(4), 4))
    # Q: baseのYがrb_pin2のYに一致
    q_x = cx + 10.16
    q_place = (q_x, rb_pin2[1], 0)
    q_base = abs_pt(q_place[:2], Q_PINS[3])
    q_coll = abs_pt(q_place[:2], Q_PINS[2])
    q_emit = abs_pt(q_place[:2], Q_PINS[1])
    # LED: KのYがq_collのYに一致(cathode = collector側)
    led_x = q_x + G(11)
    led_place = (led_x, q_coll[1], 0)
    led_k = abs_pt(led_place[:2], LED_PINS[1])
    led_a = abs_pt(led_place[:2], LED_PINS[2])
    # R_led: pin1のYがled_aのYに一致(anode側、+5Vへ)
    rled_x = led_x + G(9)
    rled_place = (rled_x, led_a[1] + R_PINS[1][1], 0)
    rled_pin1 = abs_pt(rled_place[:2], R_PINS[1])
    rled_pin2 = abs_pt(rled_place[:2], R_PINS[2])
    ch_geo[k] = dict(
        qref=qref, rref=rref, lref=lref, gpio_name=gpio_name, pin=pin, color=color, part=part,
        rval=rval, desc=desc, cx=cx, gpio_abs=pico_abs(pin),
        rb_place=rb_place, rb_pin1=rb_pin1, rb_pin2=rb_pin2, rb_label_pt=rb_label_pt,
        q_place=q_place, q_base=q_base, q_coll=q_coll, q_emit=q_emit,
        led_place=led_place, led_k=led_k, led_a=led_a,
        rled_place=rled_place, rled_pin1=rled_pin1, rled_pin2=rled_pin2,
    )

# --- 状態LED(緑、GP15): R9のpin1から上へ枝を出し、ラベルSTATUS_LEDでPicoへ結ぶ ---------
STATUS_R_Y1 = G(80)
RSTATUS_POS = (STATUS_R_X, round(STATUS_R_Y1 + R_PINS[1][1], 4), 0)
rstatus_pin1 = abs_pt(RSTATUS_POS[:2], R_PINS[1])
rstatus_pin2 = abs_pt(RSTATUS_POS[:2], R_PINS[2])
rstatus_label_pt = (rstatus_pin1[0], round(rstatus_pin1[1] - G(4), 4))
led_status_target = (rstatus_pin2[0], round(rstatus_pin2[1] + 2.54, 4))
led_status_place_x = round(led_status_target[0] - LED_PINS[2][0], 4)
LEDSTATUS_POS = (led_status_place_x, led_status_target[1], 0)
led_status_anode = abs_pt(LEDSTATUS_POS[:2], LED_PINS[2])
led_status_cathode = abs_pt(LEDSTATUS_POS[:2], LED_PINS[1])

# ===========================================================================
# 3) lib_symbols(password.kicad_sch / simon.kicad_sch から検証済みブロックを転用)
# ===========================================================================
LIB_CONN01X04 = r'''(symbol "Connector_Generic:Conn_01x04"
	(pin_names
		(offset 1.016)
		(hide yes)
	)
	(exclude_from_sim no)
	(in_bom yes)
	(on_board yes)
	(in_pos_files yes)
	(duplicate_pin_numbers_are_jumpers no)
	(property "Reference" "J"
		(at 0 5.08 0)
		(show_name no)
		(do_not_autoplace no)
		(effects (font (size 1.27 1.27)))
	)
	(property "Value" "Conn_01x04"
		(at 0 -7.62 0)
		(show_name no)
		(do_not_autoplace no)
		(effects (font (size 1.27 1.27)))
	)
	(property "Footprint" ""
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)))
	)
	(property "Datasheet" ""
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)))
	)
	(property "Description" "Generic connector, single row, 01x04, script generated (kicad-library-utils/schlib/autogen/connector/)"
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)))
	)
	(property "ki_keywords" "connector"
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)))
	)
	(property "ki_fp_filters" "Connector*:*_1x??_*"
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)))
	)
	(symbol "Conn_01x04_1_1"
		(rectangle (start -1.27 3.81) (end 1.27 -6.35)
			(stroke (width 0.254) (type default)) (fill (type background)))
		(rectangle (start -1.27 2.667) (end 0 2.413)
			(stroke (width 0.1524) (type default)) (fill (type none)))
		(rectangle (start -1.27 0.127) (end 0 -0.127)
			(stroke (width 0.1524) (type default)) (fill (type none)))
		(rectangle (start -1.27 -2.413) (end 0 -2.667)
			(stroke (width 0.1524) (type default)) (fill (type none)))
		(rectangle (start -1.27 -4.953) (end 0 -5.207)
			(stroke (width 0.1524) (type default)) (fill (type none)))
		(pin passive line (at -5.08 2.54 0) (length 3.81)
			(name "Pin_1" (effects (font (size 1.27 1.27))))
			(number "1" (effects (font (size 1.27 1.27))))
		)
		(pin passive line (at -5.08 0 0) (length 3.81)
			(name "Pin_2" (effects (font (size 1.27 1.27))))
			(number "2" (effects (font (size 1.27 1.27))))
		)
		(pin passive line (at -5.08 -2.54 0) (length 3.81)
			(name "Pin_3" (effects (font (size 1.27 1.27))))
			(number "3" (effects (font (size 1.27 1.27))))
		)
		(pin passive line (at -5.08 -5.08 0) (length 3.81)
			(name "Pin_4" (effects (font (size 1.27 1.27))))
			(number "4" (effects (font (size 1.27 1.27))))
		)
	)
	(embedded_fonts no)
)'''

LIB_LED = r'''(symbol "Device:LED"
	(pin_numbers (hide yes))
	(pin_names (offset 1.016) (hide yes))
	(exclude_from_sim no)
	(in_bom yes)
	(on_board yes)
	(in_pos_files yes)
	(duplicate_pin_numbers_are_jumpers no)
	(property "Reference" "D" (at 0 2.54 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
	(property "Value" "LED" (at 0 -2.54 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
	(property "Footprint" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Datasheet" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Description" "Light emitting diode" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Sim.Pins" "1=K 2=A" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "ki_keywords" "LED diode" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "ki_fp_filters" "LED* LED_SMD:* LED_THT:*" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(symbol "LED_0_1"
		(polyline (pts (xy -3.048 -0.762) (xy -4.572 -2.286) (xy -3.81 -2.286) (xy -4.572 -2.286) (xy -4.572 -1.524)) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy -1.778 -0.762) (xy -3.302 -2.286) (xy -2.54 -2.286) (xy -3.302 -2.286) (xy -3.302 -1.524)) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy -1.27 0) (xy 1.27 0)) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy -1.27 -1.27) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
		(polyline (pts (xy 1.27 -1.27) (xy 1.27 1.27) (xy -1.27 0) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
	)
	(symbol "LED_1_1"
		(pin passive line (at -3.81 0 0) (length 2.54) (name "K" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
		(pin passive line (at 3.81 0 180) (length 2.54) (name "A" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
	)
	(embedded_fonts no)
)'''

LIB_R = r'''(symbol "Device:R"
	(pin_numbers (hide yes))
	(pin_names (offset 0))
	(exclude_from_sim no)
	(in_bom yes)
	(on_board yes)
	(in_pos_files yes)
	(duplicate_pin_numbers_are_jumpers no)
	(property "Reference" "R" (at 2.032 0 90) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
	(property "Value" "R" (at 0 0 90) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
	(property "Footprint" "" (at -1.778 0 90) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Datasheet" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Description" "Resistor" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "ki_keywords" "R res resistor" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "ki_fp_filters" "R_*" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(symbol "R_0_1"
		(rectangle (start -1.016 -2.54) (end 1.016 2.54) (stroke (width 0.254) (type default)) (fill (type none)))
	)
	(symbol "R_1_1"
		(pin passive line (at 0 3.81 270) (length 1.27) (name "" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
		(pin passive line (at 0 -3.81 90) (length 1.27) (name "" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
	)
	(embedded_fonts no)
)'''

LIB_SW = r'''(symbol "Switch:SW_Push"
	(pin_numbers (hide yes))
	(pin_names (offset 1.016) (hide yes))
	(exclude_from_sim no)
	(in_bom yes)
	(on_board yes)
	(in_pos_files yes)
	(duplicate_pin_numbers_are_jumpers no)
	(property "Reference" "SW" (at 1.27 2.54 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27)) (justify left)))
	(property "Value" "SW_Push" (at 0 -1.524 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
	(property "Footprint" "" (at 0 5.08 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Datasheet" "" (at 0 5.08 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Description" "Push button switch, generic, two pins" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "ki_keywords" "switch normally-open pushbutton push-button" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(symbol "SW_Push_0_1"
		(circle (center -2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 0 1.27) (xy 0 3.048)) (stroke (width 0) (type default)) (fill (type none)))
		(circle (center 2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 2.54 1.27) (xy -2.54 1.27)) (stroke (width 0) (type default)) (fill (type none)))
		(pin passive line (at -5.08 0 0) (length 2.54) (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
		(pin passive line (at 5.08 0 180) (length 2.54) (name "2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
	)
	(embedded_fonts no)
)'''

LIB_2SC1815 = r'''(symbol "Button_Local:2SC1815"
	(pin_names
		(offset 0)
		(hide yes)
	)
	(exclude_from_sim no)
	(in_bom yes)
	(on_board yes)
	(in_pos_files yes)
	(duplicate_pin_numbers_are_jumpers no)
	(property "Reference" "Q"
		(at 5.08 1.905 0)
		(show_name no)
		(do_not_autoplace no)
		(effects (font (size 1.27 1.27)) (justify left))
	)
	(property "Value" "2SC1815"
		(at 5.08 0 0)
		(show_name no)
		(do_not_autoplace no)
		(effects (font (size 1.27 1.27)) (justify left))
	)
	(property "Footprint" "Button_Local:TO-92_Inline_D065"
		(at 5.08 -1.905 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27) (italic yes)) (justify left))
	)
	(property "Datasheet" "https://media.digikey.com/pdf/Data%20Sheets/Toshiba%20PDFs/2SC1815.pdf"
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)) (justify left))
	)
	(property "Description" "0.15A Ic, 50V Vce, Low Noise Audio NPN Transistor, TO-92"
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)))
	)
	(property "Sim.Device" "NPN"
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)))
	)
	(property "Sim.Pins" "1=E 2=C 3=B"
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)))
	)
	(property "ki_keywords" "Low Noise Audio NPN Transistor"
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)))
	)
	(property "ki_fp_filters" "TO?92*"
		(at 0 0 0)
		(show_name no)
		(do_not_autoplace no)
		(hide yes)
		(effects (font (size 1.27 1.27)))
	)
	(symbol "2SC1815_0_1"
		(polyline (pts (xy -2.54 0) (xy 0.635 0)) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 0.635 1.905) (xy 0.635 -1.905)) (stroke (width 0.508) (type default)) (fill (type none)))
		(circle (center 1.27 0) (radius 2.8194) (stroke (width 0.254) (type default)) (fill (type none)))
	)
	(symbol "2SC1815_1_1"
		(polyline (pts (xy 0.635 0.635) (xy 2.54 2.54)) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 0.635 -0.635) (xy 2.54 -2.54)) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 1.27 -1.778) (xy 1.778 -1.27) (xy 2.286 -2.286) (xy 1.27 -1.778)) (stroke (width 0) (type default)) (fill (type outline)))
		(pin passive line (at 2.54 -5.08 90) (length 2.54)
			(name "E" (effects (font (size 1.27 1.27))))
			(number "1" (effects (font (size 1.27 1.27))))
		)
		(pin passive line (at 2.54 5.08 270) (length 2.54)
			(name "C" (effects (font (size 1.27 1.27))))
			(number "2" (effects (font (size 1.27 1.27))))
		)
		(pin input line (at -5.08 0 0) (length 2.54)
			(name "B" (effects (font (size 1.27 1.27))))
			(number "3" (effects (font (size 1.27 1.27))))
		)
	)
	(embedded_fonts no)
)'''

LIB_GND = r'''(symbol "power:GND"
	(power global)
	(pin_numbers (hide yes))
	(pin_names (offset 0) (hide yes))
	(exclude_from_sim no)
	(in_bom yes)
	(on_board yes)
	(in_pos_files yes)
	(duplicate_pin_numbers_are_jumpers no)
	(property "Reference" "#PWR" (at 0 -6.35 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Value" "GND" (at 0 -3.81 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
	(property "Footprint" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Datasheet" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Description" "Power symbol creates a global label with name \"GND\" , ground" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "ki_keywords" "global power" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(symbol "GND_0_1"
		(polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27)) (stroke (width 0) (type default)) (fill (type none)))
	)
	(symbol "GND_1_1"
		(pin power_in line (at 0 0 270) (length 0) (name "" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
	)
	(embedded_fonts no)
)'''

LIB_3V3 = r'''(symbol "power:+3.3V"
	(power global)
	(pin_numbers (hide yes))
	(pin_names (offset 0) (hide yes))
	(exclude_from_sim no)
	(in_bom yes)
	(on_board yes)
	(in_pos_files yes)
	(duplicate_pin_numbers_are_jumpers no)
	(property "Reference" "#PWR" (at 0 -3.81 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Value" "+3.3V" (at 0 3.556 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
	(property "Footprint" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Datasheet" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Description" "Power symbol creates a global label with name \"+3.3V\"" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "ki_keywords" "global power" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(symbol "+3.3V_0_1"
		(polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
	)
	(symbol "+3.3V_1_1"
		(pin power_in line (at 0 0 90) (length 0) (name "" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
	)
	(embedded_fonts no)
)'''

LIB_5V = r'''(symbol "power:+5V"
	(power global)
	(pin_numbers (hide yes))
	(pin_names (offset 0) (hide yes))
	(exclude_from_sim no)
	(in_bom yes)
	(on_board yes)
	(in_pos_files yes)
	(duplicate_pin_numbers_are_jumpers no)
	(property "Reference" "#PWR" (at 0 -3.81 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Value" "+5V" (at 0 3.556 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))
	(property "Footprint" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Datasheet" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "Description" "Power symbol creates a global label with name \"+5V\"" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(property "ki_keywords" "global power" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
	(symbol "+5V_0_1"
		(polyline (pts (xy -0.762 1.27) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 0 2.54) (xy 0.762 1.27)) (stroke (width 0) (type default)) (fill (type none)))
		(polyline (pts (xy 0 0) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none)))
	)
	(symbol "+5V_1_1"
		(pin power_in line (at 0 0 90) (length 0) (name "" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
	)
	(embedded_fonts no)
)'''

PICO_PIN_TYPE = {}
for p in range(1, 44):
    PICO_PIN_TYPE[p] = "bidirectional"
for p in GND_PINS:
    PICO_PIN_TYPE[p] = "power_in"
PICO_PIN_TYPE[30] = "input"
PICO_PIN_TYPE[35] = "power_in"
PICO_PIN_TYPE[36] = "power_in"
PICO_PIN_TYPE[37] = "input"
PICO_PIN_TYPE[39] = "power_in"
PICO_PIN_TYPE[40] = "power_in"
PICO_PIN_TYPE[41] = "input"
PICO_PIN_TYPE[43] = "bidirectional"

def pico_pin_angle(pin):
    lx, ly = PICO_PINS[pin]
    if pin in (41, 42, 43):
        return 90
    return 0 if lx < 0 else 180

pico_pin_lines = []
for p in range(1, 44):
    lx, ly = PICO_PINS[p]
    angle = pico_pin_angle(p)
    ptype = PICO_PIN_TYPE[p]
    name = PICO_NAMES[p]
    pico_pin_lines.append(
        f'\t\t(pin {ptype} line (at {lx:g} {ly:g} {angle}) (length 2.54)\n'
        f'\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))\n'
        f'\t\t\t(number "{p}" (effects (font (size 1.27 1.27))))\n'
        f'\t\t)'
    )

LIB_PICO = (
    '(symbol "RPi_Pico:Pico"\n'
    '\t(exclude_from_sim no)\n\t(in_bom yes)\n\t(on_board yes)\n\t(in_pos_files yes)\n'
    '\t(duplicate_pin_numbers_are_jumpers no)\n'
    '\t(property "Reference" "U" (at -13.97 27.94 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))\n'
    '\t(property "Value" "Pico" (at 0 19.05 0) (show_name no) (do_not_autoplace no) (effects (font (size 1.27 1.27))))\n'
    '\t(property "Footprint" "RPi_Pico:RPi_Pico_SMD_TH" (at 0 0 90) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))\n'
    '\t(property "Datasheet" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))\n'
    '\t(property "Description" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))\n'
    '\t(symbol "Pico_0_0"\n'
    '\t\t(text "Raspberry Pi Pico" (at 0 21.59 0) (effects (font (size 1.27 1.27))))\n'
    '\t)\n'
    '\t(symbol "Pico_0_1"\n'
    '\t\t(rectangle (start -15.24 26.67) (end 15.24 -26.67) (stroke (width 0) (type default)) (fill (type background)))\n'
    '\t)\n'
    '\t(symbol "Pico_1_1"\n'
    + "\n".join(pico_pin_lines) + '\n'
    '\t)\n'
    '\t(embedded_fonts no)\n'
    ')'
)

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

LIB_PWRFLAG = _extract_stock(KICAD_SYM + "power.kicad_sym", "PWR_FLAG", "power:PWR_FLAG")
LIB_CP = _extract_stock(KICAD_SYM + "Device.kicad_sym", "C_Polarized", "Device:C_Polarized")
LIB_CONN01X08 = _extract_stock(KICAD_SYM + "Connector_Generic.kicad_sym", "Conn_01x08", "Connector_Generic:Conn_01x08")
LIB_CONN01X03 = _extract_stock(KICAD_SYM + "Connector_Generic.kicad_sym", "Conn_01x03", "Connector_Generic:Conn_01x03")
LIB_PICO = _extract_stock("C:/Users/ysou5/OneDrive - 東京理科大学/ドキュメント/osc/hardware/shared_lib/OSC_Shared.kicad_sym", "Pico_TH40", "OSC_Shared:Pico_TH40")
LIB_WS2812B = _extract_stock(KICAD_SYM + "LED.kicad_sym", "WS2812B", "LED:WS2812B")
LIB_SYMBOLS_ALL = [LIB_CONN01X04, LIB_WS2812B, LIB_CONN01X08, LIB_LED, LIB_R, LIB_PICO, LIB_SW, LIB_2SC1815,
                   LIB_GND, LIB_3V3, LIB_5V, LIB_PWRFLAG, LIB_CP]

def reindent(block, base_tabs):
    lines = block.split("\n")
    out = []
    for ln in lines:
        out.append((T * base_tabs) + ln if ln.strip() else ln)
    return "\n".join(out)

# ===========================================================================
# 4) placed-symbol / wire / no_connect emitters(password/gen_password_sch.pyと同一)
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

def text_block(s, at_xy, size=2.54):
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
lines.append(f'{T*2}(title "Button module")')
lines.append(f'{T*2}(comment 1 "OSC2026 Button module (colour LCD keytop)")')
lines.append(f'{T})')
lines.append(f'{T}(lib_symbols')
for blk in LIB_SYMBOLS_ALL:
    lines.append(reindent(blk, 2))
lines.append(f'{T})')

ALL_SEGMENTS = []

def wire(p1, p2, net):
    lines.append(wire_block(p1, p2))
    ALL_SEGMENTS.append((p1, p2, net))

# --- 名前付きラベルで結ぶ引き出し線 ---------------------------------------------
LABELS = []   # (name, xy, angle)

def stub(p_from, p_to, net, angle):
    wire(p_from, p_to, net)
    LABELS.append((net, p_to, angle))

# --- UART(J1): Picoへ直結 ------------------------------------------------------
wire(abs_pt(J1_POS[:2], CONN01X04_PINS[1]), tx_abs, "UART0_TX")
wire(abs_pt(J1_POS[:2], CONN01X04_PINS[2]), rx_abs, "UART0_RX")

# --- Picoの左列: 押下検出・ストリップLED・状態LED -------------------------------------
for pin, net in LEFT_STUBS.items():
    p = pico_abs(pin)
    stub(p, (round(PICO_LEFT_X - STUB, 4), p[1]), net, 180)
# --- Picoの右列: 表示器SPI -----------------------------------------------------------
for pin, net in RIGHT_STUBS.items():
    p = pico_abs(pin)
    stub(p, (round(PICO_RIGHT_X + STUB, 4), p[1]), net, 0)
# --- J2: 表示器コネクタの信号ピン3〜8 ---------------------------------------------------
for pin_j, (pico_pin, gp_name, net) in LCD_SIGNALS.items():
    p_j2 = abs_pt(J2_POS[:2], J2_PINS8[pin_j])
    stub(p_j2, (round(p_j2[0] - STUB, 4), p_j2[1]), net, 180)

# --- ボタン押下スイッチ(SW1): pin2から右へ短い枝を出し、ラベルBTNで結ぶ --------------------
sw_pin2 = {ref: abs_pt(sw_defs[ref]["place"][:2], SW_PUSH_PINS[2]) for ref in SW_REFS}
for ref in SW_REFS:
    p = sw_pin2[ref]
    stub(p, (round(p[0] + G(4), 4), p[1]), "BTN", 0)

# --- ストリップLED 4色チャンネル -------------------------------------------------
stub(r10_pin1, r10_label_pt, "NEO_DIN", 0)
wire(r10_pin2, abs_pt(NP_POS["NP1"][:2], NP_PINS[4]), "NEO_DIN_R")
for i in range(len(NP_REFS) - 1):
    wire(abs_pt(NP_POS[NP_REFS[i]][:2], NP_PINS[2]), abs_pt(NP_POS[NP_REFS[i + 1]][:2], NP_PINS[4]), f"NEO_CHAIN{i + 1}")
for k, g in ch_geo.items():
    net_label = STRIP_LABELS[g["pin"]]
    stub(g["rb_pin1"], g["rb_label_pt"], net_label, 0)
    wire(g["rb_pin2"], g["q_base"], f"BASE{k+1}")
    wire(g["q_coll"], g["led_k"], f"COLL{k+1}")
    wire(g["led_a"], g["rled_pin1"], f"ANODE{k+1}")

# --- 状態LED(緑) -------------------------------------------------------------
stub(rstatus_pin1, rstatus_label_pt, "STATUS_LED", 0)
wire(rstatus_pin2, led_status_anode, "STATUS_LED_ANODE")

# --- 部品配置: Pico -----------------------------------------------------------
lines.append(placed_symbol("OSC_Shared:Pico_TH40", "U1", "Pico 2 H", "OSC_Shared:RPi_Pico_TH_Headers",
                            (PICO_POS[0], PICO_POS[1], 0), list(range(1, 41)),
                            "Button module MCU (Raspberry Pi Pico 2 H on 2.54mm headers, floating ~2.5mm; 40 header pins only, hub decision 2026-09-30)."))

# --- J1(UART) -----------------------------------------------------------------
lines.append(placed_symbol("Connector_Generic:Conn_01x04", "J1", "MODULE_JST_XH_4P",
                            "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", J1_POS, [1, 2, 3, 4],
                            "Host connector, JST XH 4-pole. Pin1=GPIO0(UART0 TX, module->host), "
                            "Pin2=GPIO1(UART0 RX, host->module), Pin3=VCC(5V, from host per-slot polyfuse "
                            "MF-RX030/72-0 0.3A hold), Pin4=GND. Common to all puzzle modules (see ハブ連絡事項.md).",
                            ref_at=(J1_POS[0], J1_POS[1] - 8.89, 0), val_at=(J1_POS[0], J1_POS[1] - 6.35, 0)))

# --- J2(キートップ表示器: Waveshare 1.28インチ丸型 GC9A01 の8ピンSPI) -----------
lines.append(placed_symbol("Connector_Generic:Conn_01x08", "J2", "KEYTOP_LCD_SPI",
                            "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical", J2_POS, list(range(1, 9)),
                            "Connector to the keytop color LCD (Waveshare 1.28in round GC9A01, Akizuki 118048, "
                            "8-pin PH2.0 cable included; the far end of that cable is NOT verified -- if it is PH2.0 8P, swap this "
                            "footprint/part for JST B8B-PH-K-S (Akizuki 112808, 15 yen); a 2.54mm 1x8 header is the default for "
                            "Dupont-style ends). Pin order follows the Waveshare pin list (to be "
                            "verified against the cable in hand): Pin1=VCC(+3.3V), Pin2=GND, Pin3=DIN(MOSI, "
                            "GP19), Pin4=CLK(SCK, GP18), Pin5=CS(GP17), Pin6=DC(GP20), Pin7=RST(GP21), "
                            "Pin8=BL(GP22, backlight; PWM-dimmable). Pico SPI0 (GP16-19). The keytop mechanism "
                            "and display mounting are designed by the user; this board only provides the "
                            "connector (2026-09-30).",
                            ref_at=(J2_POS[0], J2_POS[1] + 15.24, 0), val_at=(J2_POS[0], J2_POS[1] + 17.78, 0)))

# --- SW1(押下検出、ドーム縁4点を想定・全て並列) -------------------------------
for ref in SW_REFS:
    place = sw_defs[ref]["place"]
    lines.append(placed_symbol("Switch:SW_Push", ref, "SW_Push", "Button_Local:Kailh_socket_MX",
                                place, [1, 2],
                                f"Button press detection, one Kailh MX hot-swap socket under the keytop (2026-10-01; same switch/socket as the four_button module; MX-compatible switch plugs in; replaces the 12mm tact). "
                                f"Wired onto GP4. Pico physical pin 6 (GPIO4), "
                                f"internal pull-up, no external resistor. Pin1=GND side, Pin2=GPIO side.",
                                ref_at=(round(SW_X, 4), round(place[1] - 5.08, 4), 0), hide_value=True))

# --- NeoPixel: R10(データ直列抵抗)とJ3 ---------------------------------------------
lines.append(placed_symbol("Device:R", "R10", "330", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
                            R10_POS, [1, 2],
                            "Series resistor on the NeoPixel data line (GP9 -> NP1 DIN), 300-470ohm typical; damps "
                            "ringing on long leads. Value not yet verified against the actual pixel part.",
                            ref_at=(R10_POS[0] + 3.81, R10_POS[1] - 1.27, 0),
                            val_at=(R10_POS[0] + 3.81, R10_POS[1] + 1.27, 0)))
for ref in NP_REFS:
    pl = NP_POS[ref]
    lines.append(placed_symbol("LED:WS2812B", ref, "WS2812B", "LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm", pl, [1, 2, 3, 4],
                                "Side-strip NeoPixel pixel (WS2812B-compatible 5050; SK6812 has the same footprint but a different pinout, so "
                                "check the symbol before swapping). 6 pixels in a vertical line, about 42 mm. DIN of the first pixel "
                                "comes from GP9 via R10. No per-pixel bypass capacitor (user decision 2026-10-01; datasheet recommends 0.1uF each). "
                                "DIN high level >=0.7*VDD (3.5V) is marginal at 3.3V; verify on the real part. Cap brightness in firmware.",
                                ref_at=(pl[0], round(pl[1] - 1.27, 4), 0), hide_value=True))

# --- (旧)ストリップLED4chのチャンネル: 現在は空 ----------------------------- --------------------------------
for k, g in ch_geo.items():
    lines.append(placed_symbol("Device:R", RBASE_REFS[k], "4.7k",
                                "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
                                g["rb_place"], [1, 2],
                                f"Base resistor for {g['desc']} ({g['color']}), NPN low-side switch. "
                                f"Ib=(3.3-0.7)/4.7k=0.55mA, forced beta well under 2SC1815-GR min hFE(200). "
                                f"No separate base pulldown (RP2350-E9 affects A2 stepping only; firmware "
                                f"drives this pin output-low from boot, per ハブ連絡事項.md 2026-09-27).",
                                ref_at=(g["rb_place"][0] + 3.81, g["rb_place"][1] - 1.27, 0),
                                val_at=(g["rb_place"][0] + 3.81, g["rb_place"][1] + 1.27, 0)))
    lines.append(placed_symbol("Button_Local:2SC1815", g["qref"], "2SC1815",
                                "Button_Local:TO-92_Inline_D065", g["q_place"], [1, 2, 3],
                                f"Low-side switch for {g['desc']} ({g['color']}). Pinout ECB (flat face "
                                f"toward you). Base driven from Pico GPIO via 4.7k ({RBASE_REFS[k]}).",
                                ref_at=(g["q_place"][0] + 6.35, g["q_place"][1] - 3.81, 0),
                                val_at=(g["q_place"][0] + 6.35, g["q_place"][1] - 1.27, 0)))
    lines.append(placed_symbol("Device:LED", g["lref"], f"{g['part']} ({g['color']})", "LED_THT:LED_D10.0mm",
                                g["led_place"], [1, 2],
                                f"{g['desc']}: {g['part']}, {g['color']}, 10mm THT, max brightness target "
                                f"~18-20mA. Anode(right, pin2)->series resistor->+5V; cathode(left, pin1)"
                                f"->{g['qref']} collector.",
                                ref_at=(g["led_place"][0], g["led_place"][1] - 3.81, 0),
                                val_at=(g["led_place"][0], g["led_place"][1] - 6.35, 0)))
    lines.append(placed_symbol("Device:R", g["rref"], g["rval"],
                                "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
                                g["rled_place"], [1, 2],
                                f"Series current-limiting resistor for {g['lref']} ({g['color']}), "
                                f"targets ~18-20mA from +5V (I=(5-Vf-0.1)/R; trim by measurement, per "
                                f"button_design_notes.md sec.3-C).",
                                ref_at=(g["rled_place"][0] + 3.81, g["rled_place"][1] - 1.27, 0),
                                val_at=(g["rled_place"][0] + 3.81, g["rled_place"][1] + 1.27, 0)))

# --- 状態LED(緑) --------------------------------------------------------------
lines.append(placed_symbol("Device:R", "R9", "47", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
                            RSTATUS_POS, [1, 2], "Status LED current-limiting resistor, 47ohm (common spec, "
                                            "all puzzle modules).",
                            ref_at=(RSTATUS_POS[0] + 3.81, RSTATUS_POS[1] - 1.27, 0),
                            val_at=(RSTATUS_POS[0] + 3.81, RSTATUS_POS[1] + 1.27, 0)))
lines.append(placed_symbol("Device:LED", "LED9", "LED (status, green)", "LED_THT:LED_D3.0mm",
                            LEDSTATUS_POS, [1, 2],
                            "Module status LED, green = solved (manual p.4). Panel: top-right corner area, "
                            "inset from the corner mounting hole (common spec, all puzzle modules).",
                            ref_at=(LEDSTATUS_POS[0], LEDSTATUS_POS[1] + 3.81, 0),
                            val_at=(LEDSTATUS_POS[0], LEDSTATUS_POS[1] + 6.35, 0)))

# ===========================================================================
# 6) 電源(PWR_FLAG)まわり(password.gen_password_sch.pyの手法を踏襲)
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

# Pico LEFT column (x=452.22): 2.54mm間隔なのでオフセットはX方向(列から外す)
LEFT_COL_OFFSET = (-2.54, 0.0)
for pin in (3, 8, 13, 18):
    add_power_flag("power:GND", pico_abs(pin), 180, LEFT_COL_OFFSET, hide_value=True)

# Pico RIGHT column (x=487.78)
RIGHT_COL_OFFSET = (2.54, 0.0)
for pin in (23, 28, 33, 38):
    add_power_flag("power:GND", pico_abs(pin), 0, RIGHT_COL_OFFSET, hide_value=True)
add_power_flag("power:+3.3V", pico_abs(36), 0, RIGHT_COL_OFFSET)
add_power_flag("power:+5V", pico_abs(39), 0, RIGHT_COL_OFFSET)


# J1 pin3(+5V)/pin4(GND) -> バルクコンデンサC1 -> +5V/GND宣言+PWR_FLAG
C1_POS = (round(J1_PIN_X - 5.08, 4), round(abs_pt(J1_POS[:2], CONN01X04_PINS[3])[1] + 3.81, 4), 0)
c1_plus = abs_pt(C1_POS[:2], (0.0, 3.81))
c1_minus = abs_pt(C1_POS[:2], (0.0, -3.81))
j1_p3 = abs_pt(J1_POS[:2], CONN01X04_PINS[3])
j1_p4 = abs_pt(J1_POS[:2], CONN01X04_PINS[4])
lines.append(placed_symbol("Device:C_Polarized", "C1", "100uF/16V", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
                            C1_POS, [1, 2],
                            "Bulk capacitor on the 5V input (JST Pin3-Pin4), hub common rule 2026-09-27: "
                            "100uF/16V or larger electrolytic, one per module. Pin1(+)=+5V, pin2(-)=GND.",
                            ref_at=(C1_POS[0] - 5.08, C1_POS[1] - 1.27, 0), val_at=(C1_POS[0] - 5.08, C1_POS[1] + 1.27, 0)))

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

# +3.3V PWR_FLAG (Pico 3V3ピンの電源シンボルから)
v33_sym = (round(pico_abs(36)[0] + 2.54, 4), pico_abs(36)[1])
flag33 = (round(v33_sym[0] + 2.54, 4), v33_sym[1])
wire(v33_sym, flag33, "+3.3V")
lines.append(power_symbol_block("power:PWR_FLAG", flag33, 0, next_flg_ref(), desc="Special symbol for telling ERC where power comes from", hide_value=True))

# J2(Pin1=+3.3V, Pin2=GND)。信号線は3〜8ピンのY(Pin1,2より下)にしか来ないので、-X側へ短い枝を出す。
J2_FLAG_OFFSET = (-5.08, 0.0)
add_power_flag("power:+3.3V", abs_pt(J2_POS[:2], J2_PINS8[1]), 90, J2_FLAG_OFFSET)
add_power_flag("power:GND", abs_pt(J2_POS[:2], J2_PINS8[2]), 270, J2_FLAG_OFFSET)

# SW1のGND側(pin1)
SW_GND_OFFSET = (-5.08, 0.0)   # Pico(452.22)・BUS_X(420)から離れる側(-X)
for ref in SW_REFS:
    sw_pin1_abs = abs_pt(sw_defs[ref]["place"][:2], SW_PUSH_PINS[1])
    add_power_flag("power:GND", sw_pin1_abs, 0, SW_GND_OFFSET, hide_value=True)

# NeoPixel: VDD(上)=+5V、VSS(下)=GND、最後のDOUTは未接続
for ref in NP_REFS:
    add_power_flag("power:+5V", abs_pt(NP_POS[ref][:2], NP_PINS[1]), 0, (0.0, -2.54))
    add_power_flag("power:GND", abs_pt(NP_POS[ref][:2], NP_PINS[3]), 0, (0.0, 2.54), hide_value=True)
lines.append(no_connect_block(abs_pt(NP_POS[NP_REFS[-1]][:2], NP_PINS[2])))

# (旧)チャンネル: NPNエミッタ->GND、Rled出力->+5V
for k, g in ch_geo.items():
    add_power_flag("power:GND", g["q_emit"], 270, (0.0, 2.54), hide_value=True)
    add_power_flag("power:+5V", g["rled_pin2"], 90, (0.0, 2.54))

# 状態LEDカソード -> GND
add_power_flag("power:GND", led_status_cathode, 270, (0.0, -2.54), hide_value=True)

# no_connects
for pin in NC_PINS:
    lines.append(no_connect_block(pico_abs(pin)))

# ラベル(引き出し線の先端)とブロック見出し
for name, xy, angle in LABELS:
    lines.append(label_block(name, xy, angle))
TITLES = [
    ("J1: host link (UART0 + 5V), bulk cap C1", (J1_PIN_X - 12.7, j1_place_y - 12.7)),
    ("Side strip: 6x WS2812B NeoPixel (GP9 -> 330R -> DIN chain)", (CHANNEL_X0 - 5.08, CHANNEL_ROW_Y - 25.4)),
    ("Press detect: one MX hot-swap switch, GP4", (SW_X - 25.4, SW_Y0 - 12.7)),
    ("J2: keytop colour LCD (GC9A01, SPI0)", (J2_PIN_X - 25.4, J2_Y0 - 10.16)),
    ("Status LED", (STATUS_R_X - 5.08, STATUS_R_Y1 - 15.24)),
]
for s_, xy in TITLES:
    lines.append(text_block(s_, xy, 1.905))

# Footer
lines.append(f'{T}(sheet_instances')
lines.append(f'{T*2}(path "/"')
lines.append(f'{T*3}(page "1")')
lines.append(f'{T*2})')
lines.append(f'{T})')
lines.append(f'{T}(embedded_fonts no)')
lines.append(')')

# ===========================================================================
# 7) 事後検証: password/gen_password_sch.pyと同じ2種類のチェック
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

component_pins = [(f"U1.{k}", pico_abs(k)) for k in range(1, 41)]
component_pins += [(f"J1.{k}", abs_pt(J1_POS[:2], CONN01X04_PINS[k])) for k in range(1, 5)]
component_pins += [(f"J2.{k}", abs_pt(J2_POS[:2], J2_PINS8[k])) for k in range(1, 9)]
for ref in SW_REFS:
    component_pins += [(f"{ref}.1", abs_pt(sw_defs[ref]["place"][:2], SW_PUSH_PINS[1])),
                        (f"{ref}.2", abs_pt(sw_defs[ref]["place"][:2], SW_PUSH_PINS[2]))]
for k, g in ch_geo.items():
    component_pins += [
        (f"{RBASE_REFS[k]}.1", g["rb_pin1"]), (f"{RBASE_REFS[k]}.2", g["rb_pin2"]),
        (f"{g['qref']}.B", g["q_base"]), (f"{g['qref']}.C", g["q_coll"]), (f"{g['qref']}.E", g["q_emit"]),
        (f"{g['lref']}.K", g["led_k"]), (f"{g['lref']}.A", g["led_a"]),
        (f"{g['rref']}.1", g["rled_pin1"]), (f"{g['rref']}.2", g["rled_pin2"]),
    ]
component_pins += [("R10.1", r10_pin1), ("R10.2", r10_pin2)] + [(f"{r}.{k}", abs_pt(NP_POS[r][:2], NP_PINS[k])) for r in NP_REFS for k in range(1, 5)]
component_pins += [("R9.1", rstatus_pin1), ("R9.2", rstatus_pin2),
                    ("LED9.A", led_status_anode), ("LED9.K", led_status_cathode),
                    ("C1.+", c1_plus), ("C1.-", c1_minus)]

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

# --- プロジェクト専用シンボルライブラリ(2SC1815: フットプリントをドリル0.65mm版に差し替え) -----------
SYM_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Button_Local.kicad_sym")
_blk = LIB_2SC1815.replace('(symbol "Button_Local:2SC1815"', '(symbol "2SC1815"', 1)
with open(SYM_OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write('(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "gen_button_sch")\n\t(generator_version "10.0")\n')
    f.write(reindent(_blk, 1) + "\n)\n")
with open(os.path.join(os.path.dirname(SYM_OUT), "sym-lib-table"), "w", encoding="utf-8", newline="\n") as f:
    f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "Button_Local") (type "KiCad") (uri "${KIPRJMOD}/Button_Local.kicad_sym") (options "") (descr "Button module local symbols"))\n\t(lib (name "OSC_Shared") (type "KiCad") (uri "${KIPRJMOD}/../shared_lib/OSC_Shared.kicad_sym") (options "") (descr "OSC2026 shared symbols"))\n)\n')

OUT = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\button\button.kicad_sch"
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(doc)
print("Wrote", OUT, len(doc), "bytes")
print("Root sheet uuid:", ROOT_UUID)
