# -*- coding: utf-8 -*-
"""Generate hardware/timer/timer.kicad_pcb: 80x80mm, TWO Pico 2 (timer U1 + host U3), dual-sided
placement. Placement only - no routing."""
import uuid, os

def u():
    return str(uuid.uuid4())

OUT_DIR = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\timer"

# ---------------------------------------------------------------------------
# Confirmed front-panel layout (mm, board origin = panel top-left = (0,0)):
#   - digit row: 4x A-801SR, 19.9mm wide, 27.5mm tall, y=41.75..69.25
#   - colon: 2 small LEDs stacked in the 6mm gap between digit 2 and 3
#   - strike LEDs: 2x, centered above the colon, y=30.75..38.75
#   - whole display block (LEDs+digits) is vertically centered in the 100mm
#     board; margins left/right on the digit row are ~3.2mm each side
# ---------------------------------------------------------------------------
BOARD = 80.0
DIGIT_W, DIGIT_H = 12.7, 19.0     # A-551SRD body
GAP = 1.5
COLON_W = 6.0
ROW_W = 4 * DIGIT_W + 2 * GAP + 2 * GAP + COLON_W  # 62.8
X0 = (BOARD - ROW_W) / 2                            # 8.6
D1_X = X0
D2_X = D1_X + DIGIT_W + GAP
COLON_X = D2_X + DIGIT_W + GAP
D3_X = COLON_X + COLON_W + GAP
D4_X = D3_X + DIGIT_W + GAP
DIGIT_Y = 16.0                                      # variant B: display block toward the top

STRIKE_Y = 10.0
STRIKE_X1, STRIKE_X2 = 35.0, 45.0
COLON_CX = COLON_X + COLON_W / 2
COLON_CY1 = DIGIT_Y + DIGIT_H / 3
COLON_CY2 = DIGIT_Y + DIGIT_H * 2 / 3

print("digit x:", D1_X, D2_X, D3_X, D4_X, "colon x", COLON_X, "row width", ROW_W)

# ---------------------------------------------------------------------------
# Net list (name -> code), reusing exactly what the schematic/netlist verified
# ---------------------------------------------------------------------------
NETS_INTERNAL = ["GND", "+5V", "+3.3V", "+3V3_H", "TM_CLK", "TM_DIO",
        "SDA", "SCL", "S1_TX", "S1_RX", "S2_TX", "S2_RX", "S3_TX", "S3_RX", "S4_TX", "S4_RX", "S5_TX", "S5_RX",
        "M_TX", "M_RX", "VCC_J1", "VCC_J2", "VCC_J3", "VCC_J4", "VCC_J5",
        "SHARED_ODDEVEN", "SHARED_VOWEL",
        "SEG_A", "SEG_B", "SEG_C", "SEG_D", "SEG_E", "SEG_F", "SEG_G", "SEG_DP",
        "GRID_D1", "GRID_D2", "GRID_D3", "GRID_D4", "GRID_COLON1", "GRID_COLON2",
        "STRIKE1", "STRIKE1_LED", "STRIKE2", "STRIKE2_LED"]

def N(n):
    """schematic net name as KiCad exports it: labels get a leading '/', power nets do not"""
    if not n:
        return None
    if n.startswith("unconnected-"):
        return n
    return n if n in ("GND", "+5V", "+3.3V") else "/" + n

NETS = [""] + [N(x) for x in NETS_INTERNAL]
NET_CODE = {name: i for i, name in enumerate(NETS)}

def net(name):
    return NET_CODE[name]

def pad_net(name):
    if not name:
        return ""
    if name not in NET_CODE:       # single-pad "unconnected-(...)" nets are registered on first use
        NET_CODE[name] = len(NETS)
        NETS.append(name)
    return f' (net {net(name)} "{name}")'

OUT = []

def emit(s):
    OUT.append(s)


def emit_fp_circle(cx, cy, r, layer, width):
    emit(f'\t\t(fp_circle\n\t\t\t(center {cx} {cy}) (end {cx + r} {cy})\n'
         f'\t\t\t(stroke (width {width}) (type solid)) (fill none) (layer "{layer}")\n\t\t\t(uuid "{u()}")\n\t\t)\n')

