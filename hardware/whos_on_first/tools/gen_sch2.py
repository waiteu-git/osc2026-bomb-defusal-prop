#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part 2: body content (wires, labels, symbol instances) + final assembly.
Run after gen_sch.py has produced lib_symbols_check.txt (the full lib_symbols
block including the new Conn_01x08 symbol)."""
import uuid

def u():
    return str(uuid.uuid4())

def fmt(n):
    s = f"{n:.4f}".rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s

OUT_PATH = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\whos_on_first\whos_on_first.kicad_sch"
PROJECT = "whos_on_first"
ROOT_UUID = "9f1c2a3b-4d5e-4f60-8a1b-2c3d4e5f6071"  # fixed, arbitrary

with open("lib_symbols_check.txt", "r", encoding="utf-8") as f:
    lib_symbols_block = f.read()

body_parts = []

def wire(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    body_parts.append(
        f'\t(wire\n\t\t(pts\n\t\t\t(xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)})\n\t\t)\n'
        f'\t\t(stroke (width 0) (type default))\n\t\t(uuid "{u()}")\n\t)\n'
    )

def label(text, pos, justify="left bottom"):
    x, y = pos
    body_parts.append(
        f'\t(label "{text}"\n\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t(effects (font (size 1.27 1.27)) (justify {justify}))\n'
        f'\t\t(uuid "{u()}")\n\t)\n'
    )

_pwr_counter = [0]
def power_symbol(value, pos, angle):
    """value in {'GND','+3.3V','+5V'}"""
    _pwr_counter[0] += 1
    ref = f"#PWR{_pwr_counter[0]:02d}"
    x, y = pos
    lib_id = f"power:{value}"
    # reference/value label offsets copied loosely from keypad.kicad_sch style
    body_parts.append(
        f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {fmt(x)} {fmt(y)} {angle})\n'
        f'\t\t(unit 1) (body_style 1) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
        f'\t\t(in_pos_files yes) (dnp no) (fields_autoplaced yes)\n'
        f'\t\t(uuid "{u()}")\n'
        f'\t\t(property "Reference" "{ref}"\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Value" "{value}"\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t\t(show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Footprint" ""\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Datasheet" ""\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Description" "Power symbol creates a global label with name \\"{value}\\""\n'
        f'\t\t\t(at {fmt(x)} {fmt(y)} 0)\n\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(pin "1" (uuid "{u()}"))\n'
        f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"\n'
        f'\t\t\t\t\t(reference "{ref}") (unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'
    )

_ref_counters = {}

def junction(pos):
    x, y = pos
    body_parts.append(
        f'\t(junction\n\t\t(at {fmt(x)} {fmt(y)})\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n'
        f'\t\t(uuid "{u()}")\n\t)\n'
    )

def no_connect(pos):
    x, y = pos
    body_parts.append(
        f'\t(no_connect\n\t\t(at {fmt(x)} {fmt(y)})\n\t\t(uuid "{u()}")\n\t)\n'
    )

def note(text, pos):
    x, y = pos
    body_parts.append(
        f'\t(text "{text}"\n\t\t(exclude_from_sim no)\n\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n'
        f'\t\t(uuid "{u()}")\n\t)\n'
    )

_flg_counter = [0]
def pwr_flag(pos):
    _flg_counter[0] += 1
    ref = f"#FLG{_flg_counter[0]:02d}"
    x, y = pos
    body_parts.append(
        f'\t(symbol\n\t\t(lib_id "power:PWR_FLAG")\n\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t(unit 1) (body_style 1) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
        f'\t\t(in_pos_files yes) (dnp no) (fields_autoplaced yes)\n'
        f'\t\t(uuid "{u()}")\n'
        f'\t\t(property "Reference" "{ref}"\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Value" "PWR_FLAG"\n\t\t\t(at {fmt(x)} {fmt(y-3.81)} 0)\n'
        f'\t\t\t(show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Footprint" ""\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Datasheet" "~"\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Description" "Special symbol for telling ERC where power comes from"\n'
        f'\t\t\t(at {fmt(x)} {fmt(y)} 0)\n\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(pin "1" (uuid "{u()}"))\n'
        f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"\n'
        f'\t\t\t\t\t(reference "{ref}") (unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'
    )
def component(lib_id, ref, value, footprint, description, pos, angle, pins, extra_props=None):
    x, y = pos
    pin_block = "".join(f'\t\t(pin "{p}" (uuid "{u()}"))\n' for p in pins)
    props = ""
    if extra_props:
        for pname, pval in extra_props.items():
            props += (
                f'\t\t(property "{pname}" "{pval}"\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
                f'\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
                f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
            )
    body_parts.append(
        f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {fmt(x)} {fmt(y)} {angle})\n'
        f'\t\t(unit 1) (body_style 1) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
        f'\t\t(in_pos_files yes) (dnp no) (fields_autoplaced yes)\n'
        f'\t\t(uuid "{u()}")\n'
        f'\t\t(property "Reference" "{ref}"\n\t\t\t(at {fmt(x)} {fmt(y-4)} 0)\n'
        f'\t\t\t(show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Value" "{value}"\n\t\t\t(at {fmt(x)} {fmt(y+4)} 0)\n'
        f'\t\t\t(show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Footprint" "{footprint}"\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Datasheet" ""\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        f'\t\t(property "Description" "{description}"\n\t\t\t(at {fmt(x)} {fmt(y)} 0)\n'
        f'\t\t\t(hide yes) (show_name no) (do_not_autoplace no)\n'
        f'\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n'
        + props +
        pin_block +
        f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"\n'
        f'\t\t\t\t\t(reference "{ref}") (unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'
    )

print("helpers loaded OK")

# ---------------------------------------------------------------------------
# Pico U1 at (149.86, 76.2, 0). Left column pins at x=132.08 (local_x=-17.78),
# right column at x=167.64 (local_x=+17.78). abs_y = 76.2 - local_y.
# Table below: (pin_number, name, abs_y) for the pins we actually use.
# ---------------------------------------------------------------------------
PICO_X, PICO_Y = 149.86, 76.2
PICO_LEFT_X = PICO_X - 17.78   # 132.08
PICO_RIGHT_X = PICO_X + 17.78  # 167.64

pico_pins_used = {
    "GP0": (1, PICO_LEFT_X, 52.07),
    "GP1": (2, PICO_LEFT_X, 54.61),
    "GND_L1": (3, PICO_LEFT_X, 57.15),
    "GP2": (4, PICO_LEFT_X, 59.69),
    "GP3": (5, PICO_LEFT_X, 62.23),
    "GP4": (6, PICO_LEFT_X, 64.77),
    "GP5": (7, PICO_LEFT_X, 67.31),
    "GND_L2": (8, PICO_LEFT_X, 69.85),
    "GP6": (9, PICO_LEFT_X, 72.39),
    "GP7": (10, PICO_LEFT_X, 74.93),
    "GP8": (11, PICO_LEFT_X, 77.47),
    "GP9": (12, PICO_LEFT_X, 80.01),
    "GND_L3": (13, PICO_LEFT_X, 82.55),
    "GP10": (14, PICO_LEFT_X, 85.09),
    "GP11": (15, PICO_LEFT_X, 87.63),
    "GP12": (16, PICO_LEFT_X, 90.17),
    "GP13": (17, PICO_LEFT_X, 92.71),
    "GND_L4": (18, PICO_LEFT_X, 95.25),
    "GP14": (19, PICO_LEFT_X, 97.79),
    "GP15": (20, PICO_LEFT_X, 100.33),
    "GP16": (21, PICO_RIGHT_X, 100.33),
    "GP17": (22, PICO_RIGHT_X, 97.79),
    "GND_R1": (23, PICO_RIGHT_X, 95.25),
    "GND_R2": (28, PICO_RIGHT_X, 82.55),
    "3V3": (36, PICO_RIGHT_X, 62.23),
    "GND_R3": (38, PICO_RIGHT_X, 57.15),
    "VSYS": (39, PICO_RIGHT_X, 54.61),
}

# All 43 Pico pin numbers (needed for the U1 symbol instance's pin uuid list,
# matching keypad.kicad_sch's U1 block which lists every pin regardless of use).
ALL_PICO_PINS = [str(n) for n in range(1, 44)]

# ---------------------------------------------------------------------------
# U1: Raspberry Pi Pico 2
# ---------------------------------------------------------------------------
component(
    "RPi_Pico:Pico", "U1", "Pico 2", "RPi_Pico:RPi_Pico_SMD_TH",
    "MCU: Raspberry Pi Pico 2 (RP2350). GPIO0/1 reserved for UART0 (host link).",
    (PICO_X, PICO_Y), 0, ALL_PICO_PINS,
)

# ---------------------------------------------------------------------------
# J1: JST XH 4-pole host connector (UART). Pin1=GP0 TX, Pin2=GP1 RX,
# Pin3=VCC(5V), Pin4=GND. Placement chosen so pin1/pin2 land exactly on
# GP0/GP1's Y (direct wires, no jog needed).
# ---------------------------------------------------------------------------
J1_X, J1_Y = 99.06, 54.61
component(
    "Connector_Generic:Conn_01x04", "J1", "JST_XH_HOST_UART",
    "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
    "Host link: JST XH 4-pole. Pin1=GPIO0(UART0 TX, module->host), Pin2=GPIO1(UART0 RX, host->module), Pin3=VCC(5V, polyfuse per-panel on host side), Pin4=GND. Per-module UART, not shared I2C bus (OSC2026 common spec 2026-09-24).",
    (J1_X, J1_Y), 0, ["1", "2", "3", "4"],
)
J1_PIN1 = (J1_X - 5.08, J1_Y - 2.54)   # (93.98, 52.07) -> GP0
J1_PIN2 = (J1_X - 5.08, J1_Y - 0)      # (93.98, 54.61) -> GP1
J1_PIN3 = (J1_X - 5.08, J1_Y - (-2.54))  # (93.98, 57.15) -> +5V
J1_PIN4 = (J1_X - 5.08, J1_Y - (-5.08))  # (93.98, 59.69) -> GND

wire(J1_PIN1, (pico_pins_used["GP0"][1], pico_pins_used["GP0"][2]))
wire(J1_PIN2, (pico_pins_used["GP1"][1], pico_pins_used["GP1"][2]))
label("UART_TX_GP0", (J1_PIN1[0] + 2, J1_PIN1[1]))
label("UART_RX_GP1", (J1_PIN2[0] + 2, J1_PIN2[1]))

power_symbol("+5V", (83.82, 57.15), 270)
wire((83.82, 57.15), J1_PIN3)
power_symbol("GND", (83.82, 59.69), 90)
wire((83.82, 59.69), J1_PIN4)

# ---------------------------------------------------------------------------
# Pico power: VSYS<-+5V (from J1 via global +5V net), 3V3(out)->+3.3V,
# a GND near the right column.
# ---------------------------------------------------------------------------
power_symbol("+5V", (177.8, 54.61), 270)
wire((PICO_RIGHT_X, 54.61), (177.8, 54.61))
# 2026-09-27: GND is taken from pin 28 (power_in), NOT pin 38. The third-party
# RPi_Pico symbol declares pin 38 as "bidirectional", which would give a
# pin_to_pin ERC conflict against the PWR_FLAG (power_out) on the GND net.
GND_PIN28_Y = 82.55
power_symbol("GND", (177.8, GND_PIN28_Y), 90)
wire((PICO_RIGHT_X, GND_PIN28_Y), (177.8, GND_PIN28_Y))
power_symbol("+3.3V", (177.8, 62.23), 270)
wire((PICO_RIGHT_X, 62.23), (177.8, 62.23))

print("part A (Pico+J1+power) done, body_parts so far:", len(body_parts))

# ---------------------------------------------------------------------------
# J2: OLED connector (Conn_01x04), 2026-09-27(2) TFT->OLED change (hub
# decision, "再現の方針"): 0.96in 128x64 SSD1315 OLED, Akizuki #112031, I2C0
# on GP8(SDA)/GP9(SCL) (hub-assigned pins, same convention as the maze module).
# Reuses the SAME Connector_Generic:Conn_01x04 symbol J1 already pulls in from
# keypad.kicad_sch's lib_symbols - no new symbol needed (see gen_sch.py).
# Placed so pin1/pin2 land exactly on GP8/GP9's Y (direct wires, no jog),
# exactly like J1 does for GP0/GP1.
# ---------------------------------------------------------------------------
J2_X, J2_Y = 99.06, 80.01
component(
    "Connector_Generic:Conn_01x04", "J2", "OLED_LOCAL_I2C",
    "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "Local wiring to the 0.96in SSD1315 OLED breakout (Akizuki #112031, 580 yen), I2C0 bus. "
    "Pin1=SDA(GP8), Pin2=SCL(GP9), Pin3=GND, Pin4=+3.3V (from Pico 3V3 OUT). Internal pull-ups "
    "are not required (hub confirmed empirically: the breakout has its own onboard pull-ups), "
    "but the firmware side may still enable Pico's weak internal pull-ups for robustness. "
    "Breakout's own header pin order (often GND,VCC,SCL,SDA) may differ from this connector's "
    "order; match by hand when the physical board arrives (same open item as the password module).",
    (J2_X, J2_Y), 0, ["1", "2", "3", "4"],
)
J2_PIN1 = (J2_X - 5.08, J2_Y - 2.54)     # (93.98, 77.47) -> GP8 (SDA)
J2_PIN2 = (J2_X - 5.08, J2_Y - 0)        # (93.98, 80.01) -> GP9 (SCL)
J2_PIN3 = (J2_X - 5.08, J2_Y - (-2.54))  # (93.98, 82.55) -> GND
J2_PIN4 = (J2_X - 5.08, J2_Y - (-5.08))  # (93.98, 85.09) -> +3.3V

wire(J2_PIN1, (pico_pins_used["GP8"][1], pico_pins_used["GP8"][2]))
wire(J2_PIN2, (pico_pins_used["GP9"][1], pico_pins_used["GP9"][2]))
label("OLED_SDA_GP8", (J2_PIN1[0] + 2, J2_PIN1[1]))
label("OLED_SCL_GP9", (J2_PIN2[0] + 2, J2_PIN2[1]))

power_symbol("GND", (83.82, J2_PIN3[1]), 90)
wire((83.82, J2_PIN3[1]), J2_PIN3)
power_symbol("+3.3V", (83.82, J2_PIN4[1]), 270)
wire((83.82, J2_PIN4[1]), J2_PIN4)

print("part B (J2 OLED) done, body_parts so far:", len(body_parts))

# ---------------------------------------------------------------------------
# SW1-SW6: 6 tactile switches (2 col x 3 row: TL/TR/ML/MR/BL/BR), matching
# keypad.kicad_sch's proven pattern: pin1(near,-5.08)->GND, pin2(far,+5.08)->
# direct wire to Pico GPIO pin (same Y, no jog).
# 2026-09-27(2): moved from GP8-13 to GP2-7 (freed by the TFT->OLED change,
# which moved the display to GP8/GP9 I2C0). Footprint changed 6mm->12mm: the
# 6mm+custom-elongated-cap hack existed only to match the switch row pitch to
# the TFT's on-screen label rows (old design notes §1.4); since the button
# words are now fixed printed caps (not on-screen text), that constraint is
# gone and standard 12mm tact + standard cap is simpler/cheaper to source
# (see design notes §1/§3 for the updated 80mm layout/BOM).
# ---------------------------------------------------------------------------
SW_X = 120.65
switches = [
    ("SW1", "TL", "GP2", 59.69),
    ("SW2", "TR", "GP3", 62.23),
    ("SW3", "ML", "GP4", 64.77),
    ("SW4", "MR", "GP5", 67.31),
    ("SW5", "BL", "GP6", 72.39),
    ("SW6", "BR", "GP7", 74.93),
]
for ref, pos_name, gp_name, y in switches:
    component(
        "Switch:SW_Push", ref, "SW_Push",
        "Button_Switch_THT:SW_PUSH-12mm",
        f"Answer button, position {pos_name}: 12mm tact switch (Akizuki TVGP01-G73BB) with a printed, fixed word-label cap (word fixed permanently per hub decision 2026-09-27(2) - the button word is no longer regenerated per stage). {gp_name}, internal pull-up (firmware), other leg to GND per keypad-proven wiring (opposite-edge pins of the 4-leg tact switch).",
        (SW_X, y), 0, ["1", "2"],
    )
    pin1 = (SW_X - 5.08, y)
    pin2 = (SW_X + 5.08, y)
    power_symbol("GND", (105.41, y), 270)
    wire((105.41, y), pin1)
    wire(pin2, (PICO_LEFT_X, y))
    label(f"SW_{gp_name}", (pin2[0] + 0.5, y))

print("part C (switches) done, body_parts so far:", len(body_parts))

# ---------------------------------------------------------------------------
# LED+R groups: GPIO -> R(pin1) -> [R body] -> R(pin2) -> [gap wire] ->
# LED(anode) -> [LED body] -> LED(cathode) -> [wire] -> GND.
# Matches keypad.kicad_sch's proven R1/LED1/status-LED pattern exactly
# (R is a vertical Device:R: pin1 local(0,+3.81), pin2 local(0,-3.81), so
# abs pin1_y = R_y - 3.81, abs pin2_y = R_y + 3.81).
# Device:LED: pin1(K) local(-3.81,0), pin2(A) local(+3.81,0) - both pins
# share the LED's own placement Y (angle doesn't change the abs-pos formula).
# ---------------------------------------------------------------------------
def led_group(led_ref, r_ref, value_led, value_r, r_x, gp_target_y, gnd_x, gnd_angle,
              gp_x, description_led, led_fp="LED_THT:LED_D5.0mm"):
    r_y = gp_target_y + 3.81
    r_pin1 = (r_x, gp_target_y)          # = (r_x, r_y - 3.81)
    r_pin2 = (r_x, r_y + 3.81)           # = (r_x, gp_target_y + 7.62)
    gap_y = r_pin2[1] + 2.54             # anode lands 2.54 further out
    led_anode = (r_x, gap_y)
    led_x = r_x - 3.81
    led_y = gap_y
    led_cathode = (led_x - 3.81, led_y)

    component(
        "Device:R", r_ref, value_r,
        "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
        f"Current-limiting resistor for {led_ref}",
        (r_x, r_y), 0, ["1", "2"],
    )
    component(
        "Device:LED", led_ref, value_led, led_fp,
        description_led,
        (led_x, led_y), 0, ["1", "2"],
    )
    wire((gp_x, gp_target_y), r_pin1)
    wire(r_pin2, led_anode)
    wire((gnd_x, led_cathode[1]), led_cathode)
    power_symbol("GND", (gnd_x, led_cathode[1]), gnd_angle)
    return led_cathode

# Stage progress LEDs (red, 330 ohm, OSR5JA5E34B - same part as maze module)
led_group("LED1", "R1", "LED (stage 1, red, OSR5JA5E34B)", "330",
           125.73, pico_pins_used["GP14"][2], 106.68, 270, PICO_LEFT_X,
           "Stage-progress LED 1/3 (red). Lit once stage 1 is cleared.")
led_group("LED2", "R2", "LED (stage 2, red, OSR5JA5E34B)", "330",
           110.49, pico_pins_used["GP15"][2], 91.44, 270, PICO_LEFT_X,
           "Stage-progress LED 2/3 (red). Lit once stage 2 is cleared.")
led_group("LED3", "R3", "LED (stage 3, red, OSR5JA5E34B)", "330",
           180.34, pico_pins_used["GP16"][2], 160.02, 90, PICO_RIGHT_X,
           "Stage-progress LED 3/3 (red). Lit once stage 3 is cleared (=solved).")
# Status LED: green, 47 ohm, OSG58A3131A - common spec across all modules
led_group("LED4", "R4", "LED (status, green, OSG58A3131A)", "47",
           190.5, pico_pins_used["GP17"][2], 161.29, 90, PICO_RIGHT_X,
           "Module status LED (green = solved, per manual p.4 / OSC2026 common spec). Panel placement: top-right corner, inset from the corner screw hole.", led_fp="LED_THT:LED_D3.0mm")

print("part D (LEDs) done, body_parts so far:", len(body_parts))

# ---------------------------------------------------------------------------
# 2026-09-27 (hub common rules): (1) 100uF/16V bulk capacitor across the 5V
# input, (2) PWR_FLAG on every supply net, (3) no_connect on every unused pin,
# (4) note documenting J2's pin order (the library symbol stays verbatim).
# ---------------------------------------------------------------------------
# (1) C1: same part/footprint as the simon module (Rubycon 16PX100MEFC5X11, phi5x11, 2.0mm lead pitch).
# Device:C_Polarized pins: 1(+) local (0,+3.81), 2(-) local (0,-3.81).
C1_X, C1_Y = 76.2, 58.42
component(
    "Device:C_Polarized", "C1", "100u/16V",
    "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
    "Bulk capacitor on the 5V input (JST XH Pin3-Pin4 area), OSC2026 common rule 2026-09-27: 100uF/16V or more, long lead = +. Rubycon 16PX100MEFC5X11 (Akizuki g110271, 10 yen).",
    (C1_X, C1_Y), 0, ["1", "2"],
)
C1_PLUS = (C1_X, C1_Y - 3.81)    # (76.2, 54.61)
C1_MINUS = (C1_X, C1_Y + 3.81)   # (76.2, 62.23)
power_symbol("+5V", (68.58, C1_PLUS[1]), 270)
wire((68.58, C1_PLUS[1]), C1_PLUS)
power_symbol("GND", (68.58, C1_MINUS[1]), 90)
wire((68.58, C1_MINUS[1]), C1_MINUS)

# (2) One PWR_FLAG per supply net, placed offset from the power symbol and joined
# by a wire (junction at the symbol pin, as in the Morse/host schematics).
for net_y, x_flag in ((54.61, 185.42), (GND_PIN28_Y, 185.42), (62.23, 185.42)):
    junction((177.8, net_y))
    wire((177.8, net_y), (x_flag, net_y))
    pwr_flag((x_flag, net_y))

# (3) no_connect on every unused Pico pin (26 pins).
# 2026-09-27(2): GP10-13 (pins 14-17) joined this list - the TFT->OLED change
# moved the 6 buttons from GP8-13 to GP2-7 (freed by dropping TFT's SPI bus),
# so GP10-13 are spare now. Found via kicad-cli erc (4 new pin_not_connected).
nc_pins = [
    # left column (x=132.08): GND pins 3, 8, 13, 18
    (PICO_LEFT_X, 57.15), (PICO_LEFT_X, 69.85), (PICO_LEFT_X, 82.55), (PICO_LEFT_X, 95.25),
    # left column: GP10-13 (pins 14-17), spare since the 2026-09-27(2) button move
    (PICO_LEFT_X, 85.09), (PICO_LEFT_X, 87.63), (PICO_LEFT_X, 90.17), (PICO_LEFT_X, 92.71),
    # right column (x=167.64): 23 GND, 24-27 GPIO18-21, 29 GPIO22, 30 RUN, 31/32 GPIO26/27,
    # 33 AGND, 34 GPIO28, 35 ADC_VREF, 37 3V3_EN, 38 GND (bidirectional in this symbol), 40 VBUS
    (PICO_RIGHT_X, 95.25), (PICO_RIGHT_X, 92.71), (PICO_RIGHT_X, 90.17), (PICO_RIGHT_X, 87.63),
    (PICO_RIGHT_X, 85.09), (PICO_RIGHT_X, 80.01), (PICO_RIGHT_X, 77.47), (PICO_RIGHT_X, 74.93),
    (PICO_RIGHT_X, 72.39), (PICO_RIGHT_X, 69.85), (PICO_RIGHT_X, 67.31), (PICO_RIGHT_X, 64.77),
    (PICO_RIGHT_X, 59.69), (PICO_RIGHT_X, 57.15), (PICO_RIGHT_X, 52.07),
    # bottom debug pins: 41 SWCLK, 42 GND, 43 SWDIO
    (PICO_X - 2.54, 105.41), (PICO_X, 105.41), (PICO_X + 2.54, 105.41),
]
assert len(nc_pins) == 26
for p in nc_pins:
    no_connect(p)

# (4) J2 pin-order note (2026-09-27(2): TFT->OLED change)
note("J2 = local wiring to 0.96in SSD1315 OLED breakout (Akizuki 112031), I2C0.", (12.7, 83.82))
note("Pin1=SDA(GP8), Pin2=SCL(GP9), Pin3=GND, Pin4=+3.3V (Pico 3V3 OUT).", (12.7, 86.36))
note("Breakout's own header order (often GND,VCC,SCL,SDA) may differ - match by hand.", (12.7, 88.9))

print("part E (C1, PWR_FLAG, no_connect, note) done, body_parts so far:", len(body_parts))

# ---------------------------------------------------------------------------
# Final assembly
# ---------------------------------------------------------------------------
header = f'''(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A4")
\t(title_block
\t\t(title "Who's on First module")
\t\t(comment 1 "OSC2026 bomb defusal prop - Who's on First module")
\t\t(comment 2 "2026-09-27(2): TFT->0.96in OLED(SSD1315,I2C0 GP8/9), buttons->GP2-7, hub decision (再現の方針)")
\t)
'''

footer = f'''\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''

full = header + lib_symbols_block + "".join(body_parts) + footer

import os
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(full)

print("WROTE", OUT_PATH, "total chars:", len(full))





