"""Generate hardware/wire_sequence/wire_sequence.kicad_sch (Wire Sequence module, 8-wire configuration).

Rules honoured (past pitfalls, see task brief):
  * every coordinate is an integer multiple of 1.27 mm
  * every wire has exactly 2 points
  * lib_symbols sub-unit names carry no 'Library:' prefix (only the top-level symbol name does)
  * absolute pin position = (placement_x + local_x, placement_y - local_y)   # Y-up library, Y-down sheet
  * every part is placed at rotation 0 (so the formula above is all that is needed)
"""
import os, sys, uuid, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kilib import from_std_lib, from_keypad, read_pins

OUT_DIR = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\wire_sequence"
PROJECT = "wire_sequence"
NS = uuid.UUID("6f1f2b8e-5a1c-4c3e-9d0e-2b7f0a5d9c11")
ROOT_UUID = str(uuid.uuid5(NS, "root"))
U = 1.27


def gu(n):
    """grid units -> mm (rounded to 2 decimals, exact multiple of 1.27 up to rounding)"""
    return round(n * U, 2)


def uid(tag):
    return str(uuid.uuid5(NS, tag))


# ------------------------------------------------------------------ library symbols
LIBS = {
    "RPi_Pico:Pico": from_keypad("RPi_Pico:Pico"),
    "Device:R": from_keypad("Device:R"),
    "Device:LED": from_keypad("Device:LED"),
    "Switch:SW_Push": from_keypad("Switch:SW_Push"),
    "Connector_Generic:Conn_01x04": from_keypad("Connector_Generic:Conn_01x04"),
    "power:GND": from_keypad("power:GND"),
    "power:+5V": from_keypad("power:+5V"),
    "power:+3.3V": from_keypad("power:+3.3V"),
    "Connector_Generic:Conn_01x02": from_std_lib("Connector_Generic", "Conn_01x02"),
    "Device:C": from_std_lib("Device", "C"),
    "Device:C_Polarized": from_std_lib("Device", "C_Polarized"),
    "LED:WS2812B": from_std_lib("LED", "WS2812B"),
    "power:PWR_FLAG": from_std_lib("power", "PWR_FLAG"),
    "Device:D": from_std_lib("Device", "D"),
}
PINS = {k: {p["number"]: p for p in read_pins(v)} for k, v in LIBS.items()}

# ------------------------------------------------------------------ output collectors
symbols_out, wires_out, labels_out, nc_out = [], [], [], []
placed = []      # for checks: dict(ref, lib, x, y, pins{num: (x, y)})
wire_recs = []   # for checks: dict(a=(x,y), b=(x,y), net=str)
pwr_counter = [0]
flg_counter = [0]

FONT = "\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n"


def prop(name, value, x, y, hide=False, ang=0):
    v = value.replace("\\", "\\\\").replace('"', '\\"')
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s %s)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            '\t\t\t(effects\n%s\t\t\t)\n\t\t)\n') % (name, v, x, y, ang, "\t\t\t(hide yes)\n" if hide else "", FONT)


def place(lib, ref, value, x, y, footprint="", desc="", in_bom=True, on_board=True, ref_off=(0, -5.08),
          val_off=(0, 5.08)):
    """place a symbol at rotation 0 and return {pin_number: (abs_x, abs_y)}"""
    assert lib in LIBS, lib
    for c in (x, y):
        assert abs(c / U - round(c / U)) < 1e-6, ("off-grid", ref, x, y)
    pins = {}
    for num, p in PINS[lib].items():
        pins[num] = (round(x + p["x"], 2), round(y - p["y"], 2))
    body = "\t(symbol\n\t\t(lib_id \"%s\")\n\t\t(at %s %s 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n" % (lib, x, y)
    body += "\t\t(exclude_from_sim no)\n\t\t(in_bom %s)\n\t\t(on_board %s)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n" % (
        "yes" if in_bom else "no", "yes" if on_board else "no")
    body += "\t\t(fields_autoplaced yes)\n\t\t(uuid \"%s\")\n" % uid("sym-" + ref)
    is_pwr = ref.startswith("#")
    body += prop("Reference", ref, round(x + ref_off[0], 2), round(y + ref_off[1], 2), hide=is_pwr)
    body += prop("Value", value, round(x + val_off[0], 2), round(y + val_off[1], 2))
    body += prop("Footprint", footprint, x, y, hide=True)
    body += prop("Datasheet", "", x, y, hide=True)
    body += prop("Description", desc, x, y, hide=True)
    for num in PINS[lib]:
        body += "\t\t(pin \"%s\"\n\t\t\t(uuid \"%s\")\n\t\t)\n" % (num, uid("pin-%s-%s" % (ref, num)))
    body += ("\t\t(instances\n\t\t\t(project \"%s\"\n\t\t\t\t(path \"/%s\"\n\t\t\t\t\t(reference \"%s\")\n"
             "\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n") % (PROJECT, ROOT_UUID, ref)
    symbols_out.append(body)
    placed.append(dict(ref=ref, lib=lib, x=x, y=y, pins=pins, value=value))
    return pins