A551SRD_PADS = [("1", "rect", 0.0, 0.0), ("2", "circle", 2.54, 0.0), ("3", "circle", 5.08, 0.0),
                ("4", "circle", 7.62, 0.0), ("5", "circle", 10.16, 0.0),
                ("10", "circle", 0.0, -15.24), ("9", "circle", 2.54, -15.24), ("8", "circle", 5.08, -15.24),
                ("7", "circle", 7.62, -15.24), ("6", "circle", 10.16, -15.24)]
PICO_NAMES = {
    1: "GPIO0", 2: "GPIO1", 3: "GND", 4: "GPIO2", 5: "GPIO3", 6: "GPIO4", 7: "GPIO5", 8: "GND", 9: "GPIO6",
    10: "GPIO7", 11: "GPIO8", 12: "GPIO9", 13: "GND", 14: "GPIO10", 15: "GPIO11", 16: "GPIO12", 17: "GPIO13",
    18: "GND", 19: "GPIO14", 20: "GPIO15", 21: "GPIO16", 22: "GPIO17", 23: "GND", 24: "GPIO18", 25: "GPIO19",
    26: "GPIO20", 27: "GPIO21", 28: "GND", 29: "GPIO22", 30: "RUN", 31: "GPIO26_ADC0", 32: "GPIO27_ADC1",
    33: "AGND", 34: "GPIO28_ADC2", 35: "ADC_VREF", 36: "3V3", 37: "3V3_EN", 38: "GND", 39: "VSYS", 40: "VBUS",
}
TM1637_PAD_NET = {
    "1": "GND", "2": "SEG_A", "3": "SEG_B", "4": "SEG_C", "5": "SEG_D", "6": "SEG_E",
    "7": "SEG_F", "8": "SEG_G", "9": "SEG_DP", "10": "GRID_COLON2", "11": "GRID_COLON1",
    "12": "GRID_D4", "13": "GRID_D3", "14": "GRID_D2", "15": "GRID_D1", "16": "+5V",
    "17": "TM_DIO", "18": "TM_CLK", "19": None, "20": None,
}

# ---------------------------------------------------------------------------
# 2026-09-29 (user: "絶対に8cm角に収める、pico二枚載せたうえで"): TWO Pico 2 (U1 = timer/master,
# U3 = host/communication) + everything else on ONE 80x80mm board. Strategy (dual-sided):
#   FRONT (F.Cu): display block (DS1-4, colon D1/D2, strike LEDs D3/D4) on top, both Picos
#                 (Pico H = male pin headers, so each module sits ~2.5mm above the board) below.
#   BACK  (B.Cu): all the other through-hole parts (J1-J5/J7/J8 JST XH, F1-F5 polyfuses, U2 TM1637,
#                 C1-C3, JP1, R1-R4), placed between the Picos' header-hole rows and behind the
#                 top band. Their lead ends come through to the front UNDER the Pico modules, which
#                 is why the Picos must be header-mounted (>= 2.5mm gap), not castellated-flat.
#   Back parts avoid the digit band (y 15..36): the digit bodies sit on the front there.
# All pad coordinates below are already in BOARD orientation (rotation/mirroring for back-side
# parts is applied here), so every footprint is emitted at angle 0.
# ---------------------------------------------------------------------------
def emit_fp(lib, ref, value, x, y, side, pads, crt, silks=(), circles=()):
    """pads: (num, shape, dx, dy, size, drill, net); crt: (x0,y0,x1,y1) relative to (x,y)."""
    cu, sk, ct, fb = ("F.Cu", "F.SilkS", "F.CrtYd", "F.Fab") if side == "F" else ("B.Cu", "B.SilkS", "B.CrtYd", "B.Fab")
    mir = "" if side == "F" else " (justify mirror)"
    emit(f'\t(footprint "{lib}"\n\t\t(layer "{cu}")\n\t\t(uuid "{u()}")\n\t\t(at {x} {y} 0)\n\t\t(attr through_hole)\n')
    emit(f'\t\t(property "Reference" "{ref}"\n\t\t\t(at 0 -3 0)\n\t\t\t(layer "{sk}")\n'
         f'\t\t\t(uuid "{u()}")\n\t\t\t(effects (font (size 1 1) (thickness 0.15)){mir})\n\t\t)\n')
    emit(f'\t\t(property "Value" "{value}"\n\t\t\t(at 0 3 0)\n\t\t\t(layer "{fb}")\n'
         f'\t\t\t(uuid "{u()}")\n\t\t\t(effects (font (size 1 1) (thickness 0.15)){mir})\n\t\t)\n')
    for (num, shape, dx, dy, size, drill, nt) in pads:
        emit(f'\t\t(pad "{num}" thru_hole {shape}\n\t\t\t(at {round(dx, 4)} {round(dy, 4)})\n\t\t\t(size {size} {size})\n'
             f'\t\t\t(drill {drill})\n\t\t\t(layers "*.Cu" "*.Mask")\n\t\t\t(remove_unused_layers no)'
             f'{pad_net(N(nt))}\n\t\t\t(uuid "{u()}")\n\t\t)\n')
    for (x0, y0, x1, y1) in silks:
        emit(f'\t\t(fp_rect\n\t\t\t(start {x0} {y0}) (end {x1} {y1})\n'
             f'\t\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "{sk}")\n\t\t\t(uuid "{u()}")\n\t\t)\n')
    for (cx, cy, r) in circles:
        emit(f'\t\t(fp_circle\n\t\t\t(center {cx} {cy}) (end {cx + r} {cy})\n'
             f'\t\t\t(stroke (width 0.12) (type solid)) (fill none) (layer "{sk}")\n\t\t\t(uuid "{u()}")\n\t\t)\n')
    rects = [crt] if not isinstance(crt[0], (tuple, list)) else list(crt)
    for (x0, y0, x1, y1) in rects:
        emit(f'\t\t(fp_rect\n\t\t\t(start {x0} {y0}) (end {x1} {y1})\n'
             f'\t\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "{ct}")\n\t\t\t(uuid "{u()}")\n\t\t)\n')
    emit('\t)\n')

