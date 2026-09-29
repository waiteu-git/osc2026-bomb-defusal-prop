#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Password module: password.kicad_sch の生成スクリプト(2026-09-27 リポジトリに保存)。
# - 実行: python gen_password_sch.py  → password.kicad_sch を上書きする(出力先パスは末尾のOUT)。
# - 生成後は必ず check_password_sch.py(ERC + ネットリストの機械照合)を実行すること。
# - 生成時に、ワイヤー同士の重なり、ピン/ワイヤー端が別ワイヤーの内部に乗っていないか、を自動チェックする。
# - KiCad標準ライブラリ(power.kicad_sym, Device.kicad_sym)を読むため KiCad 10.0 のインストールが必要。
# - ルートUUIDは password.kicad_pro と一致させて固定している。
"""Generate the full hardware/password/password.kicad_sch text and write it to disk."""
import uuid as uuidlib

def U():
    return str(uuidlib.uuid4())

T = "\t"
PROJECT = "password"
ROOT_UUID = "e8c63265-52ed-41b8-86b6-cfe4fe8a1882"  # fixed so re-runs stay in sync with password.kicad_pro

# ===========================================================================
# 1) Layout computation (same logic as gen_password_sch.py, kept in sync)
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
PICO_POS = (149.86, 76.2)

def pico_abs(pin):
    lx, ly = PICO_PINS[pin]
    return (round(PICO_POS[0] + lx, 4), round(PICO_POS[1] - ly, 4))

CONN01X04_PINS = {1: (-5.08, 2.54), 2: (-5.08, 0.0), 3: (-5.08, -2.54), 4: (-5.08, -5.08)}
SW_PUSH_PINS = {1: (-5.08, 0.0), 2: (5.08, 0.0)}
LED_PINS = {1: (-3.81, 0.0), 2: (3.81, 0.0)}   # pin1=K(cathode), pin2=A(anode)
R_PINS = {1: (0.0, 3.81), 2: (0.0, -3.81)}

def abs_pt(placement, local):
    return (round(placement[0] + local[0], 4), round(placement[1] - local[1], 4))

GND_PINS = [3, 8, 13, 18, 23, 28, 33, 38, 42]
NC_PINS = [21, 22, 24, 25, 26, 27, 29, 30, 31, 32, 34, 35, 37, 40, 41, 43]

SWITCHES = [
    (6, "SW1", "UP1 (col.1 letter up)"), (7, "SW2", "UP2 (col.2 letter up)"),
    (9, "SW3", "UP3 (col.3 letter up)"), (10, "SW4", "UP4 (col.4 letter up)"),
    (11, "SW5", "UP5 (col.5 letter up)"),
    (12, "SW6", "DOWN1 (col.1 letter down)"), (14, "SW7", "DOWN2 (col.2 letter down)"),
    (15, "SW8", "DOWN3 (col.3 letter down)"), (16, "SW9", "DOWN4 (col.4 letter down)"),
    (17, "SW10", "DOWN5 (col.5 letter down)"),
    (19, "SW11", "SUBMIT"),
]

SWITCH_X = 116.84   # 92 * 1.27 (grid-aligned). Moved right from 104.14 (2026-09-27) so the switch stubs/flags clear J1/J2
J1_PIN_X = 83.82    # 66 * 1.27 (grid-aligned). Moved from 99.06 (2026-09-27): J1.4 at (99.06,59.69) sat on the interior of the OLED_SDA wire
J2_PIN_X = 93.98    # 74 * 1.27 (grid-aligned; matches keypad.kicad_sch's own reference column)

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

sw_defs = {}
for pin, ref, label in SWITCHES:
    target = pico_abs(pin)
    place = (SWITCH_X, target[1], 0)
    sw_defs[ref] = dict(pin=pin, place=place, label=label)

led_gpio_abs = pico_abs(20)
r_place_x = 118.11   # 93 * 1.27 (grid-aligned)
r_place_y = round(led_gpio_abs[1] + R_PINS[1][1], 4)
R1_POS = (r_place_x, r_place_y, 0)
r_pin1_abs = abs_pt(R1_POS[:2], R_PINS[1])
r_pin2_abs = abs_pt(R1_POS[:2], R_PINS[2])
led_anode_target = (r_pin2_abs[0], round(r_pin2_abs[1] + 2.54, 4))  # 2.54 = 2*1.27, grid-aligned gap
led_place_x = round(led_anode_target[0] - LED_PINS[2][0], 4)
led_place_y = led_anode_target[1]
LED1_POS = (led_place_x, led_place_y, 0)
led_anode_abs = abs_pt(LED1_POS[:2], LED_PINS[2])
led_cathode_abs = abs_pt(LED1_POS[:2], LED_PINS[1])