def add_wire(a, b, net):
    assert a != b
    for c in (*a, *b):
        assert abs(c / U - round(c / U)) < 1e-6, ("off-grid wire", a, b)
    assert a[0] == b[0] or a[1] == b[1], ("non-orthogonal wire", a, b)
    wires_out.append("\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n"
                     "\t\t)\n\t\t(uuid \"%s\")\n\t)\n" % (a[0], a[1], b[0], b[1], uid("wire-%s-%s-%s-%s-%s" % (a, b, net, len(wires_out), 0))))
    wire_recs.append(dict(a=a, b=b, net=net))


def add_label(name, pos, direction):
    """direction = outward direction of the stub: (dx, dy). Text is laid out away from the wire."""
    dx, dy = direction
    if dx < 0:
        ang, just = 180, "right bottom"
    elif dx > 0:
        ang, just = 0, "left bottom"
    elif dy < 0:
        ang, just = 90, "left bottom"
    else:
        ang, just = 270, "left bottom"
    labels_out.append("\t(label \"%s\"\n\t\t(at %s %s %s)\n\t\t(effects\n%s\t\t\t(justify %s)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n" % (
        name, pos[0], pos[1], ang, FONT, just, uid("label-%s-%s-%s" % (name, pos, len(labels_out)))))


def add_nc(pos):
    nc_out.append("\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid \"%s\")\n\t)\n" % (pos[0], pos[1], uid("nc-%s-%s" % pos)))


def outward(lib, num):
    p = PINS[lib][num]
    a = math.radians(p["angle"] + 180.0)
    dx, dy = round(math.cos(a)), round(-math.sin(a))   # sheet frame (Y down)
    return (dx, dy)


def pwr_symbol(kind, pos, net):
    """place a power symbol whose pin sits exactly at pos."""
    lib = {"GND": "power:GND", "+5V": "power:+5V", "+3V3": "power:+3.3V"}[kind]
    val = {"GND": "GND", "+5V": "+5V", "+3V3": "+3.3V"}[kind]
    pwr_counter[0] += 1
    ref = "#PWR%02d" % pwr_counter[0]
    place(lib, ref, val, pos[0], pos[1], desc='Power symbol creates a global label with name "%s"' % val,
          in_bom=False, on_board=False, ref_off=(0, -5.08), val_off=(0, 3.81))


def flag(pos):
    flg_counter[0] += 1
    ref = "#FLG%02d" % flg_counter[0]
    place("power:PWR_FLAG", ref, "PWR_FLAG", pos[0], pos[1], desc="Power flag: this net is driven by an external source",
          in_bom=False, on_board=False, ref_off=(0, -3.81), val_off=(0, 3.81))


NET_MEMBERS = {}   # net -> list of "ref.pin" (spec-level, used by the verification script)


def connect(ref, lib, pins, num, spec, length=5.08):
    """Stub from a pin to a label / power symbol / no-connect.  spec: ('net', NAME) | 'GND' | '+5V' | '+3V3' | 'nc' """
    pos = pins[num]
    if spec == "nc":
        add_nc(pos)
        NET_MEMBERS.setdefault("<nc>", []).append("%s.%s" % (ref, num))
        return
    d = outward(lib, num)
    end = (round(pos[0] + d[0] * length, 2), round(pos[1] + d[1] * length, 2))
    if isinstance(spec, tuple):
        net = spec[1]
        add_wire(pos, end, net)
        add_label(net, end, d)
    else:
        net = spec
        add_wire(pos, end, net)
        pwr_symbol(spec, end, net)
    NET_MEMBERS.setdefault(net, []).append("%s.%s" % (ref, num))