def mounting_hole(ref, x, y, dia=2.6):
    emit(f'\t(footprint "MountingHole:MountingHole_2.6mm"\n\t\t(layer "F.Cu")\n\t\t(uuid "{u()}")\n\t\t(at {x} {y} 0)\n\t\t(attr through_hole)\n')
    emit(f'\t\t(property "Reference" "{ref}"\n\t\t\t(at 0 -3 0)\n\t\t\t(layer "F.SilkS")\n\t\t\t(uuid "{u()}")\n\t\t\t(effects (font (size 1 1) (thickness 0.15)))\n\t\t)\n')
    emit(f'\t\t(property "Value" "M2.6 hole (dia {dia}mm)"\n\t\t\t(at 0 3 0)\n\t\t\t(layer "F.Fab")\n\t\t\t(uuid "{u()}")\n\t\t\t(effects (font (size 1 1) (thickness 0.15)))\n\t\t)\n')
    emit(f'\t\t(pad "" np_thru_hole circle\n\t\t\t(at 0 0)\n\t\t\t(size {dia} {dia})\n\t\t\t(drill {dia})\n\t\t\t(layers "*.Mask")\n\t\t\t(uuid "{u()}")\n\t\t)\n')
    emit_fp_circle(0, 0, dia / 2 + 0.15, "F.SilkS", 0.12)
    r = dia / 2 + 0.25
    emit(f'\t\t(fp_rect\n\t\t\t(start {-r} {-r}) (end {r} {r})\n\t\t\t(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd")\n\t\t\t(uuid "{u()}")\n\t\t)\n')
    emit('\t)\n')

# ---- part builders (board-orientation pad lists) ----
def row_pads(n, pitch, nets, size, drill, x0=0.0, y0=0.0):
    return [(str(i + 1), "rect" if i == 0 else "circle", x0 + i * pitch, y0, size, drill, nets[i]) for i in range(n)]

def place_digit(ref, x, y, com, segs):
    ox, oy = x + 1.27, y + 17.12
    seg_net = dict(zip(["7", "6", "4", "2", "1", "9", "10", "5"], segs))
    pads = [(num, shape, dx, dy, 1.6, 1.0, com if num in ("3", "8") else seg_net[num]) for num, shape, dx, dy in A551SRD_PADS]
    emit_fp("Timer_Local:A-551SRD", ref, "A-551SRD", ox, oy, "F", pads, (-1.52, -17.37, 11.68, 2.13), [(-1.27, -17.12, 11.43, 1.88)])

