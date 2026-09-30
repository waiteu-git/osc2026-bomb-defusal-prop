# -*- coding: utf-8 -*-
"""Timer_Local:RPi_Pico_TH_Headers - the community RPi_Pico_SMD_TH footprint reduced to what a Pico 2 H on 2.54mm
header pins needs on THIS board (two Picos share the 80x80 face):
  * keeps the 40 THT header pads (same numbers/positions -> schematic symbol RPi_Pico:Pico unchanged)
  * drops the 40 SMD castellation pads (they reach 1.75mm outside the module and short two stacked Picos)
  * drops the 4 NPTH pegs (nothing enters the board there) and the 0.8mm pin-name silk texts (unreadable when stacked)
  * pads 41-43 (SWD): kept as small F.Cu SMD pads without holes so the netlist still finds them (schematic parity);
    a Pico H has a top-side JST debug socket, nothing is soldered through the board there
  * courtyard = the two header strips only (the module body floats 2.5mm above the board)"""
import re, sys
SRC = r"C:/Users/ysou5/Documents/KiCad/10.0/3rdparty/KiCad-RP-Pico/RP-Pico Libraries/MCU_RaspberryPi_and_Boards.pretty/RPi_Pico_SMD_TH.kicad_mod"
OUT = sys.argv[1]
t = open(SRC, encoding="utf-8").read()

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

body_start = t.index("(footprint") ; out = []; i = t.index("\n", body_start)
head = t[:i]                         # "(footprint ... (generator pcbnew)"
pos = i; keep = []
while True:
    m = re.compile(r"\n\s*\(").search(t, pos)
    if not m: break
    s = m.end() - 1; e = end(t, s); blk = t[s:e]; pos = e
    if blk.startswith("(pad "):
        if "np_thru_hole" in blk or " smd " in blk: continue
        if int(re.match(r'\(pad "(\d+)"', blk).group(1)) >= 41: continue          # replaced below
    if blk.startswith("(fp_text user"): continue
    if blk.startswith("(fp_line") and '"F.CrtYd"' in blk: continue
    if blk.startswith("(fp_text value"): blk = blk.replace("RPi_Pico_SMD_TH", "RPi_Pico_TH_Headers")
    keep.append("@@DESCR@@" if blk.startswith("(descr") else blk)
new = ["(fp_circle (center %s 23.9) (end %s 24.4) (layer \"F.Fab\") (width 0.1) (fill none))" % (x, x)   # SWD holes of the module: marks only, NOT pads
       for x in ("-2.54", "0", "2.54")]
for x0, x1 in ((-10.0, -7.79), (7.79, 10.0)):
    new.append('(fp_rect (start %s -25.4) (end %s 25.4) (layer "F.CrtYd") (width 0.05) (fill none))' % (x0, x1))
descr = ('(descr "Raspberry Pi Pico 2 H on 2x20 2.54mm header pins, THT pads only; SWD and castellation pads do not touch the board (floating mount): no pads 41-43, SWD positions are F.Fab marks only; flashing is USB (BOOTSEL) only. '
         'The module FLOATS about 2.5mm above the board (header plastic standoff; 3D model raised by that amount). '
         'Courtyard = the two header-pin strips only, so LOW parts (front-side SMD / lead stubs, roughly <=2mm) may sit under the module body; '
         'the body outline is on F.Fab (not courtyard) because courtyards_overlap is a 2D check. OSC2026 timer board variant of RPi_Pico_SMD_TH")')
MODEL = ('(model "${KICAD10_3RD_PARTY}/KiCad-RP-Pico/RP-Pico Libraries/Pico.wrl"\n'
         '    (offset (xyz 0 0 2.5))\n    (scale (xyz 1 1 1))\n    (rotate (xyz 0 0 0))\n  )')   # body floats 2.5mm above the board
txt = head.replace("(footprint \"RPi_Pico_SMD_TH\"", "(footprint \"RPi_Pico_TH_Headers\"") + "\n"
txt = re.sub(r'\n\s*\(descr [^\n]*\)', "\n  " + descr, txt) if "(descr" in txt else txt
body = "\n  ".join([k for k in keep if not k.startswith("(model")] + new + [MODEL])
body = body.replace("@@DESCR@@", descr)
out = txt + "  " + body + "\n)\n"
open(OUT, "w", encoding="utf-8", newline="\n").write(out)
print("wrote", OUT, len(keep), "kept +", len(new), "new")
