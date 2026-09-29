#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Button module: button.kicad_sch の生成スクリプト(2026-09-27作成、C案=単色LED+NPNローサイド駆動+OLED)。
# password/simon の生成手法(password/gen_password_sch.py)を踏襲: 全部品angle=0固定、abs_pt()はY反転のみ
# (回転は考慮しない)、生成後に自動でワイヤー重なり・ピン/ワイヤー端の内部一致をチェックする。
# 実行: python gen_button_sch.py  → button.kicad_sch を上書きする。
# 生成後は必ず check_button_sch.py(ERC + ネットリストの機械照合)を実行すること。
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

PICO_POS = (G(500), G(60))  # =(635.0, 76.2)。全座標は1.27mm格子の整数倍(G(n))で統一する。
                            # 8chの色LED列+J1/J2+SWバスを左側に展開するため広め(A1シート)に確保。

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

GND_PINS = [3, 8, 13, 18, 23, 28, 33, 38, 42]
# 使用するPico物理ピン: 1,2(UART) 4,5(OLED I2C) 6(ボタン押下) 7,9,10,11,12,14,15,16(色LED8ch) 20(状態LED)
USED_PINS = {1, 2, 4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 20}
NC_PINS = [p for p in range(1, 44) if p not in USED_PINS and p not in GND_PINS
           and p not in (36, 39)]  # 36=3V3, 39=VSYSはPWR_FLAGで処理(no_connectにしない)

# ===========================================================================
# 2) レイアウト定数(すべてG(n)=n*1.27で格子に厳密整列させる)
# ===========================================================================
PICO_LEFT_X = PICO_POS[0] - 17.78   # GP0-15側の列(左列)
PICO_RIGHT_X = PICO_POS[0] + 17.78  # GP16以降の列(右列)

J1_PIN_X = PICO_LEFT_X - G(38)    # UARTコネクタ(GP0/1)。password基準(132.08-83.82=48.26=38*1.27)を踏襲
J2_PIN_X = J1_PIN_X + G(8)        # OLEDローカルI2C(GP2/3)。password基準(+10.16=8*1.27)を踏襲
# BUS_XはPicoのすぐ左(J1/J2のX範囲に絶対入らない近さ)に置き、GP4からの水平引き出しを
# J1/J2/C1のクラスタと交差させない。BUS_Xに着地した後はY方向にジャンプしてから、
# J1/J2とは全く別のY帯(SW_ROW_Y)で左へ展開する(§5の配線コードを参照)。
BUS_X = PICO_LEFT_X - G(10)
SW_ROW_Y = PICO_POS[1] + G(90)    # J1/J2/C1のY帯(Pico上寄り)から十分離す
SW_ENTRY_X = J1_PIN_X - G(30)     # ボタン押下スイッチ本体列(J1/J2よりさらに左、Y帯が別なので交差OK)
CHANNEL_PITCH_X = G(40)           # =50.8mm。1ch分(R_base+Q+LED+R_led+flag、必要幅約45mm)より余裕を持たせる
CHANNEL_X0 = SW_ENTRY_X - G(46)   # 色LEDチャンネル群の右端(ch0=白面)。左へ向かってch7まで並ぶ
CHANNEL_ROW_Y = PICO_POS[1] + G(160)  # 8色LEDチャンネルの基準行(SW_ROW_Yからさらに下)
STATUS_R_X = J2_PIN_X + G(10)     # 状態LED用抵抗(J2の右、Picoに近い側)

tx_abs = pico_abs(1)
rx_abs = pico_abs(2)
j1_place_y = round(tx_abs[1] + CONN01X04_PINS[1][1], 4)
j1_place_x = round(J1_PIN_X + 5.08, 4)
J1_POS = (j1_place_x, j1_place_y, 0)

sda_abs = pico_abs(4)
scl_abs = pico_abs(5)
j2_place_y = round(sda_abs[1] + CONN01X04_PINS[1][1], 4)
j2_place_x = round(J2_PIN_X + 5.08, 4)
J2_POS = (j2_place_x, j2_place_y, 0)