# ===========================================================================
# 2) lib_symbols: verbatim reused blocks (copied from hardware/keypad/keypad.kicad_sch)
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

# Pico symbol: build programmatically from PICO_PINS table (bidirectional/power_in/input types)
PICO_PIN_TYPE = {}
for p in range(1, 44):
    PICO_PIN_TYPE[p] = "bidirectional"
for p in GND_PINS:
    PICO_PIN_TYPE[p] = "power_in"
PICO_PIN_TYPE[30] = "input"   # RUN
PICO_PIN_TYPE[35] = "power_in"  # ADC_VREF
PICO_PIN_TYPE[36] = "power_in"  # 3V3
PICO_PIN_TYPE[37] = "input"   # 3V3_EN
PICO_PIN_TYPE[39] = "power_in"  # VSYS
PICO_PIN_TYPE[40] = "power_in"  # VBUS
PICO_PIN_TYPE[41] = "input"   # SWCLK
PICO_PIN_TYPE[43] = "bidirectional"  # SWDIO

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
LIB_SYMBOLS_ALL = [LIB_CONN01X04, LIB_LED, LIB_R, LIB_PICO, LIB_SW, LIB_GND, LIB_3V3, LIB_5V, LIB_PWRFLAG, LIB_CP]

def reindent(block, base_tabs):
    lines = block.split("\n")
    out = []
    for ln in lines:
        out.append((T * base_tabs) + ln if ln.strip() else ln)
    return "\n".join(out)

# ===========================================================================
# 3) Placed-symbol / wire / no_connect emitters
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
# 4) Assemble the document
# ===========================================================================
lines = []
lines.append('(kicad_sch')
lines.append(f'{T}(version 20260306)')
lines.append(f'{T}(generator "eeschema")')
lines.append(f'{T}(generator_version "10.0")')
lines.append(f'{T}(uuid "{ROOT_UUID}")')
lines.append(f'{T}(paper "A4")')
lines.append(f'{T}(title_block')
lines.append(f'{T*2}(title "Password module")')
lines.append(f'{T*2}(comment 1 "OSC2026 bomb defusal prop - Password module")')
lines.append(f'{T})')
lines.append(f'{T}(lib_symbols')
for blk in LIB_SYMBOLS_ALL:
    lines.append(reindent(blk, 2))
lines.append(f'{T})')

ALL_SEGMENTS = []  # (p1, p2, net_label) for post-hoc overlap verification

# Wires
wire_list = []
wire_list.append((abs_pt(J1_POS[:2], CONN01X04_PINS[1]), tx_abs, "UART0_TX"))
wire_list.append((abs_pt(J1_POS[:2], CONN01X04_PINS[2]), rx_abs, "UART0_RX"))
wire_list.append((abs_pt(J2_POS[:2], CONN01X04_PINS[1]), sda_abs, "OLED_SDA"))
wire_list.append((abs_pt(J2_POS[:2], CONN01X04_PINS[2]), scl_abs, "OLED_SCL"))
for ref, d in sw_defs.items():
    sw_pin2_abs = abs_pt(d["place"][:2], SW_PUSH_PINS[2])
    target = pico_abs(d["pin"])
    wire_list.append((sw_pin2_abs, target, ref))
wire_list.append((led_gpio_abs, r_pin1_abs, "LED_GPIO"))
wire_list.append((r_pin2_abs, led_anode_abs, "LED_ANODE"))
for p1, p2, net in wire_list:
    lines.append(wire_block(p1, p2))
    ALL_SEGMENTS.append((p1, p2, net))

# Placed symbols: U1
lines.append(placed_symbol("RPi_Pico:Pico", "U1", "Pico", "RPi_Pico:RPi_Pico_SMD_TH",
                            (PICO_POS[0], PICO_POS[1], 0), list(range(1, 44)),
                            "Password module MCU (Raspberry Pi Pico 2, RP2350, 3.3V)."))

