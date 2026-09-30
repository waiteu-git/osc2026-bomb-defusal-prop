# -*- coding: utf-8 -*-
"""Protected patch: remove F6 (battery-input polyfuse). J6.1 now goes straight to Q1 drain (net VIN_5V).
Deletes F6 symbol, its 2 wires and 2 labels; renames Q1-side label VIN_FUSED -> VIN_5V; fixes the note text."""
import re
P = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\timer\timer.kicad_sch"
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
def cut(pred, what):
    global t
    n = 0
    for m in list(re.finditer(r'\n\t\((symbol|wire|label)\b', t))[::-1]:
        s = m.start() + 2; e = end(t, s)
        if pred(t[s:e]):
            t = t[:s].rstrip("\t") + t[e:].lstrip("\n").join(["", ""]) if False else t[:m.start()] + t[e:]
            n += 1
    print(what, n); return n
assert cut(lambda b: b.startswith("(symbol") and '(property "Reference" "F6"' in b, "F6 symbol") == 1
assert cut(lambda b: b.startswith("(wire") and "464.82" in b and ("58.42" in b or "63.5 " in b or "55.88" in b or "66.04" in b), "F6 wires") == 2
assert cut(lambda b: b.startswith("(label") and "(at 464.82 " in b, "F6 labels") == 2
assert t.count('(label "VIN_FUSED"') == 1
t = t.replace('(label "VIN_FUSED"', '(label "VIN_5V"')
a = "J6 pin1 = +5V, pin2 = GND -> F6 (MF-R185) -> Q1 ideal diode -> +5V rail"
assert t.count(a) == 1
t = t.replace(a, "J6 pin1 = +5V, pin2 = GND -> Q1 reverse-polarity guard -> +5V rail (no fuse: F6 removed 2026-09-30)")
open(P, "w", encoding="utf-8", newline="\n").write(t)
