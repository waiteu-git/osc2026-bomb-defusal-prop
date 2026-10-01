# -*- coding: utf-8 -*-
"""Swap a module schematic from RPi_Pico:Pico (43 pins) to OSC_Shared:Pico_TH40 (40 header pins).

usage: python apply_pico_th40.py <module.kicad_sch> [--write]
Dry run by default (prints what would change). Aborts without writing if the layout differs from the expected one
(Pico placed at angle 0, pin 42 = wire + power:GND symbol, pins 41/43 = no_connect flags).
Also needed once per project (not done here): register OSC_Shared in sym-lib-table / fp-lib-table, see README.md.
Edits are text-level: every other block stays byte-identical. Verify afterwards with kicad-cli ERC + netlist."""
import re, sys

P = sys.argv[1]
WRITE = "--write" in sys.argv
NICK = "OSC_Shared"
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


def fail(msg):
    raise SystemExit("ABORT (nothing written): " + msg)


if '(lib_id "RPi_Pico:Pico")' not in t:
    fail("no RPi_Pico:Pico instance (already converted or no Pico)")

# ---- 1. lib symbol: drop pins 41-43, rename
i = t.index('\n\t\t(symbol "RPi_Pico:Pico"') + 1
e = end(t, i + 2)
blk = t[i:e].strip("\t")
n = 0
for m in list(re.finditer(r'\n\t+\(pin \w+ \w+[ \n]', blk))[::-1]:
    ee = end(blk, blk.index("(pin", m.start()))
    if re.search(r'\(number "4[123]"', blk[m.start():ee]):
        blk = blk[:m.start()] + blk[ee:]; n += 1
if n != 3: fail("expected 3 pins 41-43 in the lib symbol, found %d" % n)
new = blk.replace('(symbol "RPi_Pico:Pico"', '(symbol "%s:Pico_TH40"' % NICK, 1)
new = re.sub(r'\(symbol "Pico_(\d_\d)"', r'(symbol "Pico_TH40_\1"', new)
new = re.sub(r'(\(property "Footprint" ")[^"]*"', r'\1%s:RPi_Pico_TH_Headers"' % NICK, new, count=1)
t = t[:i] + "\t\t" + new + t[e:]

# ---- 2. placed Picos
refs = []
for m in list(re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "RPi_Pico:Pico"\)', t))[::-1]:
    s = m.start() + 2; ee = end(t, s); b = t[s:ee]
    ref = re.search(r'\(property "Reference" "([^"]+)"', b).group(1); refs.append(ref)
    at = re.search(r'\(at ([-\d.]+) ([-\d.]+) (\d+)\)', b)
    X, Y, ang = float(at.group(1)), float(at.group(2)), int(at.group(3))
    if ang != 0 or "(mirror" in b: fail("%s is rotated/mirrored" % ref)
    b = b.replace('(lib_id "RPi_Pico:Pico")', '(lib_id "%s:Pico_TH40")' % NICK)
    b = re.sub(r'(\(property "Footprint" ")[^"]*"', r'\1%s:RPi_Pico_TH_Headers"' % NICK, b, count=1)
    for p in ("41", "42", "43"):
        mm = re.search(r'\n\t\t\(pin "%s"\n\t\t\t\(uuid "[^"]+"\)\n\t\t\)' % p, b)
        if not mm: fail("%s: instance pin %s entry missing" % (ref, p))
        b = b[:mm.start()] + b[mm.end():]
    t = t[:s] + b + t[ee:]
    y0 = Y + 29.21; xs = [X - 2.54, X, X + 2.54]
    dead = []
    for mm in re.finditer(r'\n\t\((no_connect|wire|symbol|label|junction)\b', t):
        s2 = mm.start() + 2; e2 = end(t, s2); bb = t[s2:e2]
        if "Pico_TH40" in bb: continue
        pts = [(float(a), float(c)) for a, c in re.findall(r'\((?:at|xy) ([-\d.]+) ([-\d.]+)', bb)]
        if not any(abs(px - x) < 0.02 and y0 - 3.0 <= py <= y0 + 12 for px, py in pts for x in xs): continue
        if bb.startswith("(symbol") and '(lib_id "power:GND")' not in bb: fail("%s: unexpected symbol below the Pico" % ref)
        dead.append((s2, e2, bb.split("\n")[0]))
    kinds = sorted(d[2] for d in dead)
    if kinds != ["(no_connect", "(no_connect", "(symbol", "(wire"]: fail("%s: unexpected items on pins 41-43: %s" % (ref, kinds))
    for s2, e2, _ in sorted(dead, reverse=True):
        t = t[:s2 - 1] + t[e2:]

print(("WRITE " if WRITE else "dry run OK ") + P, "->", ", ".join(refs))
if WRITE:
    open(P, "w", encoding="utf-8", newline="\n").write(t)
