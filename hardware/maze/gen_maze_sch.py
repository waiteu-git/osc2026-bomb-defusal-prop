"""Generate hardware/maze/maze.kicad_sch (Maze module, display-independent common part).

Scope (hub decision 2026-09-27, partial go-ahead): everything that does NOT depend on which display is chosen.
  * J1 = UART0 to host (Pin1 = GPIO0 TX, Pin2 = GPIO1 RX, Pin3 = +5V, Pin4 = GND)   [I2C shared bus is gone]
  * 4 direction buttons on GP2-5, green status LED on GP7 (47R), 100uF bulk capacitor on the +5V input
  * WS2812B chain (D1/R1/C1(1000uF)/#PWR12-15/note) removed
  * PWR_FLAG on +5V / GND / +3V3, all unused Pico pins carry a no-connect flag
  * display connector NOT placed yet (case A: I2C0 GP8/9, case B/B': SPI GP8-GP13) -> GP8-GP13 stay no-connect for now

Same generator pattern as hardware/wire_sequence/gen_wire_sequence_sch.py (rules honoured):
  * every coordinate is an integer multiple of 1.27 mm, every wire has exactly 2 points
  * lib_symbols sub-unit names carry no 'Library:' prefix (only the top-level symbol name does)
  * absolute pin position = (placement_x + local_x, placement_y - local_y)   # Y-up library, Y-down sheet
  * every part is placed at rotation 0; stubs leave a pin horizontally (never vertically on a pin column)
Connectivity is verified with verify_maze_sch.py (kicad-cli netlist vs expected_nets.json), not by ERC alone.
"""
import os, sys, uuid, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kilib import from_std_lib, from_keypad, read_pins

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT = "maze"
NS = uuid.UUID("3c8a5e0f-7d21-4b6a-9e34-51f0c2d8a7b3")
ROOT_UUID = "aeb3289c-4790-4f75-b0d4-973e8ec2f552"      # unchanged from the original maze.kicad_sch
U = 1.27


def gu(n):
    return round(n * U, 2)


def uid(tag):
    return str(uuid.uuid5(NS, tag))


LIBS = {
    "RPi_Pico:Pico": from_keypad("RPi_Pico:Pico"),
    "Device:R": from_keypad("Device:R"),
    "Device:LED": from_keypad("Device:LED"),
    "Switch:SW_Push": from_keypad("Switch:SW_Push"),
    "Connector_Generic:Conn_01x04": from_keypad("Connector_Generic:Conn_01x04"),
    "power:GND": from_keypad("power:GND"),
    "power:+5V": from_keypad("power:+5V"),
    "power:+3.3V": from_keypad("power:+3.3V"),
    "Device:C_Polarized": from_std_lib("Device", "C_Polarized"),
    "power:PWR_FLAG": from_std_lib("power", "PWR_FLAG"),
}
PINS = {k: {p["number"]: p for p in read_pins(v)} for k, v in LIBS.items()}

symbols_out, wires_out, labels_out, nc_out, texts_out = [], [], [], [], []
placed = []
wire_recs = []
pwr_counter = [0]
flg_counter = [0]

FONT = "\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n"


def prop(name, value, x, y, hide=False, ang=0):
    v = value.replace("\\", "\\\\").replace('"', '\\"')
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s %s)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            '\t\t\t(effects\n%s\t\t\t)\n\t\t)\n') % (name, v, x, y, ang, "\t\t\t(hide yes)\n" if hide else "", FONT)


def place(lib, ref, value, x, y, footprint="", desc="", in_bom=True, on_board=True, ref_off=(0, -5.08),
          val_off=(0, 5.08)):
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
                     "\t\t)\n\t\t(uuid \"%s\")\n\t)\n" % (a[0], a[1], b[0], b[1], uid("wire-%s-%s-%s-%s" % (a, b, net, len(wires_out)))))
    wire_recs.append(dict(a=a, b=b, net=net))


def add_label(name, pos, direction):
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


def add_text(s, x, y):
    t = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    texts_out.append("\t(text \"%s\"\n\t\t(at %s %s 0)\n\t\t(effects\n%s\t\t\t(justify left)\n\t\t)\n\t\t(uuid \"%s\")\n\t)\n" % (
        t, x, y, FONT, uid("text-%s-%s" % (x, y))))


def outward(lib, num):
    p = PINS[lib][num]
    a = math.radians(p["angle"] + 180.0)
    return (round(math.cos(a)), round(-math.sin(a)))


def pwr_symbol(kind, pos, net):
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