def island(lib, ref, value, x, y, spec, footprint="", desc="", lengths=None, **kw):
    pins = place(lib, ref, value, x, y, footprint=footprint, desc=desc, **kw)
    for num, s in spec.items():
        connect(ref, lib, pins, num, s, (lengths or {}).get(num, 5.08))
    missing = set(PINS[lib]) - set(spec)
    assert not missing, (ref, "unspecified pins", missing)
    return pins


N = lambda name: ("net", name)

# ------------------------------------------------------------------ Pico (same placement as keypad: easy cross-check)
PICO_X, PICO_Y = 149.86, 76.2
pico_spec = {
    "1": N("UART_TX"), "2": N("UART_RX"), "3": "GND",
    "4": N("W1_IN"), "5": N("W2_IN"), "6": N("W3_IN"), "7": N("W4_IN"),
    "8": "GND",
    "9": N("W5_IN"), "10": N("W6_IN"), "11": N("W7_IN"), "12": N("W8_IN"),
    "13": "GND",
    "14": N("NEO_RAW"), "15": N("STAGE1"), "16": N("STAGE2"), "17": N("STAGE3"),
    "18": "GND",
    "19": N("STAGE4"), "20": N("BTN_UP"),
    "21": N("BTN_DOWN"), "22": N("STATUS"), "23": "GND",
    "24": "nc", "25": "nc", "26": "nc", "27": "nc", "28": "GND",
    "29": "nc", "30": "nc", "31": "nc", "32": "nc", "33": "GND",
    "34": "nc", "35": "nc", "36": "+3V3", "37": "nc", "38": "GND",
    "39": "+5V", "40": "nc",
    "41": "nc", "42": "GND", "43": "nc",
}
pico_pins = island("RPi_Pico:Pico", "U1", "Pico 2", PICO_X, PICO_Y, pico_spec,
                   footprint="RPi_Pico:RPi_Pico_SMD_TH",
                   desc="Raspberry Pi Pico 2 (RP2350). GPIO0/1 = UART0 to host (reserved). JST +5V feeds VSYS; VBUS left open.",
                   ref_off=(0, -31.75), val_off=(0, -29.21))

# ------------------------------------------------------------------ host connector
island("Connector_Generic:Conn_01x04", "J1", "JST_XH_4P_HOST", 254.0, 88.9,
       {"1": N("UART_TX"), "2": N("UART_RX"), "3": "+5V", "4": "GND"},
       footprint="Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
       desc="Host link (common spec): Pin1=GPIO0 UART0 TX (module->host), Pin2=GPIO1 UART0 RX (host->module), Pin3=VCC 5V (host polyfuse; hub recommends a 0.3A-class part, panel budget 200mA average), Pin4=GND",
       lengths={"3": 5.08, "4": 10.16}, ref_off=(2.54, -8.89), val_off=(2.54, 8.89))

# ------------------------------------------------------------------ 8 wire inputs (generic 2-pole terminal per wire)
for i in range(8):
    n = i + 1
    col, row = i // 4, i % 4
    x0 = gu(20) if col == 0 else gu(50)      # 25.4 / 63.5
    y0 = round(25.4 + row * 38.1, 2)
    y0 = gu(round(y0 / U))
    island("Connector_Generic:Conn_01x02", "TB%d" % n, "WIRE%d" % n, x0, y0,
           {"1": N("W%d_T" % n), "2": "GND"},
           desc="Wire %d terminal (generic 2-pole: pin1 = signal side, pin2 = GND side). Physical realisation (screw / push-in, one block per wire end or shared) is decided after the sample tests. An intact wire joins signal to GND (reads LOW); a cut wire reads HIGH." % n,
           ref_off=(-2.54, -5.08), val_off=(-2.54, 5.08))
    island("Device:R", "R%d" % n, "1k", gu(round((x0 + 20.32) / U)), y0,
           {"1": N("W%d_T" % n), "2": N("W%d_IN" % n)},
           footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
           desc="Series resistor on the exposed wire terminal (ESD / short-circuit current limit; 1k, aligned with the wires and complicated-wires modules)",
           ref_off=(3.81, -1.27), val_off=(3.81, 1.27))
    island("Device:R", "R%d" % (8 + n), "10k", gu(round((x0 + 30.48) / U)), y0,
           {"1": "+3V3", "2": N("W%d_IN" % n)},
           footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
           desc="External pull-up to 3V3 (internal pull-up NOT used, aligned with the wires module); with the 1k series resistor an intact wire reads about 3.3V*1k/(10k+1k) = 0.3V (VIL max 0.8V)",
           ref_off=(3.81, -1.27), val_off=(3.81, 1.27))

