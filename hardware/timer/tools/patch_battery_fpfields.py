# -*- coding: utf-8 -*-
"""Protected patch of timer.kicad_sch (hand-edited file, never regenerated):
 1. fill the empty Footprint fields (F1-F5, J1-J5, J7, R3, R4, U2) and correct C3's (470uF is not a 5 mm can)
 2. append the battery-input circuit: J6 (JST XH 2p) -> F6 (MF-R185) -> Q1 (IRLML6402 ideal diode) -> +5V, R5 gate resistor
Only appended blocks + property text inside the named symbols change; everything else stays byte-identical."""
import sys, re, uuid

PATH = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\timer\timer.kicad_sch"
OUT = sys.argv[1] if len(sys.argv) > 1 else PATH
SYMDIR = r"C:\Program Files\KiCad\10.0\share\kicad\symbols"
PROJ_UUID = "666ebaab-c68e-41d4-bf0e-3386c25b9236"
t = open(PATH, encoding="utf-8").read()
u = lambda: str(uuid.uuid4())

def block_end(s, i):
    """index just after the balanced block that opens at s[i] == '('"""
    depth = 0; instr = False; j = i
    while True:
        c = s[j]
        if instr:
            if c == "\\": j += 1
            elif c == '"': instr = False
        else:
            if c == '"': instr = True
            elif c == "(": depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0: return j + 1
        j += 1

def lib_block(libfile, name):
    s = open(SYMDIR + "\\" + libfile, encoding="utf-8").read()
    i = s.index('\n\t(symbol "%s"\n' % name) + 2
    return s[i:block_end(s, i)]

def indent(b):
    return "\n".join(("\t" + l if l else l) for l in b.split("\n"))

# ---------------------------------------------------------------- 1. footprint fields
FP = {
    "F1": "Timer_Local:MF-RX030_Radial_P5.10mm", "F2": "Timer_Local:MF-RX030_Radial_P5.10mm",
    "F3": "Timer_Local:MF-RX030_Radial_P5.10mm", "F4": "Timer_Local:MF-RX030_Radial_P5.10mm",
    "F5": "Timer_Local:MF-RX030_Radial_P5.10mm",
    "J1": "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", "J2": "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
    "J3": "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", "J4": "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
    "J5": "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", "J7": "Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical",
    "R3": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical",
    "R4": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical",
    "U2": "Package_DIP:DIP-20_W7.62mm",
}
CHANGE = {"C3": ("Capacitor_THT:CP_Radial_D5.0mm_P2.00mm", "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm")}

def sym_span(ref):
    for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "[^"]+"\)', t):
        s = m.start() + 2; e = block_end(t, s)
        if ('(property "Reference" "%s"' % ref) in t[s:e]:
            return s, e
    raise SystemExit("symbol not found: " + ref)

def set_fp(ref, new, expect_old):
    global t
    s, e = sym_span(ref)
    b = t[s:e]
    old = '(property "Footprint" "%s"' % expect_old
    if b.count(old) != 1:
        raise SystemExit("%s: Footprint field is not '%s'" % (ref, expect_old))
    t = t[:s] + b.replace(old, '(property "Footprint" "%s"' % new, 1) + t[e:]
    print("footprint", ref, "->", new)

for ref, fp in FP.items(): set_fp(ref, fp, "")
for ref, (old, new) in CHANGE.items(): set_fp(ref, new, old)

# ---------------------------------------------------------------- 2. new library symbols
assert '"Connector_Generic:Conn_01x02"' not in t and '"Transistor_FET:IRLML6402"' not in t
conn2 = lib_block("Connector_Generic.kicad_sym", "Conn_01x02")
conn2 = conn2.replace('(symbol "Conn_01x02"', '(symbol "Connector_Generic:Conn_01x02"', 1)
assert 'pin passive line\n\t\t\t\t(at -5.08 0 0)' in conn2 and '(at -5.08 -2.54 0)' in conn2, "Conn_01x02 pin geometry changed"

q = lib_block("Transistor_FET.kicad_sym", "TP0610T")          # IRLML6402 "extends" TP0610T -> flatten it
irl = lib_block("Transistor_FET.kicad_sym", "IRLML6402")
q = q.replace('(symbol "TP0610T"', '(symbol "Transistor_FET:IRLML6402"', 1).replace('"TP0610T_', '"IRLML6402_')
def prop_val(block, name):
    return re.search(r'\(property "%s" "((?:[^"\\]|\\.)*)"' % name, block).group(1)
for name in ("Value", "Datasheet", "Description"):
    q = re.sub(r'(\(property "%s" ")((?:[^"\\]|\\.)*)"' % name, lambda m: m.group(1) + prop_val(irl, name) + '"', q, count=1)
q = re.sub(r'(\(property "ki_keywords" ")((?:[^"\\]|\\.)*)"', lambda m: m.group(1) + prop_val(irl, "ki_keywords") + '"', q, count=1)
assert '(number "1"' in q and 'IRLML6402_1_1' in q

i_ls = t.index("\n\t(lib_symbols")
i_ls_end = block_end(t, i_ls + 2)                    # just after lib_symbols' closing paren
close = i_ls_end - 1
t = t[:close].rstrip("\t") + "\n" + indent("	"+conn2) + "\n" + indent("	"+q) + "\n\t" + t[close:]
print("lib symbols added")

# ---------------------------------------------------------------- 3. new placed items
def fmt(x):
    return ("%.2f" % x).rstrip("0").rstrip(".")
