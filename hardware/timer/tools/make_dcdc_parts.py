# -*- coding: utf-8 -*-
"""Add the Akizuki AE-TPS63802 buck-boost module (20 x 13 mm, 4-pin 2.54mm header CN1) to the Timer_Local libraries:
   symbol  Timer_Local:AE-TPS63802       (VIN, GND, VOUT, EN)
   footprint Timer_Local:AE-TPS63802     (mounted flat on the 4 header pins + 1 plain dummy pin, module floats ~2.5mm)
Dimensions from the manual (AE-TPS63802.pdf p.2): pin column 1.8mm from the short edge, first pin 2.7mm from the long edge,
13 x 20 mm board, dummy (mechanical) pin on 2.54mm column 5 next to pin 1's row. Run once."""
import uuid, os
D = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\timer"
u = lambda: str(uuid.uuid4())

# ---------------------------------------------------------------- symbol
FONT = "(effects (font (size 1.27 1.27)))"
def prop(name, val, x, y, hide=False):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t%s\n\t\t)\n'
            % (name, val, x, y, "\t\t\t(hide yes)\n" if hide else "", FONT))
def pin(kind, x, y, ang, name, num):
    return ('\t\t\t(pin %s line\n\t\t\t\t(at %s %s %d)\n\t\t\t\t(length 5.08)\n\t\t\t\t(name "%s" %s)\n\t\t\t\t(number "%s" %s)\n\t\t\t)\n'
            % (kind, x, y, ang, name, FONT, num, FONT))
sym = ('\t(symbol "AE-TPS63802"\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n'
       '\t\t(duplicate_pin_numbers_are_jumpers no)\n'
       + prop("Reference", "U", 0, 7.62) + prop("Value", "AE-TPS63802", 0, -12.7)
       + prop("Footprint", "Timer_Local:AE-TPS63802", 0, 0, True)
       + prop("Datasheet", "https://akizukidenshi.com/goodsaffix/AE-TPS63802.pdf", 0, 0, True)
       + prop("Description", "Akizuki AE-TPS63802 buck-boost module (TI TPS63802): VIN 1.8-5.5V, VOUT 1.8-5.2V set by VR1, EN low = off", 0, 0, True)
       + '\t\t(symbol "AE-TPS63802_0_1"\n\t\t\t(rectangle (start -5.08 5.08) (end 5.08 -5.08)\n\t\t\t\t(stroke (width 0.254) (type default))\n\t\t\t\t(fill (type background))\n\t\t\t)\n\t\t)\n'
       + '\t\t(symbol "AE-TPS63802_1_1"\n'
       + pin("passive", -10.16, 2.54, 0, "VIN", 1)
       + pin("power_in", 0, -10.16, 90, "GND", 2)
       + pin("passive", 10.16, 2.54, 180, "VOUT", 3)
       + pin("input", -10.16, -2.54, 0, "EN", 4)
       + '\t\t)\n\t\t(embedded_fonts no)\n\t)\n')
p = D + r"\Timer_Local.kicad_sym"
lib = open(p, encoding="utf-8").read()
assert '(symbol "AE-TPS63802"' not in lib
k = lib.rstrip().rfind(")")
open(p, "w", encoding="utf-8", newline="\n").write(lib[:k].rstrip("\n") + "\n" + sym + ")\n")

# ---------------------------------------------------------------- footprint (origin = pad 1 = VIN, y grows downwards)
def fprop(name, val, x, y, layer, hide=False):
    return ('\t(property "%s" "%s"\n\t\t(at %s %s 0)\n\t\t(layer "%s")\n%s\t\t(uuid "%s")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n'
            % (name, val, x, y, layer, "\t\t(hide yes)\n" if hide else "", u()))
def rect(x0, y0, x1, y1, layer, w):
    return ('\t(fp_rect\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(stroke\n\t\t\t(width %s)\n\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n\t\t(layer "%s")\n\t\t(uuid "%s")\n\t)\n'
            % (x0, y0, x1, y1, w, layer, u()))
def pad(num, shape, x, y):
    return ('\t(pad "%s" thru_hole %s\n\t\t(at %s %s)\n\t\t(size 1.7 1.7)\n\t\t(drill 1.0)\n\t\t(layers "*.Cu" "*.Mask")\n\t\t(remove_unused_layers no)\n\t\t(uuid "%s")\n\t)\n'
            % (num, shape, x, y, u()))
fp = ('(footprint "AE-TPS63802"\n\t(version 20260206)\n\t(generator "pcbnew")\n\t(generator_version "10.0")\n\t(layer "F.Cu")\n'
      '\t(descr "Akizuki AE-TPS63802 buck-boost module 20x13mm on its 4-pin 2.54mm header CN1 (1 VIN, 2 GND, 3 VOUT, 4 EN) plus one plain dummy pin for support. '
      'The module floats about 2.5mm above the board, so low parts may sit under it. Courtyard = the two pin strips only; the module outline is on F.SilkS/F.Fab.")\n'
      '\t(tags "AE-TPS63802 buck boost module")\n'
      + fprop("Reference", "REF**", 9.0, -15.0, "F.SilkS")
      + fprop("Value", "AE-TPS63802", 9.0, 5.0, "F.Fab")
      + fprop("Datasheet", "https://akizukidenshi.com/goodsaffix/AE-TPS63802.pdf", 0, 0, "F.Fab", True)
      + fprop("Description", "Akizuki AE-TPS63802 buck-boost module", 0, 0, "F.Fab", True)
      + "\t(attr through_hole)\n\t(duplicate_pad_numbers_are_jumpers no)\n"
      + rect(-1.8, -10.3 - 2.7, 18.2, 2.7, "F.SilkS", 0.12)          # module outline 20 x 13: 1.8 left of pin 1, 2.7 below pin 1's row
      + rect(-1.8, -13.0, 18.2, 2.7, "F.Fab", 0.1)
      + rect(-1.5, -9.1, 1.5, 1.5, "F.CrtYd", 0.05)                  # pin strip
      + rect(8.66, -1.5, 11.66, 1.5, "F.CrtYd", 0.05)                # dummy pin
      + pad("1", "rect", 0, 0) + pad("2", "circle", 0, -2.54) + pad("3", "circle", 0, -5.08) + pad("4", "circle", 0, -7.62)
      + pad("", "circle", 10.16, 0) + ")\n")
open(D + r"\Timer_Local.pretty\AE-TPS63802.kicad_mod", "w", encoding="utf-8", newline="\n").write(fp)
print("done")