# ------------------------------------------------------------------ NeoPixel chain
NP_X0, NP_DX = 198.12, 22.86
row_y = {0: 27.94, 1: 127.0}
np_pins = {}
for i in range(8):
    n = i + 1
    row, col = i // 4, i % 4
    x = round(NP_X0 + col * NP_DX, 2)
    y = row_y[row]
    x = gu(round(x / U)); y = gu(round(y / U))
    din = N("NEO_DIN") if n == 1 else (N("NEO_%d_%d" % (n - 1, n)) if col == 0 else None)
    dout = None if n == 8 else (N("NEO_%d_%d" % (n, n + 1)) if col == 3 else None)
    pins = place("LED:WS2812B", "NP%d" % n, "WS2812B", x, y,
                 footprint="", desc="NeoPixel #%d for wire %d (WS2812B V5 chip or AE-WS2812B module; footprint decided with the board method). Chain: DIN<-GPIO10 via 330R, DOUT->next DIN." % (n, n),
                 ref_off=(0, -10.16), val_off=(0, 10.16))
    np_pins[n] = (x, y, pins)
    connect("NP%d" % n, "LED:WS2812B", pins, "1", N("NEO_VDD"), 5.08)
    connect("NP%d" % n, "LED:WS2812B", pins, "3", "GND", 5.08)
    # DIN
    if n == 1:
        connect("NP1", "LED:WS2812B", pins, "4", N("NEO_DIN"), 5.08)
    elif col == 0:
        connect("NP%d" % n, "LED:WS2812B", pins, "4", N("NEO_%d_%d" % (n - 1, n)), 5.08)
    # DOUT
    if n == 8:
        connect("NP8", "LED:WS2812B", pins, "2", "nc")
    elif col == 3:
        connect("NP%d" % n, "LED:WS2812B", pins, "2", N("NEO_%d_%d" % (n, n + 1)), 5.08)
# direct wires DOUT(n) -> DIN(n+1) inside a row
for n in (1, 2, 3, 5, 6, 7):
    xa, ya, pa = np_pins[n]
    xb, yb, pb = np_pins[n + 1]
    a, b = pa["2"], pb["4"]
    assert a[1] == b[1]
    add_wire(a, b, "NEO_%d_%d" % (n, n + 1))
    NET_MEMBERS.setdefault("NEO_%d_%d" % (n, n + 1), []).extend(["NP%d.2" % n, "NP%d.4" % (n + 1)])
# per-LED decoupling capacitors
for i in range(8):
    n = i + 1
    x, y, _ = np_pins[n]
    cx = gu(round((x + 11.43) / U)); cy = gu(round((y + 25.4) / U)) if i < 4 else gu(round((y + 25.4) / U))
    island("Device:C", "C%d" % n, "0.1u", cx, cy, {"1": N("NEO_VDD"), "2": "GND"},
           footprint="Capacitor_THT:C_Disc_D3.0mm_W2.0mm_P2.50mm",
           desc="Local decoupling for NeoPixel #%d (VDD-VSS)" % n, ref_off=(3.81, -1.27), val_off=(3.81, 1.27))

# NeoPixel data resistor + bulk capacitor
island("Device:R", "R17", "330", 200.66, 88.9, {"1": N("NEO_RAW"), "2": N("NEO_DIN")},
       footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
       desc="Series resistor at the start of the NeoPixel data line (GPIO10 -> first DIN)", ref_off=(3.81, -1.27), val_off=(3.81, 1.27))
