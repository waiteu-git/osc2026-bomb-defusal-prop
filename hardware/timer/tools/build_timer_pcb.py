# -*- coding: utf-8 -*-
"""ONE-SHOT builder of hardware/timer/timer.kicad_pcb from REAL library footprints (2026-09-30).

After this run the PCB is edited by hand in KiCad (Tools > Update PCB from Schematic keeps working);
do NOT run this again on a board that has routing or hand edits - it rebuilds every footprint.

Inputs : kicad-cli netlist of timer.kicad_sch (footprint, value, uuid path, pad nets per component)
         the previous timer.kicad_pcb (board setup, outline, keep-out markers; old pad positions to match placement)
Output : timer.kicad_pcb
usage  : python build_timer_pcb.py <netlist.net> <old.kicad_pcb> <out.kicad_pcb>
"""
import sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Program Files\KiCad\10.0\bin\Lib\site-packages")
os.add_dll_directory(r"C:\Program Files\KiCad\10.0\bin")
import pcbnew

NET, OLD, OUT = sys.argv[1:4]
PROJ = os.environ.get("TIMER_DIR", os.path.dirname(os.path.abspath(OUT)))   # folder holding Timer_Local.pretty
FPDIR = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
LIBS = {"Timer_Local": os.path.join(PROJ, "Timer_Local.pretty"),
        "RPi_Pico": r"C:/Users/ysou5/Documents/KiCad/10.0/3rdparty/KiCad-RP-Pico/RP-Pico Libraries/MCU_RaspberryPi_and_Boards.pretty"}
mm = pcbnew.ToMM
fm = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(fm(x), fm(y))

# ---------------------------------------------------------------- netlist (small s-expr reader)
def sexpr(text):
    tok = re.findall(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()"]+', text)
    pos = 0
    def rd():
        nonlocal pos
        t = tok[pos]; pos += 1
        if t == "(":
            out = []
            while tok[pos] != ")": out.append(rd())
            pos += 1
            return out
        return t[1:-1] if t.startswith('"') else t
    return rd()
def kids(node, name): return [k for k in node[1:] if isinstance(k, list) and k and k[0] == name]
def kid(node, name):
    r = kids(node, name); return r[0] if r else None

nl = sexpr(open(NET, encoding="utf-8").read())
comps = {}
for c in kids(kid(nl, "components"), "comp"):
    ref = kid(c, "ref")[1]
    fields = {kid(f, "name")[1]: (f[2] if len(f) > 2 else "") for f in kids(kid(c, "fields") or [], "field")}
    comps[ref] = dict(value=kid(c, "value")[1], fp=kid(c, "footprint")[1], uuid=kid(c, "tstamps")[1],
                      descr=(kid(c, "description") or ["", ""])[1], datasheet=fields.get("Datasheet", ""))
pad_net = {}                      # (ref, pin) -> net name
for n in kids(kid(nl, "nets"), "net"):
    name = kid(n, "name")[1]
    for nd in kids(n, "node"):
        pad_net[(kid(nd, "ref")[1], kid(nd, "pin")[1])] = name
netnames = sorted(set(pad_net.values()))

# ---------------------------------------------------------------- old board: outline, markers, old pad positions
b = pcbnew.LoadBoard(OLD)
old = {}
for f in b.GetFootprints():
    old[f.GetReference()] = dict(side=f.IsFlipped(), pos=f.GetPosition(),
                                 pads={p.GetNumber(): (mm(p.GetX()), mm(p.GetY())) for p in f.Pads() if p.GetNumber()})
for f in list(b.GetFootprints()): b.RemoveNative(f)
for n in list(b.GetNetsByName().values()):
    if n.GetNetCode() != 0: b.RemoveNative(n)
b.BuildListOfNets()

nets = {}
for name in netnames:
    it = pcbnew.NETINFO_ITEM(b, name); b.Add(it); nets[name] = it

# ---------------------------------------------------------------- footprint loading / placement
def load(fpid):
    lib, name = fpid.split(":")
    d = LIBS.get(lib, os.path.join(FPDIR, lib + ".pretty"))
    fp = pcbnew.FootprintLoad(d, name)
    if fp is None: raise SystemExit("footprint not found: " + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    b.Add(fp)                     # Flip() needs the footprint to belong to a board
    return fp

def orient(fp, side_back, rot):
    fp.SetPosition(V(0, 0)); fp.SetOrientationDegrees(0)
    if side_back and not fp.IsFlipped(): fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(rot)

def padmap(fp): return {p.GetNumber(): (mm(p.GetX()), mm(p.GetY())) for p in fp.Pads() if p.GetNumber()}
def centroid(pm):
    xs = [v[0] for v in pm.values()]; ys = [v[1] for v in pm.values()]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2

# placement table: ref -> (side, mode, args).  side 'F'/'B'
#   ('match', dx, dy)   rotation + position found by matching the previous board's pad positions, then shifted by dx,dy
#   ('at', x, y, rot)   bounding-box centre of the PAD set at x,y with a given rotation
PLACE = {}; SILK = []; REFPOS = {}
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "timer_placement.py"), encoding="utf-8").read())