# J1
lines.append(placed_symbol("Connector_Generic:Conn_01x04", "J1", "MODULE_JST_XH_4P",
                            "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", J1_POS, [1, 2, 3, 4],
                            "Host connector, JST XH 4-pole. Pin1=GPIO0(UART0 TX, module->host), "
                            "Pin2=GPIO1(UART0 RX, host->module), Pin3=VCC(5V, from host per-slot polyfuse), "
                            "Pin4=GND. Fixed pinout, common to all puzzle modules (see ハブ連絡事項.md).",
                            ref_at=(J1_POS[0], J1_POS[1] - 8.89, 0), val_at=(J1_POS[0], J1_POS[1] - 6.35, 0)))

# J2
lines.append(placed_symbol("Connector_Generic:Conn_01x04", "J2", "OLED_LOCAL_I2C",
                            "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", J2_POS, [1, 2, 3, 4],
                            "Local wiring to the 0.96in SSD1315 OLED breakout, I2C1 bus (NOT the shared "
                            "UART link to host). Pin1=SDA(GP2), Pin2=SCL(GP3), Pin3=GND, Pin4=+3.3V "
                            "(from Pico 3V3 OUT, regulated). Breakout board's own header pin order "
                            "(commonly GND,VCC,SCL,SDA) may differ; match by hand when the physical "
                            "board arrives, per password_design_notes.md open item.",
                            ref_at=(J2_POS[0], J2_POS[1] + 10.16, 0), val_at=(J2_POS[0], J2_POS[1] + 12.7, 0)))

# Switches
for pin, ref, label in SWITCHES:
    place = sw_defs[ref]["place"]
    lines.append(placed_symbol("Switch:SW_Push", ref, "SW_Push", "Button_Switch_THT:SW_PUSH_6mm",
                                place, [1, 2],
                                f"Password module button: {label}. Pico physical pin {pin} "
                                f"({PICO_NAMES[pin]}), internal pull-up, no external resistor. "
                                f"Pin1=GND side, Pin2=GPIO side.",
                                ref_at=(round(SWITCH_X + 10.16, 4), round(place[1] - 1.4, 4), 0), hide_value=True))

# R1, LED1
lines.append(placed_symbol("Device:R", "R1", "47", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                            R1_POS, [1, 2], "Status LED current-limiting resistor, 47ohm (common spec, "
                                            "all puzzle modules).",
                            ref_at=(R1_POS[0] + 3.81, R1_POS[1] - 1.27, 0), val_at=(R1_POS[0] + 3.81, R1_POS[1] + 1.27, 0)))
lines.append(placed_symbol("Device:LED", "LED1", "LED (status, green)", "LED_THT:LED_D5.0mm",
                            LED1_POS, [1, 2],
                            "Module status LED, green = solved (manual p.4). Panel: top-right corner, "
                            "inset from the corner mounting hole (common spec, all puzzle modules).",
                            ref_at=(LED1_POS[0], LED1_POS[1] + 3.81, 0), val_at=(LED1_POS[0], LED1_POS[1] + 6.35, 0)))

# Power flags: placed with a small grid-aligned offset from the target pin, joined by an
# explicit wire (rather than relying on exact pin-on-pin coincidence with no wire).
pwr_counter = [0]
def next_pwr_ref():
    pwr_counter[0] += 1
    return f"#PWR{pwr_counter[0]:02d}"

flg_counter = [0]
def next_flg_ref():
    flg_counter[0] += 1
    return f"#FLG{flg_counter[0]:02d}"

# NOTE: Pico pins (and several of our own connectors) sit on shared X or Y columns spaced
# every 2.54mm. A flag offset of exactly +-2.54 along that same column can land EXACTLY on a
# neighbouring pin (a real short, caught by the ALL_SEGMENTS overlap check below), so each
# flag below is given an explicit offset chosen to move it OFF its column into empty space,
# verified by the automated overlap check at the end of this script (not just by inspection).
GND_OFFSET = (0.0, -2.54)   # default: flag sits 2.54mm below its target pin, arrow pointing down
PWR_OFFSET = (0.0, 2.54)    # default: flag sits 2.54mm above its target pin, arrow pointing up

def add_power_flag(lib_id, target_xy, angle, offset, hide_value=False):
    flag_xy = (round(target_xy[0] + offset[0], 4), round(target_xy[1] + offset[1], 4))
    ref = next_pwr_ref()
    lines.append(power_symbol_block(lib_id, flag_xy, angle, ref, hide_value=hide_value))
    lines.append(wire_block(target_xy, flag_xy))
    net = lib_id.split(":")[1]
    ALL_SEGMENTS.append((target_xy, flag_xy, net))