def place_led(ref, x, y, k_net, a_net, dia=5.0, vertical=False):
    s, d = (1.8, 1.0) if dia == 5.0 else (1.5, 0.9)
    if vertical:
        pads = [("1", "rect", 0, 1.27, s, d, k_net), ("2", "circle", 0, -1.27, s, d, a_net)]
    else:
        pads = [("1", "rect", -1.27, 0, s, d, k_net), ("2", "circle", 1.27, 0, s, d, a_net)]
    h = dia / 2 + 0.25
    emit_fp("LED_THT:LED_D5.0mm" if dia == 5.0 else "LED_THT:LED_D3.0mm", ref, "LED", x, y, "F", pads,
            (-(h + 0.25), -(h + 0.25), h + 0.25, h + 0.25), [(-h, -h, h, h)])

def place_pico(ref, cx, cy, nets):
    """Pico 2 H on the FRONT (module + pin headers), USB end toward -X. All 40 header holes
    (2.54 pitch, rows 17.78 apart). Rotated 'USB-left': pin n<=20 on the +y row (x = -24.13+2.54(n-1)),
    pin n>=21 on the -y row (x = 24.13-2.54(n-21))."""
    pads = []
    for n in range(1, 41):
        if n <= 20:
            dx, dy = -24.13 + 2.54 * (n - 1), 8.89
        else:
            dx, dy = 24.13 - 2.54 * (n - 21), -8.89
        nt = nets.get(n) or f"unconnected-({ref}-{PICO_NAMES[n]}-Pad{n})"   # KiCad's name for a no_connect pin
        pads.append((str(n), "rect" if n == 1 else "circle", dx, dy, 1.7, 1.0, nt))
    # Courtyard = the two pin-header strips only: the module body floats ~2.5mm above the board on
    # the header plastic, so through-hole lead ends of the BACK-side parts may sit under it. The
    # module outline (21 x 51mm) is drawn on the silkscreen only.
    emit_fp("RPi_Pico:RPi_Pico_SMD_TH", ref, "Pico 2 H (header-mounted, 2.5mm standoff)", cx, cy, "F", pads,
            [(-25.8, 8.89 - 1.6, 25.8, 8.89 + 1.6), (-25.8, -8.89 - 1.6, 25.8, -8.89 + 1.6)],
            [(-25.5, -10.5, 25.5, 10.5)])

def place_conn(ref, value, x, y, nets):
    n = len(nets)
    pads = row_pads(n, 2.5, nets, 1.7, 1.0)
    emit_fp(f"Connector_JST:JST_XH_B{n}B-XH-A_1x0{n}_P2.50mm_Vertical", ref, value, x, y, "B", pads,
            (-2.75, -3.0, (n - 1) * 2.5 + 2.75, 3.0), [(-2.5, -2.9, (n - 1) * 2.5 + 2.5, 2.9)])

def place_fuse(ref, x, y, p1, p2):
    pads = [("1", "rect", 0, 0, 1.7, 1.0, p1), ("2", "circle", 5.1, 0, 1.7, 1.0, p2)]
    emit_fp("Fuse_THT:Fuse_Radial_MF-RX030_P5.10mm", ref, "MF-RX030/72-0 (upright)", x, y, "B", pads,
            (-1.6, -2.2, 6.7, 2.2), [(-1.2, -1.7, 6.3, 1.7)])

def place_r(ref, x, y, p1, p2, value):
    pads = [("1", "rect", -5.08, 0, 1.7, 0.9, p1), ("2", "circle", 5.08, 0, 1.7, 0.9, p2)]
    emit_fp("Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", ref, value, x, y, "B", pads,
            (-5.7, -1.7, 5.7, 1.7), [(-3.15, -1.25, 3.15, 1.25)])

def place_cap(ref, x, y, value, pitch, p1, p2, body):
    pads = [("1", "rect", 0, 0, 1.7, 0.9, p1), ("2", "circle", pitch, 0, 1.7, 0.9, p2)]
    emit_fp("Capacitor_THT:C_generic", ref, value, x, y, "B", pads,
            (-body - 0.3, -body - 0.3, pitch + body + 0.3, body + 0.3), [(-0.6, -body, pitch + 0.6, body)])

