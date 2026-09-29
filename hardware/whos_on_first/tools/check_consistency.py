# -*- coding: utf-8 -*-
"""Cross-check the KiCad netlist against (1) the GPIO table in the design notes and
(2) the pin constants in the bring-up script. Also diff against the previous netlist.

2026-09-27(2): updated for the TFT->OLED change (J2 is now a 4-pin I2C0
connector: 1=SDA, 2=SCL, 3=GND, 4=+3.3V; buttons moved from GP8-13 to GP2-7)."""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os
# Usage: python check_consistency.py [old_netlist.net]   (run from anywhere)
# Compares whos_on_first_netlist.net with the GPIO table in whos_on_first_design_notes.md (section 4)
# and the pin constants in whos_on_first_bringup_test.py; optionally diffs against an older netlist.
_HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(_HERE) + os.sep           # hardware/whos_on_first/
OLD_NETLIST = sys.argv[1] if len(sys.argv) > 1 else None

def parse_sexp(s):
    tokens = re.findall(r'\(|\)|"[^"]*"|[^\s()]+', s)
    pos = [0]
    def parse():
        node = []
        while pos[0] < len(tokens):
            t = tokens[pos[0]]; pos[0] += 1
            if t == '(': node.append(parse())
            elif t == ')': return node
            else: node.append(t.strip('"'))
        return node
    return parse()[0]

def nets(path):
    tree = parse_sexp(open(path, encoding='utf-8').read())
    nn = [c for c in tree[1:] if isinstance(c, list) and c and c[0] == 'nets'][0]
    out = {}
    for net in [c for c in nn[1:] if c and c[0] == 'net']:
        name = [c for c in net[1:] if c[0] == 'name'][0][1]
        mem = []
        for n in net[1:]:
            if n[0] == 'node':
                ref = [x for x in n if x[0] == 'ref'][0][1]
                pin = [x for x in n if x[0] == 'pin'][0][1]
                pf = [x for x in n if x[0] == 'pinfunction']
                mem.append((ref, pin, pf[0][1] if pf else ""))
        out[name] = sorted(mem)
    return out

new = nets(BASE + "whos_on_first_netlist.net")
old = nets(OLD_NETLIST) if OLD_NETLIST else None

# Pico physical pin number -> GPIO number (from the RPi_Pico:Pico symbol pinfunction names)
def gpio_of(pinfunc):
    m = re.match(r'GPIO(\d+)', pinfunc)
    return int(m.group(1)) if m else None

# ---- what the NETLIST says each GPIO connects to ----
# J2 (2026-09-27(2)): 0.96in SSD1315 OLED, I2C0, 4-pin local connector.
J2_SIG = {"1": "SDA", "2": "SCL", "3": "GND", "4": "VCC"}
SW_POS = {"SW1": "TL", "SW2": "TR", "SW3": "ML", "SW4": "MR", "SW5": "BL", "SW6": "BR"}
net_map = {}   # gpio -> description
for name, mem in new.items():
    for ref, pin, pf in mem:
        if ref == "U1" and gpio_of(pf) is not None:
            g = gpio_of(pf)
            others = [(r, p) for r, p, _ in mem if not (r == "U1" and p == pin)]
            desc = []
            for r, p in others:
                if r == "J2": desc.append("OLED_" + J2_SIG[p])
                elif r == "J1": desc.append({"1": "UART_TX", "2": "UART_RX"}.get(p, "J1." + p))
                elif r in SW_POS: desc.append("BTN_" + SW_POS[r])
                elif r.startswith("R"): desc.append({"R1": "STAGE1", "R2": "STAGE2", "R3": "STAGE3", "R4": "STATUS"}[r])
                else: desc.append(r + "." + p)
            net_map[g] = "+".join(sorted(desc)) if desc else "(unconnected)"

# ---- what the DESIGN NOTES section 4 table says ----
notes = open(BASE + "whos_on_first_design_notes.md", encoding="utf-8").read()
sec4 = notes[notes.index("## 4. GPIO割当表"):notes.index("## 5. 挙動")]
notes_map = {}
for m in re.finditer(r'^\| GP(\d+) \| ([^|]+) \|', sec4, re.M):
    g = int(m.group(1)); use = m.group(2).strip()
    key = None
    for tok, k in (("OLED SDA", "OLED_SDA"), ("OLED SCL", "OLED_SCL"),
                   ("UART0 TX", "UART_TX"), ("UART0 RX", "UART_RX"),
                   ("ボタンSW 左上", "BTN_TL"), ("ボタンSW 右上", "BTN_TR"), ("ボタンSW 左中", "BTN_ML"),
                   ("ボタンSW 右中", "BTN_MR"), ("ボタンSW 左下", "BTN_BL"), ("ボタンSW 右下", "BTN_BR"),
                   ("ステージ進捗LED 1", "STAGE1"), ("ステージ進捗LED 2", "STAGE2"), ("ステージ進捗LED 3", "STAGE3"),
                   ("状態表示LED", "STATUS"), ("(予備)", "(unconnected)")):
        if tok in use: key = k
    notes_map[g] = key

# ---- what the BRING-UP SCRIPT says ----
py = open(BASE + "whos_on_first_bringup_test.py", encoding="utf-8").read()
script_map = {}
m = re.search(r'^OLED_SDA, OLED_SCL = (\d+), (\d+)$', py, re.M)
script_map[int(m.group(1))] = "OLED_SDA"
script_map[int(m.group(2))] = "OLED_SCL"
for pos in ("TL", "TR", "ML", "MR", "BL", "BR"):
    mm = re.search(r'"%s": (\d+)' % pos, py)
    script_map[int(mm.group(1))] = "BTN_" + pos
sm = re.search(r'STAGE_LED_PINS = \[([\d, ]+)\]', py)
for i, v in enumerate([int(x) for x in sm.group(1).split(",")], start=1): script_map[v] = "STAGE%d" % i
script_map[int(re.search(r'STATUS_LED_PIN = (\d+)', py).group(1))] = "STATUS"

print("GPIO | netlist                | notes sec4   | bring-up script")
bad = 0
for g in list(range(0, 18)):
    n_, t_, s_ = net_map.get(g), notes_map.get(g), script_map.get(g)
    # GP0/GP1 are not in the script (UART unused in bring-up)
    ok = (n_ == t_) and (s_ is None or s_ == n_)
    if not ok: bad += 1
    print("GP%-2d | %-22s | %-12s | %-12s %s" % (g, n_, t_, s_, "" if ok else "  <== MISMATCH"))
print("MISMATCHES:", bad)

# ---- diff netlist old vs new (by ref.pin members, ignoring auto-generated names) ----
def as_sets(d):
    return {frozenset((r, p) for r, p, _ in mem) for mem in d.values()}
if old is not None:
    so, sn = as_sets(old), as_sets(new)
    print("\nnets only in OLD (removed/changed):")
    for s in sorted(so - sn, key=lambda x: sorted(x)): print("  ", sorted(s))
    print("nets only in NEW (added/changed):")
    for s in sorted(sn - so, key=lambda x: sorted(x)): print("  ", sorted(s))
sys.exit(1 if bad else 0)