# Pico LEFT column (x=132.08): pins spaced every 2.54mm in Y -> offset in X instead (off-column).
LEFT_COL_OFFSET = (-2.54, 0.0)   # -> x=129.54, angle: point flag "outward" (left) = 180
for pin in (3, 8, 13, 18):
    add_power_flag("power:GND", pico_abs(pin), 180, LEFT_COL_OFFSET, hide_value=True)

# Pico RIGHT column (x=167.64): same reasoning, offset further right (away from Pico).
RIGHT_COL_OFFSET = (2.54, 0.0)   # -> x=170.18, angle 0 = point flag "outward" (right)
for pin in (23, 28, 33, 38):
    add_power_flag("power:GND", pico_abs(pin), 0, RIGHT_COL_OFFSET, hide_value=True)
add_power_flag("power:+3.3V", pico_abs(36), 0, RIGHT_COL_OFFSET)
add_power_flag("power:+5V", pico_abs(39), 0, RIGHT_COL_OFFSET)

# Pico BOTTOM row (y=105.41): pins spaced in X -> offset in Y instead (off-row), safe direction
# verified: nothing else occupies x=149.86 at y=102.87.
add_power_flag("power:GND", pico_abs(42), 270, (0.0, -2.54), hide_value=True)

# J1 pin3 (+5V) / pin4 (GND) go to the bulk capacitor C1 (hub common rule 2026-09-27: 100uF/16V+
# electrolytic next to JST Pin3-Pin4), and the +5V / GND power symbols + one PWR_FLAG per supply
# net hang off C1's two terminals (power symbols are never placed on a pin, always wired).
C1_POS = (round(J1_PIN_X - 5.08, 4), round(abs_pt(J1_POS[:2], CONN01X04_PINS[3])[1] + 3.81, 4), 0)   # C1+ (pin1) lands at J1.3's y
c1_plus = abs_pt(C1_POS[:2], (0.0, 3.81))     # pin1 (+)
c1_minus = abs_pt(C1_POS[:2], (0.0, -3.81))   # pin2 (-)
j1_p3 = abs_pt(J1_POS[:2], CONN01X04_PINS[3])
j1_p4 = abs_pt(J1_POS[:2], CONN01X04_PINS[4])
lines.append(placed_symbol("Device:C_Polarized", "C1", "100uF/16V", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
                            C1_POS, [1, 2],
                            "Bulk capacitor on the 5V input (JST Pin3-Pin4), hub common rule 2026-09-27: "
                            "100uF/16V or larger electrolytic, one per module. Pin1(+)=+5V, pin2(-)=GND. "
                            "Actual part/size to be confirmed when purchased (footprint is a 6.3mm-dia placeholder).",
                            ref_at=(C1_POS[0] - 5.08, C1_POS[1] - 1.27, 0), val_at=(C1_POS[0] - 5.08, C1_POS[1] + 1.27, 0)))

def wire(p1, p2, net):
    lines.append(wire_block(p1, p2))
    ALL_SEGMENTS.append((p1, p2, net))

# +5V: J1.3 -> C1+ ; C1+ -> +5V symbol (left) ; C1+ -> PWR_FLAG (up)
wire(j1_p3, c1_plus, "+5V")
v5_sym = (round(c1_plus[0] - 2.54, 4), c1_plus[1])
wire(c1_plus, v5_sym, "+5V")
lines.append(power_symbol_block("power:+5V", v5_sym, 90, next_pwr_ref()))
flag5 = (c1_plus[0], round(c1_plus[1] - 2.54, 4))
wire(c1_plus, flag5, "+5V")
lines.append(power_symbol_block("power:PWR_FLAG", flag5, 0, next_flg_ref(), desc="Special symbol for telling ERC where power comes from", hide_value=True))

# GND: J1.4 -> (bend) -> C1- ; C1- -> GND symbol (left) ; C1- -> PWR_FLAG (down)
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