def place_jp(ref, x, y, nets):
    pads = [(str(i + 1), "rect" if i == 0 else "circle", 0, i * 2.54, 1.7, 1.0, nets[i]) for i in range(3)]
    emit_fp("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", ref, "TM1637_VDD_SEL", x, y, "B", pads,
            (-1.77, -1.77, 1.77, 2 * 2.54 + 1.77), [(-1.27, -1.27, 1.27, 2 * 2.54 + 1.27)])

def place_tm1637(ref, cx, cy):
    """DIP-20 on the BACK, long axis along X. Natural (top-of-IC) view: pins 1-10 left column
    top->bottom, 11-20 right column bottom->top. Seen from the back that is mirrored in X; then
    rotated so the long axis is horizontal: (x,y) -> (y,-x)."""
    pads = []
    for n in range(1, 21):
        if n <= 10:
            nx, ny = -3.81, -11.43 + 2.54 * (n - 1)
        else:
            nx, ny = 3.81, 11.43 - 2.54 * (n - 11)
        mx, my = -nx, ny            # back-side mirror
        dx, dy = my, -mx            # rotate to horizontal
        nt = TM1637_PAD_NET[str(n)] or f"unconnected-({ref}-K{n - 18}-Pad{n})"   # pins 19/20 = K1/K2
        pads.append((str(n), "rect" if n == 1 else "circle", dx, dy, 1.6, 1.0, nt))
    emit_fp("Timer_Local:TM1637", ref, "TM1637", cx, cy, "B", pads, (-13.0, -5.2, 13.0, 5.2), [(-12.7, -4.9, 12.7, 4.9)])

# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------
SEGS = ["SEG_A", "SEG_B", "SEG_C", "SEG_D", "SEG_E", "SEG_F", "SEG_G", "SEG_DP"]
place_digit("DS1", D1_X, DIGIT_Y, "GRID_D1", SEGS)
place_digit("DS2", D2_X, DIGIT_Y, "GRID_D2", SEGS)
place_digit("DS3", D3_X, DIGIT_Y, "GRID_D3", SEGS)
place_digit("DS4", D4_X, DIGIT_Y, "GRID_D4", SEGS)
place_led("D1", COLON_CX, COLON_CY1, "SEG_A", "GRID_COLON1", dia=3.0, vertical=True)
place_led("D2", COLON_CX, COLON_CY2, "SEG_A", "GRID_COLON2", dia=3.0, vertical=True)
place_led("D3", STRIKE_X1, STRIKE_Y, "GND", "STRIKE1_LED")
place_led("D4", STRIKE_X2, STRIKE_Y, "GND", "STRIKE2_LED")

PICO_X = 40.0
PICO_A_Y, PICO_B_Y = 46.5, 68.4      # rows at y-8.89 / y+8.89 -> A 37.61/55.39, B 59.51/77.29
U1_NETS = {1: "M_RX", 2: "M_TX", 3: "GND", 4: "TM_CLK", 5: "TM_DIO", 6: "STRIKE1", 7: "STRIKE2", 8: "GND",
           13: "GND", 18: "GND", 23: "GND", 28: "GND", 33: "GND", 36: "+3.3V", 38: "GND", 39: "+5V"}
U3_NETS = {1: "SDA", 2: "SCL", 3: "GND", 4: "SHARED_ODDEVEN", 5: "SHARED_VOWEL",
           8: "GND", 11: "S1_TX", 12: "S1_RX",
           13: "GND", 14: "S3_TX", 15: "S3_RX", 16: "S2_TX", 17: "S2_RX", 18: "GND", 19: "S4_TX", 20: "S4_RX",
           21: "S5_TX", 22: "S5_RX", 23: "GND", 24: "M_TX", 25: "M_RX", 28: "GND", 33: "GND",
           36: "+3V3_H", 38: "GND", 39: "+5V"}
place_pico("U1", PICO_X, PICO_A_Y, U1_NETS)
place_pico("U3", PICO_X, PICO_B_Y, U3_NETS)

