# -*- coding: utf-8 -*-
"""Point U1/U3 at Timer_Local:RPi_Pico_TH_Headers (property text only)."""
import re, sys
PATH = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\timer\timer.kicad_sch"
t = open(PATH, encoding="utf-8").read()
old = '(property "Footprint" "RPi_Pico:RPi_Pico_SMD_TH"'
new = '(property "Footprint" "Timer_Local:RPi_Pico_TH_Headers"'
# only inside the two placed symbols (lib_symbols keep the library's own default)
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
n = 0
for m in list(re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "RPi_Pico:Pico"\)', t))[::-1]:
    s = m.start() + 2; e = end(t, s); b = t[s:e]
    assert b.count(old) == 1, b[:80]
    t = t[:s] + b.replace(old, new) + t[e:]; n += 1
print("patched", n)
open(PATH, "w", encoding="utf-8", newline="\n").write(t)