island("Device:C_Polarized", "C9", "100u", 220.98, 88.9, {"1": N("NEO_VDD"), "2": "GND"},
       footprint="Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
       desc="Bulk capacitor across the NeoPixel supply at the head of the chain (100-220uF)", ref_off=(3.81, -1.27), val_off=(3.81, 1.27))

# NeoPixel supply: +5V -> NEO_VDD through EITHER a 0R link (default) OR a series diode (drops VDD ~0.7V, lowers the DIN threshold)
R23_PINS = island("Device:R", "R23", "0", 208.28, 111.76, {"1": "+5V", "2": N("NEO_VDD")},
       footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
       desc="0R link (default) between +5V and NEO_VDD. Remove it and fit D10 instead when a VDD drop is needed (see design notes 7)", ref_off=(3.81, -1.27), val_off=(3.81, 1.27))
island("Device:D", "D10", "1N4007", 233.68, 111.76, {"1": N("NEO_VDD"), "2": "+5V"},
       footprint="Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
       desc="Optional VDD-drop diode for the NeoPixel chain (fit INSTEAD of R23 if DIN threshold margin is insufficient: VDD ~4.3V gives VIH ~3.0V; NeoPixel VDD min is 3.5V (AE module) / 3.7V (V5 chip))",
       ref_off=(0, -3.81), val_off=(0, 3.81))

# ------------------------------------------------------------------ stage LEDs, status LED, buttons (bottom-left area)
for i in range(4):
    n = i + 1
    x = gu(round((20.32 + i * 30.48) / U))
    island("Device:R", "R%d" % (17 + n), "330", x, 160.02, {"1": N("STAGE%d" % n), "2": N("STAGE%d_A" % n)},
           footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
           desc="Current limit for stage indicator LED %d" % n, ref_off=(3.81, -1.27), val_off=(3.81, 1.27))
    island("Device:LED", "LED%d" % n, "STAGE%d" % n, x, 182.88, {"1": "GND", "2": N("STAGE%d_A" % n)},
           footprint="LED_THT:LED_D5.0mm", desc="Stage indicator %d (lit once page %d has been confirmed)" % (n, n),
           ref_off=(0, -3.81), val_off=(0, 3.81))
island("Device:R", "R22", "47", 142.24, 160.02, {"1": N("STATUS"), "2": N("STATUS_A")},
       footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
       desc="Current limit for the green status LED (common spec: GPIO direct + 47R)", ref_off=(3.81, -1.27), val_off=(3.81, 1.27))
island("Device:LED", "LED5", "STATUS_GREEN", 142.24, 182.88, {"1": "GND", "2": N("STATUS_A")},
       footprint="LED_THT:LED_D3.0mm", desc="Module status LED (green, lit while the module is solved) - OSG58A3131A (3mm InGaN pure green, Vf 2.9/3.1/3.6V at 20mA)", ref_off=(0, -3.81), val_off=(0, 3.81))
island("Switch:SW_Push", "SW1", "UP", 182.88, 160.02, {"1": N("BTN_UP"), "2": "GND"},
       footprint="Button_Switch_THT:SW_PUSH-12mm", desc="UP button (tact switch 1273HIM-160G-G, 12mm square; use two legs from opposite sides)",
       ref_off=(0, -3.81), val_off=(0, 3.81))
island("Switch:SW_Push", "SW2", "DOWN", 213.36, 160.02, {"1": N("BTN_DOWN"), "2": "GND"},
       footprint="Button_Switch_THT:SW_PUSH-12mm", desc="DOWN button (tact switch 1273HIM-160G-G, 12mm square; use two legs from opposite sides)",
       ref_off=(0, -3.81), val_off=(0, 3.81))

# ------------------------------------------------------------------ power flags (so ERC sees the rails as driven)
# put each flag on an existing power-symbol stub end (same wire node, same net)
# +5V flag: at J1 pin 3 stub end; +3V3 flag: at U1 pin 36 stub end; GND flag: at J1 pin 4 stub end
j1 = [p for p in placed if p["ref"] == "J1"][0]["pins"]
u1 = pico_pins
flag((round(j1["3"][0] - 5.08, 2), j1["3"][1]))
flag((round(j1["4"][0] - 10.16, 2), j1["4"][1]))
flag((round(u1["36"][0] + 5.08, 2), u1["36"][1]))
r23 = [p for p in placed if p["ref"] == "R23"][0]["pins"]
flag((r23["2"][0], round(r23["2"][1] + 5.08, 2)))      # NEO_VDD is fed through passive parts only -> needs a flag