# --- BACK side ---
# strike-LED resistors: back top band (x 12..68 keeps their pads out of the corner keep-outs)
place_r("R1", 22.0, 5.0, "STRIKE1", "STRIKE1_LED", "330")
place_r("R2", 58.0, 5.0, "STRIKE2", "STRIKE2_LED", "330")
# between Pico A's header rows (y 37.6 .. 55.4): J1-J5 (row a), J8 + J7 + pullups (row b)
YA, YB = 43.5, 50.0
for k in range(5):
    n = k + 1
    place_conn(f"J{n}", f"MODULE_SLOT_{n}", 4.0 + 15.0 * k, YA, [f"S{n}_RX", f"S{n}_TX", f"VCC_J{n}", "GND"])
# 2026-09-30 (user): J8 shrunk 7 -> 3 pins (GND, SHARED_ODDEVEN, SHARED_VOWEL); row b is ~10mm freer
place_conn("J8", "SHARED_WIDGET_GPIO", 4.0, YB, ["GND", "SHARED_ODDEVEN", "SHARED_VOWEL"])
place_conn("J7", "SHARED_WIDGET_I2C_TAP", 18.0, YB, ["SDA", "SCL", "+3V3_H", "GND"])
place_r("R3", 38.0, YB, "+3V3_H", "SDA", "4.7k")
place_r("R4", 54.0, YB, "+3V3_H", "SCL", "4.7k")
# between Pico B's header rows (y 59.5 .. 77.3): F1-F5 (upright), TM1637, C1-C3, JP1
for k in range(5):
    n = k + 1
    place_fuse(f"F{n}", 4.0 + 15.0 * k, 63.2, "+5V", f"VCC_J{n}")
place_tm1637("U2", 27.0, 71.0)
place_cap("C3", 44.5, 71.0, "470uF", 2.5, "+5V", "GND", 3.2)
place_cap("C1", 53.0, 71.0, "100nF", 2.5, "+5V", "GND", 1.6)
place_cap("C2", 60.4, 71.0, "100uF", 2.0, "+5V", "GND", 2.0)
# 2026-09-30 (user): TM1637 supply fixed at +5V - JP1 (3.3V/5V selector) removed

# mounting holes (2026-09-29 hub: dia 2.6mm, 9mm inset, 62mm pitch)
HOLE_INSET, HOLE_DIA = 9.0, 2.6
for ref, (hx, hy) in {"H1": (HOLE_INSET, HOLE_INSET), "H2": (BOARD - HOLE_INSET, HOLE_INSET),
                      "H3": (HOLE_INSET, BOARD - HOLE_INSET), "H4": (BOARD - HOLE_INSET, BOARD - HOLE_INSET)}.items():
    mounting_hole(ref, hx, hy, HOLE_DIA)

body = "".join(OUT)

# ---------------------------------------------------------------------------
# Board outline + full file assembly
# ---------------------------------------------------------------------------
board_uuid = u()
net_decls = "\n".join(f'\t(net {i} "{name}")' for i, name in enumerate(NETS))

