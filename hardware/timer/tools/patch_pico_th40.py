# -*- coding: utf-8 -*-
"""Protected patch of timer.kicad_sch (hand-edited): U1/U3 use a 40-pin Pico symbol (Timer_Local:Pico_TH40).
The floating Pico only touches the board through the 40 header pins, so SWCLK/GND/SWDIO (41-43) are dropped:
 - new lib symbol Timer_Local:Pico_TH40 = RPi_Pico:Pico without pins 41-43 (also appended to Timer_Local.kicad_sym)
 - U1/U3: lib_id switched, (pin "41".."43") instance entries removed
 - deleted: per Pico 2 no_connect flags (pins 41/43), the wire from pin 42 and its power:GND symbol
 - the now unused RPi_Pico:Pico lib symbol is removed from lib_symbols
Everything else stays byte-identical."""
import re, sys
D = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\timer"
P = D + r"\timer.kicad_sch"
LIB = D + r"\Timer_Local.kicad_sym"
t = open(P, encoding="utf-8").read()

def end(s, i):
    d = 0; ins = False; j = i
    while True:
        c = s[j]
        if ins:
            if c == "\\": j += 1
            elif c == '"': ins = False
        elif c == '"': ins = True
        elif c == "(": d += 1
        elif c == ")":
            d -= 1
            if d == 0: return j + 1
        j += 1

# ---- 1. new symbol from the embedded RPi_Pico:Pico
i = t.index('\n\t\t(symbol "RPi_Pico:Pico"') + 1
e = end(t, i + 2)
old = t[i:e]                       # starts with two tabs
blk = old.strip("\t")
n = 0
for m in list(re.finditer(r'\n\t+\(pin \w+ \w+\n', blk))[::-1]:
    s = m.start() + 1; ee = end(blk, blk.index("(pin", s))
    if re.search(r'\(number "4[123]"', blk[s:ee]):
        blk = blk[:s].rstrip("\t") + blk[ee:].lstrip("\n").join(["", ""]) if False else blk[:m.start()] + blk[ee:]
        n += 1
assert n == 3, n
new = blk.replace('(symbol "RPi_Pico:Pico"', '(symbol "Timer_Local:Pico_TH40"', 1)
new = re.sub(r'\(symbol "Pico_(\d_\d)"', r'(symbol "Pico_TH40_\1"', new)
new = re.sub(r'(\(property "Footprint" ")[^"]*"', r'\1Timer_Local:RPi_Pico_TH_Headers"', new, count=1)
new = re.sub(r'(\(property "Description" ")[^"]*"', r'\1Raspberry Pi Pico 2 H on header pins: only the 40 through-hole header pins (no SWD/debug pins 41-43; the module floats above the board)"', new, count=1)
assert 'number "41"' not in new and 'number "42"' not in new
t = t[:i] + "\t\t" + new + t[e:]          # replace in place; the old symbol is dropped, the new one keeps its slot
print("lib symbol replaced (3 pins dropped)")

# ---- 2. placed symbols U1 / U3
for ref in ("U1", "U3"):
    k = t.index('(property "Reference" "%s"' % ref)
    s = t.rfind("\n\t(symbol\n", 0, k) + 2; ee = end(t, s)
    b = t[s:ee]
    assert '(lib_id "RPi_Pico:Pico")' in b
    b = b.replace('(lib_id "RPi_Pico:Pico")', '(lib_id "Timer_Local:Pico_TH40")')
    at = re.search(r'\(at ([\d.]+) ([\d.]+) 0\)', b)
    X, Y = float(at.group(1)), float(at.group(2))
    for p in ("41", "42", "43"):
        m = re.search(r'\n\t\t\(pin "%s"\n\t\t\t\(uuid "[^"]+"\)\n\t\t\)' % p, b)
        assert m, (ref, p)
        b = b[:m.start()] + b[m.end():]
    t = t[:s] + b + t[ee:]
    # ---- 3. items hanging on the removed pins
    y0 = Y + 29.21
    xs = [X - 2.54, X, X + 2.54]
    dead = []
    for m in re.finditer(r'\n\t\((no_connect|wire|symbol)\b', t):
        s2 = m.start() + 2; e2 = end(t, s2); bb = t[s2:e2]
        if "Pico_TH40" in bb: continue
        pts = [(float(a), float(c)) for a, c in re.findall(r'\((?:at|xy) ([-\d.]+) ([-\d.]+)', bb)]
        if not any(abs(px - x) < 0.02 and y0 - 0.02 <= py <= y0 + 12 for px, py in pts for x in xs): continue
        if bb.startswith("(symbol") and '(lib_id "power:GND")' not in bb: raise SystemExit("unexpected symbol below " + ref)
        dead.append((s2, e2, bb.split("\n")[0]))
    kinds = sorted(d[2] for d in dead)
    print(ref, "removing", kinds)
    assert kinds == ["(no_connect", "(no_connect", "(symbol", "(wire"], kinds
    for s2, e2, _ in sorted(dead, reverse=True):
        t = t[:s2 - 1] + t[e2:]           # also drops the newline before the block
open(P, "w", encoding="utf-8", newline="\n").write(t)

# ---- 4. the same symbol in the project library
lib = open(LIB, encoding="utf-8").read()
assert "Pico_TH40" not in lib
sym = new.replace('(symbol "Timer_Local:Pico_TH40"', '(symbol "Pico_TH40"', 1)
sym = "\n".join((l[1:] if l.startswith("\t") else l) for l in sym.split("\n"))
k = lib.rstrip().rfind(")")
lib = lib[:k].rstrip("\n") + "\n\t" + sym.replace("\n", "\n").strip("\t") + "\n)\n"
open(LIB, "w", encoding="utf-8", newline="\n").write(lib)
print("done")
