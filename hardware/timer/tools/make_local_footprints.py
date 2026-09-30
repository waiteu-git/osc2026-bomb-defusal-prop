# -*- coding: utf-8 -*-
"""Create the project-local footprints that the KiCad standard libraries do not have:
   Timer_Local:MF-RX030_Radial_P5.10mm, Timer_Local:MF-R185_Radial_P5.10mm (upright PTC fuses),
   Timer_Local:MountingHole_2.6mm (NPTH 2.6mm, hub decision 2026-09-29)."""
import uuid, os

OUT = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\timer\Timer_Local.pretty"
u = lambda: str(uuid.uuid4())

def prop(name, value, x, y, layer, hide=False):
    h = "\n\t\t(hide yes)" if hide else ""
    return (f'\t(property "{name}" "{value}"\n\t\t(at {x} {y} 0)\n\t\t(layer "{layer}"){h}\n\t\t(uuid "{u()}")\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n')

def rect(x0, y0, x1, y1, layer, w):
    return (f'\t(fp_rect\n\t\t(start {x0} {y0})\n\t\t(end {x1} {y1})\n\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type solid)\n\t\t)\n'
            f'\t\t(fill no)\n\t\t(layer "{layer}")\n\t\t(uuid "{u()}")\n\t)\n')

def pad(num, shape, x, y, size, drill):
    return (f'\t(pad "{num}" thru_hole {shape}\n\t\t(at {x} {y})\n\t\t(size {size} {size})\n\t\t(drill {drill})\n'
            f'\t\t(layers "*.Cu" "*.Mask")\n\t\t(remove_unused_layers no)\n\t\t(uuid "{u()}")\n\t)\n')

def head(name, descr, tags):
    return (f'(footprint "{name}"\n\t(version 20260206)\n\t(generator "pcbnew")\n\t(generator_version "10.0")\n\t(layer "F.Cu")\n'
            f'\t(descr "{descr}")\n\t(tags "{tags}")\n')

def fuse(name, descr, body_w, thick, height, datasheet):
    x0, x1 = 2.55 - body_w / 2, 2.55 + body_w / 2
    s = head(name, descr, "PTC resettable fuse polyfuse radial Bourns MF-R")
    s += prop("Reference", "REF**", 2.55, -thick / 2 - 1.6, "F.SilkS")
    s += prop("Value", name, 2.55, thick / 2 + 1.6, "F.Fab")
    s += prop("Datasheet", datasheet, 0, 0, "F.Fab", True)
    s += prop("Description", f"{descr} (mounted upright, height about {height}mm above the board)", 0, 0, "F.Fab", True)
    s += "\t(attr through_hole)\n\t(duplicate_pad_numbers_are_jumpers no)\n"
    s += rect(round(x0, 2), -thick / 2, round(x1, 2), thick / 2, "F.SilkS", 0.12)
    s += rect(round(x0 - 0.25, 2), -thick / 2 - 0.25, round(x1 + 0.25, 2), thick / 2 + 0.25, "F.CrtYd", 0.05)
    s += pad("1", "rect", 0, 0, 1.7, 0.9)
    s += pad("2", "circle", 5.1, 0, 1.7, 0.9)
    s += ")\n"
    return s

files = {
    "MF-RX030_Radial_P5.10mm.kicad_mod": fuse(
        "MF-RX030_Radial_P5.10mm", "Bourns MF-RX030/72-0 PTC resettable fuse, lead pitch 5.1mm, body max 7.4 x 3.1mm",
        7.4, 3.1, 13.4, "https://www.bourns.com/docs/product-datasheets/mf-rx72.pdf"),
    "MF-R185_Radial_P5.10mm.kicad_mod": fuse(
        "MF-R185_Radial_P5.10mm", "Bourns MF-R185 PTC resettable fuse (1.85A hold), lead pitch 5.1mm, body max 12.0 x 3.0mm",
        12.0, 3.0, 18.4, "https://www.bourns.com/docs/product-datasheets/mf-r.pdf"),
}

mh = head("MountingHole_2.6mm", "Mounting hole, NPTH 2.6mm (OSC2026 panel: 4 corners, 9mm inset, 62mm pitch)", "mounting hole 2.6mm")
mh += prop("Reference", "REF**", 0, -3, "F.SilkS")
mh += prop("Value", "MountingHole_2.6mm", 0, 3, "F.Fab")
mh += prop("Datasheet", "", 0, 0, "F.Fab", True)
mh += prop("Description", "Mounting hole, NPTH 2.6mm", 0, 0, "F.Fab", True)
mh += "\t(attr board_only exclude_from_pos_files exclude_from_bom)\n\t(duplicate_pad_numbers_are_jumpers no)\n"
mh += (f'\t(fp_circle\n\t\t(center 0 0)\n\t\t(end 1.45 0)\n\t\t(stroke\n\t\t\t(width 0.12)\n\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n'
       f'\t\t(layer "F.SilkS")\n\t\t(uuid "{u()}")\n\t)\n')
mh += rect(-1.55, -1.55, 1.55, 1.55, "F.CrtYd", 0.05)
mh += (f'\t(pad "" np_thru_hole circle\n\t\t(at 0 0)\n\t\t(size 2.6 2.6)\n\t\t(drill 2.6)\n\t\t(layers "*.Cu" "*.Mask")\n'
       f'\t\t(uuid "{u()}")\n\t)\n)\n')
files["MountingHole_2.6mm.kicad_mod"] = mh

for fn, txt in files.items():
    with open(os.path.join(OUT, fn), "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    print("wrote", fn)