NET_MEMBERS = {}


def connect(ref, lib, pins, num, spec, length=5.08):
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

# ------------------------------------------------------------------ Pico 2 (same placement as keypad / wire_sequence)
PICO_X, PICO_Y = 149.86, 76.2
pico_spec = {
    "1": N("UART_TX"), "2": N("UART_RX"), "3": "GND",
    "4": N("BTN_UP"), "5": N("BTN_LEFT"), "6": N("BTN_DOWN"), "7": N("BTN_RIGHT"),
    "8": "GND",
    "9": "nc",                                   # GP6: free (was the WS2812B DIN)
    "10": N("STATUS"),                           # GP7: status LED
    "11": N("OLED_SDA"), "12": N("OLED_SCL"),    # GP8/GP9: 0.96in SSD1315 OLED, local I2C0 (case A, decided 2026-09-27)
    "13": "GND",
    "14": "nc", "15": "nc", "16": "nc", "17": "nc",   # GP10-GP13: unused (TFT case B/B' not adopted)
    "18": "GND",
    "19": "nc", "20": "nc", "21": "nc", "22": "nc",
    "23": "GND",
    "24": "nc", "25": "nc", "26": "nc", "27": "nc", "28": "GND",
    "29": "nc", "30": "nc", "31": "nc", "32": "nc", "33": "GND",
    "34": "nc", "35": "nc", "36": "+3V3", "37": "nc", "38": "GND",
    "39": "+5V", "40": "nc",
    "41": "nc", "42": "GND", "43": "nc",
}
pico_pins = island("RPi_Pico:Pico", "U1", "Pico 2", PICO_X, PICO_Y, pico_spec,
                   footprint="RPi_Pico:RPi_Pico_SMD_TH",
                   desc="Raspberry Pi Pico 2 (RP2350, headerless / direct-solder, 990 yen basis). GPIO0/1 = UART0 to host (reserved). JST +5V feeds VSYS; VBUS left open. GP8/GP9 = local I2C0 to the OLED (case A, decided 2026-09-27). GP10-13 unused.",
                   ref_off=(0, -31.75), val_off=(0, -29.21))

# ------------------------------------------------------------------ host connector (UART, common spec)
island("Connector_Generic:Conn_01x04", "J1", "JST_XH_4P_HOST", 254.0, 88.9,
       {"1": N("UART_TX"), "2": N("UART_RX"), "3": "+5V", "4": "GND"},
       footprint="Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
       desc="Host link (common spec): Pin1=GPIO0 UART0 TX (module->host), Pin2=GPIO1 UART0 RX (host->module), Pin3=VCC 5V (host polyfuse, panel budget 200mA average), Pin4=GND. No pull-ups on the module side.",
       lengths={"3": 5.08, "4": 10.16}, ref_off=(2.54, -8.89), val_off=(2.54, 8.89))

# ------------------------------------------------------------------ display: 0.96in SSD1315 OLED, local I2C0 (case A)
island("Connector_Generic:Conn_01x04", "J2", "OLED_LOCAL_I2C", 254.0, 127.0,
       {"1": N("OLED_SDA"), "2": N("OLED_SCL"), "3": "GND", "4": "+3V3"},
       footprint="Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
       desc="Local wiring to the 0.96in SSD1315 OLED breakout, I2C0 bus (NOT the shared UART link to host). "
            "Pin1=SDA(GP8), Pin2=SCL(GP9), Pin3=GND, Pin4=+3.3V (from Pico 3V3 OUT, regulated). Breakout board's "
            "own header pin order (commonly GND,VCC,SCL,SDA) may differ; match by hand when the physical board "
            "arrives (same open item as password_design_notes.md). Address 0x3C, board's own pull-ups used "
            "(no external pull-up on this connector).",
       ref_off=(2.54, -8.89), val_off=(2.54, 8.89))

# ------------------------------------------------------------------ 5V input bulk capacitor
island("Device:C_Polarized", "C1", "100u", 220.98, 88.9, {"1": "+5V", "2": "GND"},
       footprint="Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
       desc="Bulk capacitor on the +5V input (>=100uF per hub rule: absorbs short current peaks; observe polarity)",
       ref_off=(3.81, -1.27), val_off=(3.81, 1.27))

# ------------------------------------------------------------------ status LED (common spec: GPIO direct + 47R), GP7
island("Device:R", "R2", "47", 142.24, 160.02, {"1": N("STATUS"), "2": N("STATUS_A")},
       footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
       desc="Current limit for the green status LED (common spec: GPIO direct + 47R, same as keypad)", ref_off=(3.81, -1.27), val_off=(3.81, 1.27))