def prop(name, val, x, y, hide=False, justify=None):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n%s\t\t\t)\n\t\t)\n'
            % (name, val, fmt(x), fmt(y), "\t\t\t(hide yes)\n" if hide else "",
               ("\t\t\t\t(justify %s)\n" % justify) if justify else ""))

pwr_n = [210]
new = []
def symbol(lib_id, x, y, ref, value, footprint, desc, pins, ds=""):
    new.append('\t(symbol\n\t\t(lib_id "%s")\n\t\t(at %s %s 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
               '\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n' % (lib_id, fmt(x), fmt(y), u())
               + prop("Reference", ref, x, y - 5.08) + prop("Value", value, x, y + 6.35)
               + prop("Footprint", footprint, x, y, True) + prop("Datasheet", ds, x, y, True) + prop("Description", desc, x, y, True)
               + "".join('\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (p, u()) for p in pins)
               + '\t\t(instances\n\t\t\t(project "timer"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'
               % (PROJ_UUID, ref))

def power(name, x, y):
    pwr_n[0] += 1
    ref = "#PWR%d" % pwr_n[0]
    dy = 3.81 if name == "GND" else -3.81
    new.append('\t(symbol\n\t\t(lib_id "power:%s")\n\t\t(at %s %s 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
               '\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n' % (name, fmt(x), fmt(y), u())
               + prop("Reference", ref, x, y, True) + prop("Value", name, x, y + dy)
               + prop("Footprint", "", x, y, True) + prop("Datasheet", "", x, y, True)
               + prop("Description", 'Power symbol creates a global label with name \\"%s\\"' % name, x, y, True)
               + '\t\t(pin "1"\n\t\t\t(uuid "%s")\n\t\t)\n' % u()
               + '\t\t(instances\n\t\t\t(project "timer"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'
               % (PROJ_UUID, ref))

def wire(x1, y1, x2, y2):
    new.append('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "%s")\n\t)\n'
               % (fmt(x1), fmt(y1), fmt(x2), fmt(y2), u()))

def label(text, x, y, ang):
    j = "\t\t\t(justify right bottom)\n" if ang == 180 else ("\t\t\t(justify left bottom)\n" if ang == 270 else "")
    new.append('\t(label "%s"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n%s\t\t)\n\t\t(uuid "%s")\n\t)\n'
               % (text, fmt(x), fmt(y), ang, j, u()))

G = 1.27
J6x, J6y = 352 * G, 40 * G          # pins at x-5.08: pin1 (y), pin2 (y+2.54)
symbol("Connector_Generic:Conn_01x02", J6x, J6y, "J6", "PWR_IN",
       "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
       "Battery-box 5V input (JST XH 2p): pin1 = +5V from the DC-DC in the battery box, pin2 = GND. 5V IN ONLY", ["1", "2"])
wire(J6x - 5.08, J6y, 344 * G, J6y);              label("VIN_5V", 344 * G, J6y, 180)
wire(J6x - 5.08, J6y + 2.54, 344 * G, J6y + 2.54); power("GND", 344 * G, J6y + 2.54)

F6x, F6y = 366 * G, 48 * G
symbol("Device:Polyfuse_Small", F6x, F6y, "F6", "MF-R185 (1.85A hold, Akizuki 112629)",
       "Timer_Local:MF-R185_Radial_P5.10mm", "Battery input polyfuse, 1.85A hold, Bourns MF-R185 (upright, about 18.4mm tall)", ["1", "2"])
wire(F6x, F6y - 2.54, F6x, 44 * G);  label("VIN_5V", F6x, 44 * G, 90)
wire(F6x, F6y + 2.54, F6x, 52 * G);  label("VIN_FUSED", F6x, 52 * G, 270)

Qx, Qy = 380 * G, 56 * G
symbol("Transistor_FET:IRLML6402", Qx, Qy, "Q1", "IRLML6402",
       "Package_TO_SOT_SMD:SOT-23", "Ideal diode (reverse-polarity / back-feed guard): P-MOSFET, drain = fused battery side, source = +5V rail, gate = GND via R5",
       ["1", "2", "3"], "https://www.infineon.com/dgdl/irlml6402pbf.pdf?fileId=5546d462533600a401535668d5c2263c")
wire(Qx + 2.54, Qy - 5.08, Qx + 2.54, 50 * G);  label("VIN_FUSED", Qx + 2.54, 50 * G, 90)
wire(Qx + 2.54, Qy + 5.08, 386 * G, Qy + 5.08);  power("+5V", 386 * G, Qy + 5.08)
wire(Qx - 5.08, Qy, 372 * G, Qy)
symbol("Device:R", 372 * G, Qy + 3.81, "R5", "100k",
       "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical", "Q1 gate resistor (gate held at GND; limits ESD/transient gate current)", ["1", "2"])
power("GND", 372 * G, Qy + 7.62)

note = ("5V IN ONLY (J6 = regulated 5V from the battery-box DC-DC, never raw battery voltage)\\n"
        "J6 pin1 = +5V, pin2 = GND -> F6 (MF-R185) -> Q1 ideal diode -> +5V rail\\n"
        "USB rule: unplug J6 before flashing over USB (Q1 conducts both ways when the rail is up).\\n"
        "USB-only (J6 empty) is for bench tests only")
new.append('\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
           '\t\t\t(justify left top)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (note, fmt(344 * G), fmt(24 * G), u()))

i_si = t.index("\n\t(sheet_instances") + 1
t = t[:i_si] + "".join(new) + t[i_si:]
open(OUT, "w", encoding="utf-8", newline="\n").write(t)
print("WROTE", OUT, len(t))