# --- ボタン押下スイッチ(SW1-4、GP4に並列) -----------------------------------
# GP4の絶対Yはpin7/9等の他の実ピンと2.54mm間隔で近接しているため、Picoの列(X=PICO_LEFT_X)
# ではGP4自身の1点以外を絶対に通らせない。BUS_Xまでは短い水平配線のみで抜け、そこから
# J1/J2/C1のクラスタとは別のY帯(SW_ROW_Y)まで垂直移動してから、SW_ENTRY_X列で
# 左へ展開する(この移動先Y帯は他のどの部品も使わないため、J1/J2のX範囲を横切っても安全)。
btn_gpio_abs = pico_abs(6)  # GP4
SW_Y = [SW_ROW_Y - G(7), SW_ROW_Y - G(3), SW_ROW_Y + G(3), SW_ROW_Y + G(7)]
SW_REFS = ["SW1", "SW2", "SW3", "SW4"]
sw_defs = {}
for ref, y in zip(SW_REFS, SW_Y):
    sw_defs[ref] = dict(place=(SW_ENTRY_X, y, 0))
BUS_CHAIN_Y = [SW_Y[0], SW_Y[1], SW_ROW_Y, SW_Y[2], SW_Y[3]]  # 昇順にソート済み前提

# --- 色LEDチャンネル(8ch: 面White/Blue/Red/Yellow, ストリップWhite/Blue/Red/Yellow) --
CHANNELS = [
    ("Q1", "R1", "LED1", "GP5", 7,  "White", "OS4WMLA131A", "100", "Face LED (white)"),
    ("Q2", "R2", "LED2", "GP6", 9,  "Blue",  "OSB56AA131A", "100", "Face LED (blue)"),
    ("Q3", "R3", "LED3", "GP7", 10, "Red",   "OS5RAAA131A", "150", "Face LED (red)"),
    ("Q4", "R4", "LED4", "GP8", 11, "Yellow","OS5YAAA131A", "150", "Face LED (yellow)"),
    ("Q5", "R5", "LED5", "GP9", 12, "White", "OS4WMLA131A", "100", "Side strip LED (white)"),
    ("Q6", "R6", "LED6", "GP10",14, "Blue",  "OSB56AA131A", "100", "Side strip LED (blue)"),
    ("Q7", "R7", "LED7", "GP11",15, "Red",   "OS5RAAA131A", "150", "Side strip LED (red)"),
    ("Q8", "R8", "LED8", "GP12",16, "Yellow","OS5YAAA131A", "150", "Side strip LED (yellow)"),
]
RBASE_REFS = ["RB1", "RB2", "RB3", "RB4", "RB5", "RB6", "RB7", "RB8"]

ch_geo = {}
for k, (qref, rref, lref, gpio_name, pin, color, part, rval, desc) in enumerate(CHANNELS):
    cx = CHANNEL_X0 + k * CHANNEL_PITCH_X
    gpio_abs = pico_abs(pin)
    # R_base: pin1のYがCHANNEL_ROW_Yに一致するよう配置(GPIOからの垂直ドロップの着地点)
    rb_place = (cx, CHANNEL_ROW_Y + R_PINS[1][1], 0)
    rb_pin1 = abs_pt(rb_place[:2], R_PINS[1])   # = (cx, CHANNEL_ROW_Y)
    rb_pin2 = abs_pt(rb_place[:2], R_PINS[2])   # = (cx, CHANNEL_ROW_Y + 7.62)
    # Q: baseのYがrb_pin2のYに一致
    q_x = cx + 10.16
    q_place = (q_x, rb_pin2[1], 0)
    q_base = abs_pt(q_place[:2], Q_PINS[3])     # (q_x-5.08, rb_pin2.y)
    q_coll = abs_pt(q_place[:2], Q_PINS[2])     # (q_x+2.54, rb_pin2.y-5.08)
    q_emit = abs_pt(q_place[:2], Q_PINS[1])     # (q_x+2.54, rb_pin2.y+5.08)
    # LED: KのYがq_collのYに一致(cathode = collector側)
    led_x = q_x + G(11)   # =13.97
    led_place = (led_x, q_coll[1], 0)
    led_k = abs_pt(led_place[:2], LED_PINS[1])  # (led_x-3.81, q_coll.y)
    led_a = abs_pt(led_place[:2], LED_PINS[2])  # (led_x+3.81, q_coll.y)
    # R_led: pin1のYがled_aのYに一致(anode側、+5Vへ)
    rled_x = led_x + G(9)   # =11.43
    rled_place = (rled_x, led_a[1] + R_PINS[1][1], 0)
    rled_pin1 = abs_pt(rled_place[:2], R_PINS[1])  # (rled_x, led_a.y)
    rled_pin2 = abs_pt(rled_place[:2], R_PINS[2])  # (rled_x, led_a.y+7.62)
    ch_geo[k] = dict(
        qref=qref, rref=rref, lref=lref, gpio_name=gpio_name, pin=pin, color=color, part=part,
        rval=rval, desc=desc, cx=cx, gpio_abs=gpio_abs,
        rb_place=rb_place, rb_pin1=rb_pin1, rb_pin2=rb_pin2,
        q_place=q_place, q_base=q_base, q_coll=q_coll, q_emit=q_emit,
        led_place=led_place, led_k=led_k, led_a=led_a,
        rled_place=rled_place, rled_pin1=rled_pin1, rled_pin2=rled_pin2,
    )