# ------------------------------------------------------------------ assemble
def build():
    hdr = ("(kicad_sch\n\t(version 20260306)\n\t(generator \"eeschema\")\n\t(generator_version \"10.0\")\n"
           "\t(uuid \"%s\")\n\t(paper \"A4\")\n\t(title_block\n\t\t(title \"Wire Sequence module (order-of-wires)\")\n"
           "\t\t(date \"2026-09-24\")\n\t\t(comment 1 \"OSC2026 bomb defusal prop - Wire Sequence module, 80mm panel, 8 wires (4 pages x 2)\")\n"
           "\t\t(comment 2 \"Wire terminals are generic 2-pole connectors; terminal block model and NeoPixel footprint are decided later\")\n"
           "\t)\n") % ROOT_UUID
    libs = "\t(lib_symbols\n" + "\n".join(_indent(v) for v in LIBS.values()) + "\n\t)\n"
    return (hdr + libs + "".join(wires_out) + "".join(nc_out) + "".join(labels_out) + "".join(symbols_out)
            + "\t(sheet_instances\n\t\t(path \"/\"\n\t\t\t(page \"1\")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n")


def _indent(block):
    # lib files use 1 tab at the top level; keypad's embedded ones use 2 tabs. Re-indent uniformly by prefixing.
    lines = block.split("\n")
    return "\n".join(("\t" + l if l.strip() else l) for l in lines)


# ------------------------------------------------------------------ self checks (geometry only; connectivity is verified via kicad-cli netlist)
def seg_contains(a, b, p):
    if a[0] == b[0] == p[0]:
        return min(a[1], b[1]) - 1e-6 <= p[1] <= max(a[1], b[1]) + 1e-6
    if a[1] == b[1] == p[1]:
        return min(a[0], b[0]) - 1e-6 <= p[0] <= max(a[0], b[0]) + 1e-6
    return False


def checks():
    problems = []
    # off-grid
    for w in wire_recs:
        for c in (*w["a"], *w["b"]):
            if abs(c / U - round(c / U)) > 1e-6:
                problems.append(("off-grid", w))
    # different-net wires must not touch
    for i, w1 in enumerate(wire_recs):
        for w2 in wire_recs[i + 1:]:
            if w1["net"] == w2["net"]:
                continue
            for p in (w1["a"], w1["b"]):
                if seg_contains(w2["a"], w2["b"], p):
                    problems.append(("wire touches other net", w1, w2))
            for p in (w2["a"], w2["b"]):
                if seg_contains(w1["a"], w1["b"], p):
                    problems.append(("wire touches other net", w2, w1))
    # pins lying on a wire of a different net than the pin's own net (need pin->net map)
    pin_net = {}
    for net, mem in NET_MEMBERS.items():
        for m in mem:
            pin_net[m] = net
    for part in placed:
        for num, pos in part["pins"].items():
            key = "%s.%s" % (part["ref"], num)
            own = pin_net.get(key)
            for w in wire_recs:
                if seg_contains(w["a"], w["b"], pos) and w["net"] != own and own is not None:
                    problems.append(("pin on foreign wire", key, own, w))
    # two different parts' pins at the same point but different nets
    seen = {}
    for part in placed:
        for num, pos in part["pins"].items():
            key = "%s.%s" % (part["ref"], num)
            if pos in seen and not (part["ref"].startswith("#") or seen[pos][0].startswith("#")):
                other = seen[pos]
                if pin_net.get(key) != pin_net.get(other):
                    problems.append(("coincident pins", key, other))
            seen.setdefault(pos, key)
    return problems


if __name__ == "__main__":
    probs = checks()
    for p in probs:
        print("PROBLEM:", p)
    text = build()
    path = os.path.join(OUT_DIR, "wire_sequence.kicad_sch")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    json.dump({k: sorted(v) for k, v in NET_MEMBERS.items()}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "spec_nets.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("written", path, len(text), "bytes; parts:", len(placed), "wires:", len(wire_recs), "problems:", len(probs))
