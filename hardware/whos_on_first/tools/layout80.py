# -*- coding: utf-8 -*-
"""80mm-square panel layout check + ASCII render for Who's on First.
Coordinates: mm, origin top-left, x right, y down. Panel = 80 x 80.

2026-09-27(2): TFT->OLED change (hub decision, "再現の方針"). Replaces the old
TFT-based model. OLED data: 0.96in 128x64 SSD1315, Akizuki #112031, exterior
27 x 24.7mm per the maze module's design notes (maze_design_notes.md; a second
source lists 26x26mm for the same part - flagged as unconfirmed, see design
notes §1.7). Active area 21.74 x 10.86mm (0.17mm/px, 128x64) - NOT measured
from this session's own datasheet (no OLED datasheet opened here yet), so the
vertical offset of the active area within the PCB is an ESTIMATE (header
assumed along the bottom edge, like most 0.96in I2C OLED breakouts) and is
flagged as an open item pending the physical part.
Buttons: 12mm standard tact + standard cap (Akizuki TVGP01-G73BB), replacing
the old 6mm+custom-elongated-cap hack - that hack existed only to match the
switch row pitch to the TFT's on-screen label rows, which no longer exist
(button words are fixed printed caps now, not on-screen text).
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PANEL = 80.0
KEEP = 15.0  # corner keep-out square (covers a 10mm hole whose centre is <=10mm from both edges)

# ---- OLED (display) ----
PCB_W, PCB_H = 27.0, 24.7
AA_W, AA_H = 21.74, 10.86
CX = 40.0                          # horizontal centre
PCB_X0 = CX - PCB_W / 2            # 26.5
PCB_Y0 = 18.14                     # same top-edge convention as the old TFT layout
AA_DX = (PCB_W - AA_W) / 2         # 2.63, active area centred horizontally (assumption)
AA_DY = 2.5                        # ESTIMATE: header assumed along PCB bottom edge (unconfirmed)
AA_X0, AA_Y0 = PCB_X0 + AA_DX, PCB_Y0 + AA_DY
WIN_MARGIN = 0.4                   # bezel opening slightly larger than AA

# ---- elements: name -> (x0, y0, x1, y1) ----
E = {}
E["OLED_PCB(behind)"] = (PCB_X0, PCB_Y0, PCB_X0 + PCB_W, PCB_Y0 + PCB_H)
E["OLED_window"] = (AA_X0 - WIN_MARGIN, AA_Y0 - WIN_MARGIN, AA_X0 + AA_W + WIN_MARGIN, AA_Y0 + AA_H + WIN_MARGIN)

# 12mm tact + standard cap. Row pitch no longer needs to match an on-screen
# label pitch (buttons carry fixed printed word caps), so rows are spaced for
# comfortable finger clearance instead.
CAP_W, CAP_H = 12.0, 12.0
LX, RX = 15.0, 63.0
ROW_P = 15.0
row_centres = [27.0 + ROW_P * i for i in range(3)]   # 27, 42, 57
names = [("TL", LX, 0), ("TR", RX, 0), ("ML", LX, 1), ("MR", RX, 1), ("BL", LX, 2), ("BR", RX, 2)]
for n, x, r in names:
    yc = row_centres[r]
    E["cap_" + n] = (x - CAP_W / 2, yc - CAP_H / 2, x + CAP_W / 2, yc + CAP_H / 2)

for i, x in enumerate((32.0, 40.0, 48.0), start=1):
    E["stageLED%d(5mm)" % i] = (x - 2.5, 9.0 - 2.5, x + 2.5, 9.0 + 2.5)
E["statusLED(3mm)"] = (74.0 - 1.5, 20.0 - 1.5, 74.0 + 1.5, 20.0 + 1.5)
E["JST_XH(behind)"] = (40.0 - 6.15, 74.0 - 2.9, 40.0 + 6.15, 74.0 + 2.9)

KEEPS = {
    "keep_TL": (0, 0, KEEP, KEEP),
    "keep_TR": (PANEL - KEEP, 0, PANEL, KEEP),
    "keep_BL": (0, PANEL - KEEP, KEEP, PANEL),
    "keep_BR": (PANEL - KEEP, PANEL - KEEP, PANEL, PANEL),
}

def inter(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

def gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0)
    dy = max(b[1] - a[3], a[1] - b[3], 0)
    return (dx * dx + dy * dy) ** 0.5

if __name__ == "__main__":
    print("row centres (mm):", [round(v, 2) for v in row_centres])
    print("AA:", [round(v, 2) for v in (AA_X0, AA_Y0, AA_X0 + AA_W, AA_Y0 + AA_H)])
    ok = True
    for k, r in E.items():
        if r[0] < 0 or r[1] < 0 or r[2] > PANEL or r[3] > PANEL:
            print("OUT OF PANEL:", k, r); ok = False
    for k, r in E.items():
        for kk, kr in KEEPS.items():
            if inter(r, kr):
                print("KEEP-OUT HIT:", k, kk); ok = False
    keys = list(E)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            if {a, b} == {"OLED_PCB(behind)", "OLED_window"}:
                continue
            if inter(E[a], E[b]):
                print("OVERLAP:", a, b); ok = False
    print("ALL OK" if ok else "PROBLEMS FOUND")

    def show(a, b):
        print("gap %-18s <-> %-18s = %.2f mm" % (a, b, gap(E[a], E[b])))
    show("cap_TL", "OLED_PCB(behind)")
    show("cap_TR", "OLED_PCB(behind)")
    show("cap_TL", "cap_ML")
    show("cap_ML", "cap_BL")
    show("stageLED1(5mm)", "OLED_PCB(behind)")
    show("statusLED(3mm)", "cap_TR")
    show("JST_XH(behind)", "OLED_PCB(behind)")
    show("cap_BL", "JST_XH(behind)")
    print("status LED to top keep-out edge: y=%.2f (keep-out ends y=15)" % E["statusLED(3mm)"][1])
    print("tightest edge margin among front items (to panel edge):")
    for k, r in E.items():
        m = min(r[0], r[1], PANEL - r[2], PANEL - r[3])
        print("   %-18s %.2f" % (k, m))

    print("\nsensitivity: hole centre distance from panel edge -> gap to nearest part (status LED, top-right corner)")
    # nearest corner part to the top-right hole is the status LED
    slx0, sly0, slx1, sly1 = E["statusLED(3mm)"]
    for d in (5.0, 7.5, 10.0, 12.5):
        # hole assumed on the diagonal, distance d from both edges (square keep-out approx already used)
        # remaining clearance from a Ø10 hole edge (radius 5) to the status LED's nearest edge
        hole_cx, hole_cy = PANEL - d, d
        import math
        # closest point on statusLED rect to hole centre
        cx_ = min(max(hole_cx, slx0), slx1)
        cy_ = min(max(hole_cy, sly0), sly1)
        dist = math.hypot(hole_cx - cx_, hole_cy - cy_) - 5.0
        print("  hole centre %.1fmm from edge -> hole edge to status LED = %.2fmm" % (d, dist))

    with open("layout_oled_check.txt", "w", encoding="utf-8") as f:
        pass