# --- 状態LED(緑、GP15) -------------------------------------------------------
led_gpio_abs = pico_abs(20)
r_place_x = STATUS_R_X
r_place_y = round(led_gpio_abs[1] + R_PINS[1][1], 4)
RSTATUS_POS = (r_place_x, r_place_y, 0)
rstatus_pin1 = abs_pt(RSTATUS_POS[:2], R_PINS[1])
rstatus_pin2 = abs_pt(RSTATUS_POS[:2], R_PINS[2])
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

LIB_2SC1815 = r'''(symbol "Transistor_BJT:2SC1815"
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
	(property "Footprint" "Package_TO_SOT_THT:TO-92_Inline"
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
LIB_SYMBOLS_ALL = [LIB_CONN01X04, LIB_LED, LIB_R, LIB_PICO, LIB_SW, LIB_2SC1815,
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

# ===========================================================================
# 5) 組み立て
# ===========================================================================
lines = []
lines.append('(kicad_sch')
lines.append(f'{T}(version 20260306)')
lines.append(f'{T}(generator "eeschema")')
lines.append(f'{T}(generator_version "10.0")')
lines.append(f'{T}(uuid "{ROOT_UUID}")')
lines.append(f'{T}(paper "A1")')
lines.append(f'{T}(title_block')
lines.append(f'{T*2}(title "Button module")')
lines.append(f'{T*2}(comment 1 "OSC2026 bomb defusal prop - Button module (interpretation C: electrical gate)")')
lines.append(f'{T})')
lines.append(f'{T}(lib_symbols')
for blk in LIB_SYMBOLS_ALL:
    lines.append(reindent(blk, 2))
lines.append(f'{T})')

ALL_SEGMENTS = []

def wire(p1, p2, net):
    lines.append(wire_block(p1, p2))
    ALL_SEGMENTS.append((p1, p2, net))

# --- UART(J1)・OLED I2C(J2) -------------------------------------------------
wire(abs_pt(J1_POS[:2], CONN01X04_PINS[1]), tx_abs, "UART0_TX")
wire(abs_pt(J1_POS[:2], CONN01X04_PINS[2]), rx_abs, "UART0_RX")
wire(abs_pt(J2_POS[:2], CONN01X04_PINS[1]), sda_abs, "OLED_SDA")
wire(abs_pt(J2_POS[:2], CONN01X04_PINS[2]), scl_abs, "OLED_SCL")

# --- ボタン押下スイッチ(SW1-4、GP4に並列。BUS_Xを経由してSW_ROW_Y帯に抜ける) ---
# Picoの列(X=PICO_LEFT_X)に触れるのはGP4自身の1点だけ。そこから短い水平配線でBUS_X列へ抜け、
# BUS_X列上を垂直にSW_ROW_Y帯まで移動する(この区間はBUS_X上に他の部品が無いので安全)。
# SW_ROW_Y帯に入ってからSW_ENTRY_X列まで水平移動し(J1/J2のX範囲を横切るが、Y帯が別なので
# 交差しても安全)、SW_ENTRY_X列上でのみ縦の数珠つなぎ(隣接ノードだけを結ぶ)を行う。
sw_pin2 = {ref: abs_pt(sw_defs[ref]["place"][:2], SW_PUSH_PINS[2]) for ref in SW_REFS}
wire(btn_gpio_abs, (BUS_X, btn_gpio_abs[1]), "BTN")            # Pico実ピン(GP4)一点のみ -> BUS_X列
wire((BUS_X, btn_gpio_abs[1]), (BUS_X, SW_ROW_Y), "BTN")       # BUS_X列上を垂直にSW_ROW_Y帯へ
wire((BUS_X, SW_ROW_Y), (SW_ENTRY_X, SW_ROW_Y), "BTN")         # SW_ROW_Y帯を水平にSW_ENTRY_X列へ
for y1, y2 in zip(BUS_CHAIN_Y[:-1], BUS_CHAIN_Y[1:]):
    wire((SW_ENTRY_X, y1), (SW_ENTRY_X, y2), "BTN")            # SW_ENTRY_X列上の隣接ノードだけを縦につなぐ
for ref in SW_REFS:
    wire((SW_ENTRY_X, sw_defs[ref]["place"][1]), sw_pin2[ref], "BTN")  # 同列上の枝(SW自身のpin2)

# --- 8色LEDチャンネル ---------------------------------------------------------
for k, g in ch_geo.items():
    wire(g["gpio_abs"], g["rb_pin1"], f"GPIO_{g['gpio_name']}")
    wire(g["rb_pin2"], g["q_base"], f"BASE{k+1}")
    wire(g["q_coll"], g["led_k"], f"COLL{k+1}")
    wire(g["led_a"], g["rled_pin1"], f"ANODE{k+1}")

# --- 状態LED(緑) -------------------------------------------------------------
wire(led_gpio_abs, rstatus_pin1, "STATUS_LED_GPIO")
wire(rstatus_pin2, led_status_anode, "STATUS_LED_ANODE")

# --- 部品配置: Pico -----------------------------------------------------------
lines.append(placed_symbol("RPi_Pico:Pico", "U1", "Pico", "RPi_Pico:RPi_Pico_SMD_TH",
                            (PICO_POS[0], PICO_POS[1], 0), list(range(1, 44)),
                            "Button module MCU (Raspberry Pi Pico 2, RP2350, 3.3V)."))

# --- J1(UART) -----------------------------------------------------------------
lines.append(placed_symbol("Connector_Generic:Conn_01x04", "J1", "MODULE_JST_XH_4P",
                            "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", J1_POS, [1, 2, 3, 4],
                            "Host connector, JST XH 4-pole. Pin1=GPIO0(UART0 TX, module->host), "
                            "Pin2=GPIO1(UART0 RX, host->module), Pin3=VCC(5V, from host per-slot polyfuse "
                            "MF-RX030/72-0 0.3A hold), Pin4=GND. Common to all puzzle modules (see ハブ連絡事項.md).",
                            ref_at=(J1_POS[0], J1_POS[1] - 8.89, 0), val_at=(J1_POS[0], J1_POS[1] - 6.35, 0)))

# --- J2(キートップ表示器 ローカルI2C、部品未定) --------------------------------
lines.append(placed_symbol("Connector_Generic:Conn_01x04", "J2", "KEYTOP_DISPLAY_I2C",
                            "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", J2_POS, [1, 2, 3, 4],
                            "Local wiring to the keytop-mounted word-label display (word: 中止/起爆/長押し/押す). "
                            "Display part is not yet chosen by the user (2026-09-29: probably not the 0.96in "
                            "SSD1315 OLED used elsewhere in the project; user is selecting parts and asked to "
                            "design the board first) -- this header reserves I2C1 on Pin1=SDA(GP2), Pin2=SCL(GP3), "
                            "Pin3=GND, Pin4=+3.3V (from Pico 3V3 OUT), which fits most small I2C displays. Because "
                            "the display now sits on the moving keytop rather than a fixed panel window, this "
                            "connector represents a flexible-cable link (exact connector/cable type TBD by user). "
                            "If the chosen display needs SPI instead of I2C, reassign to spare GPIOs (GP13/14/16-22/"
                            "26-28) and update this connector -- not yet done, since the part is unpicked.",
                            ref_at=(J2_POS[0], J2_POS[1] + 10.16, 0), val_at=(J2_POS[0], J2_POS[1] + 12.7, 0)))

# --- SW1-4(押下検出、ドーム縁4点を想定・全て並列) -------------------------------
for ref in SW_REFS:
    place = sw_defs[ref]["place"]
    lines.append(placed_symbol("Switch:SW_Push", ref, "SW_Push", "Button_Switch_THT:SW_PUSH_6mm",
                                place, [1, 2],
                                f"Button press detection, one of 4 tacts around the dome rim, all wired in "
                                f"parallel onto GP4 (single logical button). Pico physical pin 6 (GPIO4), "
                                f"internal pull-up, no external resistor. Pin1=GND side, Pin2=GPIO side.",
                                ref_at=(round(SW_ENTRY_X + 10.16, 4), round(place[1] - 1.4, 4), 0), hide_value=True))

# --- 8色LEDチャンネル: R_base, Q, LED, R_led --------------------------------
for k, g in ch_geo.items():
    lines.append(placed_symbol("Device:R", RBASE_REFS[k], "4.7k",
                                "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                                g["rb_place"], [1, 2],
                                f"Base resistor for {g['desc']} ({g['color']}), NPN low-side switch. "
                                f"Ib=(3.3-0.7)/4.7k=0.55mA, forced beta well under 2SC1815-GR min hFE(200). "
                                f"No separate base pulldown (RP2350-E9 affects A2 stepping only; firmware "
                                f"drives this pin output-low from boot, per ハブ連絡事項.md 2026-09-27).",
                                ref_at=(g["rb_place"][0] + 3.81, g["rb_place"][1] - 1.27, 0),
                                val_at=(g["rb_place"][0] + 3.81, g["rb_place"][1] + 1.27, 0)))
    lines.append(placed_symbol("Transistor_BJT:2SC1815", g["qref"], "2SC1815",
                                "Package_TO_SOT_THT:TO-92_Inline", g["q_place"], [1, 2, 3],
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
                                val_at=(g["led_place"][0], g["led_place"][1] + 3.81, 0)))
    lines.append(placed_symbol("Device:R", g["rref"], g["rval"],
                                "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                                g["rled_place"], [1, 2],
                                f"Series current-limiting resistor for {g['lref']} ({g['color']}), "
                                f"targets ~18-20mA from +5V (I=(5-Vf-0.1)/R; trim by measurement, per "
                                f"button_design_notes.md sec.3-C).",
                                ref_at=(g["rled_place"][0] + 3.81, g["rled_place"][1] - 1.27, 0),
                                val_at=(g["rled_place"][0] + 3.81, g["rled_place"][1] + 1.27, 0)))

# --- 状態LED(緑) --------------------------------------------------------------
lines.append(placed_symbol("Device:R", "R9", "47", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                            RSTATUS_POS, [1, 2], "Status LED current-limiting resistor, 47ohm (common spec, "
                                            "all puzzle modules).",
                            ref_at=(RSTATUS_POS[0] + 3.81, RSTATUS_POS[1] - 1.27, 0),
                            val_at=(RSTATUS_POS[0] + 3.81, RSTATUS_POS[1] + 1.27, 0)))
lines.append(placed_symbol("Device:LED", "LED9", "LED (status, green)", "LED_THT:LED_D5.0mm",
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

# Pico BOTTOM row
add_power_flag("power:GND", pico_abs(42), 270, (0.0, -2.54), hide_value=True)

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

# J2(GND/+3.3V)
J2_FLAG_OFFSET = (-5.08, 0.0)   # BUS_X(420)・Pico列(452.22)から離す(-X側)
add_power_flag("power:GND", abs_pt(J2_POS[:2], CONN01X04_PINS[3]), 270, J2_FLAG_OFFSET)
add_power_flag("power:+3.3V", abs_pt(J2_POS[:2], CONN01X04_PINS[4]), 90, J2_FLAG_OFFSET)

# SW1-4のGND側(pin1)
SW_GND_OFFSET = (-5.08, 0.0)   # Pico(452.22)・BUS_X(420)から離れる側(-X)
for ref in SW_REFS:
    sw_pin1_abs = abs_pt(sw_defs[ref]["place"][:2], SW_PUSH_PINS[1])
    add_power_flag("power:GND", sw_pin1_abs, 0, SW_GND_OFFSET, hide_value=True)

# 8チャンネル: NPNエミッタ->GND、Rled出力->+5V
for k, g in ch_geo.items():
    add_power_flag("power:GND", g["q_emit"], 270, (0.0, 2.54), hide_value=True)
    add_power_flag("power:+5V", g["rled_pin2"], 90, (0.0, 2.54))

# 状態LEDカソード -> GND
add_power_flag("power:GND", led_status_cathode, 270, (0.0, -2.54), hide_value=True)

# no_connects
for pin in NC_PINS:
    lines.append(no_connect_block(pico_abs(pin)))

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

component_pins = [(f"U1.{k}", pico_abs(k)) for k in range(1, 44)]
component_pins += [(f"J1.{k}", abs_pt(J1_POS[:2], CONN01X04_PINS[k])) for k in range(1, 5)]
component_pins += [(f"J2.{k}", abs_pt(J2_POS[:2], CONN01X04_PINS[k])) for k in range(1, 5)]
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

OUT = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\button\button.kicad_sch"
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(doc)
print("Wrote", OUT, len(doc), "bytes")
print("Root sheet uuid:", ROOT_UUID)