# +3.3V PWR_FLAG: hang off the Pico 3V3 power symbol (pin 36, symbol at x+2.54)
v33_sym = (round(pico_abs(36)[0] + 2.54, 4), pico_abs(36)[1])
flag33 = (round(v33_sym[0] + 2.54, 4), v33_sym[1])
wire(v33_sym, flag33, "+3.3V")
lines.append(power_symbol_block("power:PWR_FLAG", flag33, 0, next_flg_ref(), desc="Special symbol for telling ERC where power comes from", hide_value=True))

# J2 (x=93.98 column): offset away from Pico (-X), clear of J1's x=99.06 column.
J2_FLAG_OFFSET = (-5.08, 0.0)
add_power_flag("power:GND", abs_pt(J2_POS[:2], CONN01X04_PINS[3]), 270, J2_FLAG_OFFSET)
add_power_flag("power:+3.3V", abs_pt(J2_POS[:2], CONN01X04_PINS[4]), 90, J2_FLAG_OFFSET)

# Switch GND pins (x=104.14-5.08=99.06 column, many pairs exactly 2.54mm apart): offset in X
# (away from Pico, -X) instead of Y so no switch's flag can land on a neighbouring switch's pin.
SW_GND_OFFSET = (-2.54, 0.0)   # -> x=96.52, clear of J2's x=93.98 and J1/switch-pin1's x=99.06
for ref, d in sw_defs.items():
    sw_pin1_abs = abs_pt(d["place"][:2], SW_PUSH_PINS[1])
    add_power_flag("power:GND", sw_pin1_abs, 180, SW_GND_OFFSET, hide_value=True)

# LED1 cathode: isolated point, default Y offset is fine (verified by the overlap check below).
add_power_flag("power:GND", led_cathode_abs, 270, GND_OFFSET, hide_value=True)

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
# 5) Post-hoc overlap verification: any two DIFFERENT-net segments that are
#    collinear and share more than an endpoint indicate an unintended short.
#    Also flag any point shared by >=2 distinct-net segments' ENDPOINTS.
# ===========================================================================
def seg_overlap_1d(a0, a1, b0, b1):
    lo1, hi1 = min(a0, a1), max(a0, a1)
    lo2, hi2 = min(b0, b1), max(b0, b1)
    lo = max(lo1, lo2)
    hi = min(hi1, hi2)
    return hi - lo  # >0 real overlap, ==0 touching at a point, <0 no overlap

problems = []
n = len(ALL_SEGMENTS)
for i in range(n):
    p1, p2, net1 = ALL_SEGMENTS[i]
    for j in range(i + 1, n):
        q1, q2, net2 = ALL_SEGMENTS[j]
        if net1 == net2:
            continue
        # vertical vs vertical, same x
        if p1[0] == p2[0] == q1[0] == q2[0]:
            ov = seg_overlap_1d(p1[1], p2[1], q1[1], q2[1])
            if ov > 0:
                problems.append(f"OVERLAP (vertical x={p1[0]}) {net1} vs {net2}: {p1}-{p2} / {q1}-{q2}")
        # horizontal vs horizontal, same y
        if p1[1] == p2[1] == q1[1] == q2[1]:
            ov = seg_overlap_1d(p1[0], p2[0], q1[0], q2[0])
            if ov > 0:
                problems.append(f"OVERLAP (horizontal y={p1[1]}) {net1} vs {net2}: {p1}-{p2} / {q1}-{q2}")
        # exact shared endpoint between different nets (a true short)
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

# --- 5b) pin-on-wire and wire-end-on-wire checks (added 2026-09-27) --------------------------
# The check above only compares wire vs wire. A component PIN (or another wire's end) sitting on the
# INTERIOR of a foreign wire is not connected by KiCad's netlister today, but is a latent short
# (J1.4/GND sat on the OLED_SDA wire in the first version and was missed).
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
for _ref, _d in sw_defs.items():
    component_pins += [(f"{_ref}.1", abs_pt(_d["place"][:2], SW_PUSH_PINS[1])),
                       (f"{_ref}.2", abs_pt(_d["place"][:2], SW_PUSH_PINS[2]))]
component_pins += [("R1.1", r_pin1_abs), ("R1.2", r_pin2_abs), ("LED1.A", led_anode_abs),
                   ("LED1.K", led_cathode_abs), ("C1.+", c1_plus), ("C1.-", c1_minus)]

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

OUT = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\password\password.kicad_sch"
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(doc)
print("Wrote", OUT, len(doc), "bytes")
print("Root sheet uuid:", ROOT_UUID)