report = []
for ref in sorted(comps, key=lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0))):
    c = comps[ref]
    fp = load(c["fp"])
    side, mode = PLACE[ref][0], PLACE[ref][1]
    back = side == "B"
    if mode == "match":
        _, _, dx, dy = PLACE[ref]
        o = old[ref]["pads"]; best = None
        for rot in (0, 90, 180, 270):
            orient(fp, back, rot)
            pm = padmap(fp); common = [k for k in pm if k in o]
            tx = sum(o[k][0] - pm[k][0] for k in common) / len(common); ty = sum(o[k][1] - pm[k][1] for k in common) / len(common)
            res = max(((o[k][0] - pm[k][0] - tx) ** 2 + (o[k][1] - pm[k][1] - ty) ** 2) ** .5 for k in common)
            if best is None or res < best[0] - 1e-6: best = (res, rot, tx, ty)
        res, rot, tx, ty = best
        orient(fp, back, rot); fp.SetPosition(V(tx + dx, ty + dy))
        report.append("%-3s match rot=%3d residual=%.2fmm" % (ref, rot, res))
    else:
        _, _, x, y, rot = PLACE[ref]
        orient(fp, back, rot)
        cx, cy = centroid(padmap(fp)); fp.SetPosition(V(x - cx, y - cy))
        report.append("%-3s at (%.2f,%.2f) rot=%d" % (ref, x, y, rot))
    fp.SetReference(ref); fp.SetValue(c["value"])
    fp.GetField("Description").SetText(c["descr"]); fp.GetField("Datasheet").SetText(c["datasheet"])   # as "Update PCB from Schematic" does
    fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
    try:
        fp.SetSheetname("Root"); fp.SetSheetfile("timer.kicad_sch")
    except Exception: pass
    for p in fp.Pads():
        k = (ref, p.GetNumber())
        if k in pad_net: p.SetNet(nets[pad_net[k]])

# extra: mounting holes are board-only footprints (no schematic symbol)
for i, (x, y) in enumerate([(9, 9), (71, 9), (9, 71), (71, 71)], 1):
    fp = load("Timer_Local:MountingHole_2.6mm")
    fp.SetFPID(pcbnew.LIB_ID("MountingHole", "MountingHole_2.6mm"))   # the shared corner keep-out rule exempts Library_Link 'MountingHole:*'
    fp.SetReference("H%d" % i); fp.SetValue("M2.6 hole (dia 2.6mm)")
    fp.SetPosition(V(x, y)); fp.SetBoardOnly(True)     # no schematic symbol -> not an "extra footprint" in the parity check

# reference designators: library default sits on top of neighbouring pads for some parts -> move each to a spot that touches no pad
def pad_boxes():
    out = []
    for f in b.GetFootprints():
        for p in f.Pads():
            bb = p.GetBoundingBox()
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) or p.GetLayerSet().Contains(pcbnew.F_Cu) or p.GetLayerSet().Contains(pcbnew.B_Cu):
                out.append((f.GetReference(), mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())))
    return out
BOXES = pad_boxes()
def hits(x, y, w, h):
    return any(not (x + w / 2 < l - .15 or x - w / 2 > r + .15 or y + h / 2 < t - .15 or y - h / 2 > bt + .15) for (_, l, t, r, bt) in BOXES)
for f in b.GetFootprints():
    ref = f.GetReference()
    if ref.startswith("H"): continue
    t = f.Reference()
    if ref in REFPOS:
        t.SetPosition(V(*REFPOS[ref])); continue
    w = 0.9 * len(ref) + 0.3; h = 1.2
    cur = (mm(t.GetPosition().x), mm(t.GetPosition().y))
    if not hits(cur[0], cur[1], w, h): continue
    bb = f.GetBoundingBox(False)
    cx, cy = mm(bb.GetCenter().x), mm(bb.GetCenter().y)
    L, R, T, Bt = mm(bb.GetLeft()), mm(bb.GetRight()), mm(bb.GetTop()), mm(bb.GetBottom())
    cands = [(cx, T - 1.0), (cx, Bt + 1.0), (L - w / 2 - 0.3, cy), (R + w / 2 + 0.3, cy)]
    cands += [(cx + dx, cy + dy) for dy in (0, -2.5, 2.5, -5, 5) for dx in (0, -4, 4, -8, 8, -12, 12)]
    for (x, y) in cands:
        if 1.0 < x < 79.0 and 1.0 < y < 79.0 and not hits(x, y, w, h):
            t.SetPosition(V(x, y)); break

# silkscreen for the battery input (back side, mirrored so it reads from the back)
def silk(text, x, y, size, layer=pcbnew.B_SilkS):
    t = pcbnew.PCB_TEXT(b); t.SetText(text); t.SetLayer(layer)
    t.SetPosition(V(x, y)); t.SetTextSize(pcbnew.VECTOR2I(fm(size), fm(size))); t.SetTextThickness(fm(0.15))
    t.SetMirrored(layer == pcbnew.B_SilkS); b.Add(t)
for (txt, x, y, size) in SILK: silk(txt, x, y, size)

b.Save(OUT)
print("\n".join(report))
print("saved", OUT, "footprints:", len(list(b.GetFootprints())), "nets:", len(nets))