header = f'''(kicad_pcb
\t(version 20260206)
\t(generator "pcbnew")
\t(generator_version "10.0")
\t(general
\t\t(thickness 1.6)
\t\t(legacy_teardrops no)
\t)
\t(paper "A4")
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(2 "B.Cu" signal)
\t\t(9 "F.Adhes" user "F.Adhesive")
\t\t(11 "B.Adhes" user "B.Adhesive")
\t\t(13 "F.Paste" user)
\t\t(15 "B.Paste" user)
\t\t(5 "F.SilkS" user "F.Silkscreen")
\t\t(7 "B.SilkS" user "B.Silkscreen")
\t\t(1 "F.Mask" user)
\t\t(3 "B.Mask" user)
\t\t(17 "Dwgs.User" user "User.Drawings")
\t\t(19 "Cmts.User" user "User.Comments")
\t\t(21 "Eco1.User" user "User.Eco1")
\t\t(23 "Eco2.User" user "User.Eco2")
\t\t(25 "Edge.Cuts" user)
\t\t(27 "Margin" user)
\t\t(31 "F.CrtYd" user "F.Courtyard")
\t\t(29 "B.CrtYd" user "B.Courtyard")
\t\t(35 "F.Fab" user)
\t\t(33 "B.Fab" user)
\t)
\t(setup
\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (color "Green") (thickness 0.01))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (color "Green") (thickness 0.01))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))
\t\t\t(copper_finish "None")
\t\t\t(dielectric_constraints no)
\t\t)
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints no)
\t\t(tenting front back)
\t\t(aux_axis_origin 0 0)
\t\t(grid_origin 0 0)
\t\t(pcbplotparams
\t\t\t(layerselection 0x00000000_00000000_00000000_000000a5)
\t\t\t(plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000)
\t\t\t(disableapertmacros no)
\t\t\t(usegerberextensions no)
\t\t\t(usegerberattributes yes)
\t\t\t(usegerberadvancedattributes yes)
\t\t\t(creategerberjobfile yes)
\t\t\t(dashed_line_dash_ratio 12.000000)
\t\t\t(dashed_line_gap_ratio 3.000000)
\t\t\t(svgprecision 6)
\t\t\t(plotframeref no)
\t\t\t(mode 1)
\t\t\t(useauxorigin no)
\t\t\t(hpglpennumber 1)
\t\t\t(hpglpenspeed 20)
\t\t\t(hpglpendiameter 15.000000)
\t\t\t(pdf_front_fp_property_popups yes)
\t\t\t(pdf_back_fp_property_popups yes)
\t\t\t(pdf_metadata yes)
\t\t\t(pdf_single_document no)
\t\t\t(dxfpolygonmode yes)
\t\t\t(dxfimperialunits yes)
\t\t\t(dxfusepcbnewfont yes)
\t\t\t(psnegative no)
\t\t\t(psa4output no)
\t\t\t(plot_black_and_white yes)
\t\t\t(plotinvisibletext no)
\t\t\t(sketchpadsonfab no)
\t\t\t(plotpadnumbers no)
\t\t\t(hidednponfab no)
\t\t\t(sketchdnponfab yes)
\t\t\t(crossoutdnponfab yes)
\t\t\t(subtractmaskfromsilk no)
\t\t\t(outputformat 1)
\t\t\t(mirror no)
\t\t\t(drillshape 1)
\t\t\t(scaleselection 1)
\t\t\t(outputdirectory "")
\t\t)
\t)
\t(net 0 "")
{net_decls}
'''

TAB = chr(9)
NL = chr(10)
Q = chr(34)
keepouts = ""
for (kx, ky) in [(0, 0), (68, 0), (0, 68), (68, 68)]:
    keepouts += (TAB + "(gr_rect" + NL
                 + TAB + TAB + f"(start {kx} {ky}) (end {kx + 12} {ky + 12})" + NL
                 + TAB + TAB + "(stroke (width 0.1) (type dash)) (fill none) (layer " + Q + "Dwgs.User" + Q + ")" + NL
                 + TAB + TAB + "(uuid " + Q + u() + Q + ")" + NL
                 + TAB + ")" + NL)
board_outline = (TAB + "(gr_rect" + NL
                 + TAB + TAB + f"(start 0 0) (end {BOARD} {BOARD})" + NL
                 + TAB + TAB + "(stroke (width 0.1) (type solid)) (fill none) (layer " + Q + "Edge.Cuts" + Q + ")" + NL
                 + TAB + TAB + "(uuid " + Q + u() + Q + ")" + NL
                 + TAB + ")" + NL
                 + TAB + "(gr_text " + Q + "PROVISIONAL: 80x80mm, two Pico 2 (U1 timer, U3 host), dual-sided: front = display + Picos (pin-header mounted), back = JST/fuses/TM1637/passives; 4x M2.6 holes (9mm inset); dashed 12mm squares = corner keep-out (hub 2026-09-29)" + Q + NL
                 + TAB + TAB + "(at 40 -3 0) (layer " + Q + "Cmts.User" + Q + ")" + NL
                 + TAB + TAB + "(uuid " + Q + u() + Q + ")" + NL
                 + TAB + TAB + "(effects (font (size 1 1) (thickness 0.15)))" + NL
                 + TAB + ")" + NL) + keepouts

footer = ')\n'

full_text = header + board_outline + body + footer

out_path = os.path.join(OUT_DIR, "timer.kicad_pcb")
with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(full_text)
print("WROTE", out_path, len(full_text), "chars")