island("Device:LED", "LED1", "STATUS_GREEN", 142.24, 182.88, {"1": "GND", "2": N("STATUS_A")},
       footprint="LED_THT:LED_D3.0mm",
       desc="Module status LED (green, lit while the module is solved) - OSG58A3131A (3mm InGaN pure green, Vf 2.9/3.1/3.6V at 20mA). GPIO7, drive low right after reset (RP2350 E9 rule).",
       ref_off=(0, -3.81), val_off=(0, 3.81))

# ------------------------------------------------------------------ 4 direction buttons (GP2-GP5), 2 x 2 block
for ref, val, net, x, y in (("SW1", "UP", "BTN_UP", 182.88, 132.08), ("SW2", "LEFT", "BTN_LEFT", 223.52, 132.08),
                            ("SW3", "DOWN", "BTN_DOWN", 182.88, 157.48), ("SW4", "RIGHT", "BTN_RIGHT", 223.52, 157.48)):
    island("Switch:SW_Push", ref, val, x, y, {"1": N(net), "2": "GND"},
           footprint="Button_Switch_THT:SW_PUSH-12mm",
           desc="%s direction button (tact switch 1273HIM-160G-G, 12mm square; use two legs from opposite sides). Internal pull-up, GND on the other side." % val,
           ref_off=(0, -3.81), val_off=(0, 3.81))

add_text("Maze module (2026-09-27, complete): position display = 0.96in SSD1315 OLED (case A),\n"
         "decided by the hub 2026-09-27 (TFT cases B/B' not adopted: cost/complexity not worth the\n"
         "visual gain). J2 = local I2C0 to the OLED, GP8=SDA GP9=SCL, VCC=3V3, address 0x3C.\n"
         "GP6, GP10-GP13 unused/free. GP0/GP1 = UART0 to host (JST Pin1/Pin2).", 20.32, 25.4)

# ------------------------------------------------------------------ power flags (one per supply net, at existing power-symbol stub ends)
j1 = [p for p in placed if p["ref"] == "J1"][0]["pins"]
flag((round(j1["3"][0] - 5.08, 2), j1["3"][1]))            # +5V
flag((round(j1["4"][0] - 10.16, 2), j1["4"][1]))           # GND
flag((round(pico_pins["36"][0] + 5.08, 2), pico_pins["36"][1]))   # +3V3


def _indent(block):
    return "\n".join(("\t" + l if l.strip() else l) for l in block.split("\n"))


def build():
    hdr = ("(kicad_sch\n\t(version 20260306)\n\t(generator \"eeschema\")\n\t(generator_version \"10.0\")\n"
           "\t(uuid \"%s\")\n\t(paper \"A4\")\n\t(title_block\n\t\t(title \"Maze module\")\n"
           "\t\t(date \"2026-09-27\")\n\t\t(comment 1 \"OSC2026 bomb defusal prop - Maze module, 80mm panel\")\n"
           "\t\t(comment 2 \"UART0 host link; buttons GP2-5; status LED GP7; 0.96in SSD1315 OLED on local I2C0 (GP8/GP9)\")\n"
           "\t)\n") % ROOT_UUID
    libs = "\t(lib_symbols\n" + "\n".join(_indent(v) for v in LIBS.values()) + "\n\t)\n"
    return (hdr + libs + "".join(wires_out) + "".join(nc_out) + "".join(labels_out) + "".join(texts_out)
            + "".join(symbols_out)
            + "\t(sheet_instances\n\t\t(path \"/\"\n\t\t\t(page \"1\")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n")


def seg_contains(a, b, p):
    if a[0] == b[0] == p[0]:
        return min(a[1], b[1]) - 1e-6 <= p[1] <= max(a[1], b[1]) + 1e-6
    if a[1] == b[1] == p[1]:
        return min(a[0], b[0]) - 1e-6 <= p[0] <= max(a[0], b[0]) + 1e-6
    return False


def checks():
    problems = []
    for w in wire_recs:
        for c in (*w["a"], *w["b"]):
            if abs(c / U - round(c / U)) > 1e-6:
                problems.append(("off-grid", w))
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
    path = os.path.join(OUT_DIR, "maze.kicad_sch")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    json.dump({k: sorted(v) for k, v in NET_MEMBERS.items()},
              open(os.path.join(OUT_DIR, "expected_nets.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("written", path, len(text), "bytes; parts:", len(placed), "wires:", len(wire_recs), "problems:", len(probs))
