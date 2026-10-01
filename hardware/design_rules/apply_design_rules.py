#!/usr/bin/env python3
"""OSC2026 shared PCB design rules for JLCPCB (2-layer, 1.6mm, 1oz).

Writes, per board project under hardware/:
  * <name>.kicad_dru  - custom rules (always safe to rewrite; KiCad never touches it on save)
  * <name>.kicad_pro  - board constraints, net classes (trace widths), net-class patterns, severities

A .kicad_pro that KiCad has open is NOT modified (KiCad rewrites it from memory on save and would
silently undo the edit). Close KiCad and re-run, or pass --force-pro.

Power / Power_Main classes and their patterns are owned by this script: every run resets them
(add extra rails to the NETS_* lists below instead of editing them in KiCad).

Usage: python apply_design_rules.py [--force-pro] [project ...]
Exit code: 0 ok, 2 a .kicad_pro was skipped (KiCad open), 3 a rule block could not be generated.
Spec and rationale: hardware/design_rules/design_rules.md
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DEFAULT_PROJECTS = ["button", "keypad", "simon", "complicated_wires", "timer", "four_button"]

# board.design_settings.rules, millimetres. Keys not listed here are left as they are.
# Numbers follow the legacy KiCad 7 values of the user's reference page, checked against JLCPCB's page.
RULES = {
    "min_clearance": 0.15,            # JLCPCB SMD pad-to-pad 0.15 (track-to-track 0.10); the netclasses are stricter
    "min_track_width": 0.127,         # JLCPCB 0.10 (+/-20%); 5 mil
    "min_connection": 0.0,
    "min_via_annular_width": 0.13,
    "min_via_diameter": 0.5,          # no-surcharge floor is 0.45 with 0.2/0.25 drill; with drill 0.3 this gives 0.56/0.3
    "min_hole_clearance": 0.33,       # JLCPCB PTH-to-track 0.28 min / 0.35 recommended
    "min_copper_edge_clearance": 0.3, # JLCPCB routed edge 0.2 (V-cut 0.4); 0.3 kept for the outline
    "min_through_hole_diameter": 0.3,
    "min_hole_to_hole": 0.45,         # JLCPCB PTH hole-to-hole 0.45
    "min_microvia_diameter": 0.2,
    "min_microvia_drill": 0.1,
    "min_text_height": 1.0,           # JLCPCB silkscreen height 1.0
    "min_text_thickness": 0.15,       # JLCPCB silkscreen line width 0.15
}
# KiCad reports hole_to_hole as a warning by default; 0.45 is a fab drill-spacing limit, so make it an error.
RULE_SEVERITIES = {"hole_to_hole": "error"}
# Defaults for NEW silkscreen items (only written when the project already has a 'defaults' block).
DEFAULTS_SILK = {"silk_line_width": 0.15, "silk_text_thickness": 0.15}

# Net classes: track_width/via are routing defaults (KiCad does not enforce them as DRC minimums,
# the .kicad_dru rules below do). Clearance is enforced by KiCad.
CLASS_DEFAULT = {"clearance": 0.2, "track_width": 0.25, "via_diameter": 0.8, "via_drill": 0.4}
CLASS_POWER = {"name": "Power", "priority": 1, "clearance": 0.2, "track_width": 0.5,
               "via_diameter": 0.8, "via_drill": 0.4}
CLASS_MAIN = {"name": "Power_Main", "priority": 0, "clearance": 0.3, "track_width": 1.0,
              "via_diameter": 1.0, "via_drill": 0.5}

# PCB net names vary (script-generated PCBs vs "Update PCB from Schematic": leading '/', +3.3V vs +3V3).
NETS_3V3 = ["+3.3V", "+3V3", "+3V3_H", "/+3V3_H"]   # +3V3_H = host Pico's separate 3.3V rail (timer board)
NETS_5V_LOAD = ["VCC_J*", "/VCC_J*", "TM_VDD", "/TM_VDD"]   # per-slot 5V branches, TM1637 supply
NETS_GND = ["GND"]

PROJECT_CFG = {
    # Status LED (green): the user decided on 2026-10-01 that it sits near the top-right corner on every module, so
    # the status LED of each board is exempt from the corner keep-out (button LED9, complicated_wires LED1,
    # four_button D5). Geometry (button, estimate): LED centre ~8.2 mm from hole H2, minus LED radius 1.75 and
    # screw head radius 2.5 leaves ~3.9 mm. complicated_wires: 7.6 mm from H2, ~2.2 mm margin (decided 2026-09-29).
    "button": {"panel": True, "corner_exceptions": ["LED9"]},
    "keypad": {"panel": True},
    "simon": {"panel": True},
    "complicated_wires": {"led_window_edge": True, "panel": True, "main_rail": [],
                          "corner_exceptions": ["LED1"]},
    "timer": {"panel": True, "main_rail": ["+5V"]},
    "four_button": {"panel": True, "corner_exceptions": ["D5"]},
}

WARNINGS = []


def pattern_assignments(cfg):
    main = cfg.get("main_rail", [])
    out = []
    for n in ["+5V"] + NETS_3V3 + NETS_5V_LOAD + NETS_GND:
        if n in main:
            continue
        out.append({"netclass": "Power", "pattern": n})
    for n in main:
        out.append({"netclass": "Power_Main", "pattern": n})
    return out


def _names(nets):
    return " || ".join("A.NetName == '%s'" % n for n in nets)


def _pcb(project):
    return os.path.join(HW, project, project + ".kicad_pcb")


def detect_panel(pcb_path):
    """(x0, y0) of the 80x80 panel = top-left of the Edge.Cuts outline; None if not found / not 80 wide."""
    if not os.path.exists(pcb_path):
        return None
    t = open(pcb_path, encoding="utf-8").read()
    xs, ys = [], []
    pat = (r'\((?:gr_rect|gr_line)\s(?:(?!\((?:gr_\w+|fp_\w+|footprint|segment|via|zone)\s).)*?'
           r'\(layer "Edge\.Cuts"\)')
    for blk in re.findall(pat, t, re.S):
        for x, y in re.findall(r'\((?:start|end)\s+([\-\d.]+)\s+([\-\d.]+)\)', blk):
            xs.append(float(x))
            ys.append(float(y))
    if not xs:
        return None
    if abs((max(xs) - min(xs)) - 80.0) > 0.05 or (max(ys) - min(ys)) < 79.95:
        return None
    return min(xs), min(ys)


def sk6812_refs(pcb_path):
    """References of SK6812MINI-E footprints (they carry their own Edge.Cuts light window)."""
    if not os.path.exists(pcb_path):
        return []
    t = open(pcb_path, encoding="utf-8").read()
    refs = []
    for m in re.finditer(r'\(footprint\s+"[^"]*SK6812MINI-E[^"]*"', t):
        r = re.search(r'\(property "Reference" "([^"]+)"', t[m.end():m.end() + 4000])
        if r:
            refs.append(r.group(1))
    return sorted(set(refs), key=lambda s: (len(s), s))


def _num(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


def corner_rules(x0, y0, exceptions=()):
    px = [x0, x0 + 12, x0 + 68, x0 + 80]
    py = [y0, y0 + 12, y0 + 68, y0 + 80]
    vals = [_num(v) for v in px + py]
    pad_ex = "".join(" && !A.memberOfFootprint('%s')" % r for r in exceptions)
    fp_ex = "".join(" && A.Reference != '%s'" % r for r in exceptions)
    cy_ex = "".join(" && !A.intersectsCourtyard('%s')" % r for r in exceptions)
    note = "".join("# Exception: %s (documented in design_rules.md)\n" % r for r in exceptions)
    xin = "((A.%s >= {0}mm && A.%s <= {1}mm) || (A.%s >= {2}mm && A.%s <= {3}mm))"
    yin = "((A.%s >= {4}mm && A.%s <= {5}mm) || (A.%s >= {6}mm && A.%s <= {7}mm))"

    def box(fx, fy):
        return (xin % (fx, fx, fx, fx) + " && " + yin % (fy, fy, fy, fy)).format(*vals)

    sx = (xin % (("Start_X",) * 4)).format(*vals)
    sy = (yin % (("Start_Y",) * 4)).format(*vals)
    ex = (xin % (("End_X",) * 4)).format(*vals)
    ey = (yin % (("End_Y",) * 4)).format(*vals)
    track = "(((%s) && (%s)) || ((%s) && (%s)))" % (sx, sy, ex, ey)
    pos = box("Position_X", "Position_Y")
    return (
        "# ---- corner keep-out: four 12 x 12 mm squares at the corners of the 80 x 80 mm panel ----\n"
        "# Only reference points are tested (pad/via centre, track end points, footprint origin).\n"
        "# Copper that merely reaches into a square from outside is not caught.\n"
        + note +
        '(rule "osc_corner_keepout_pad"\n\t(constraint disallow pad)\n'
        "\t(condition \"A.Type == 'Pad' && A.Pad_Type != 'NPTH, mechanical'%s && %s\"))\n\n"
        '(rule "osc_corner_keepout_via"\n\t(constraint disallow via)\n'
        "\t(condition \"A.Type == 'Via'%s && %s\"))\n\n"
        '(rule "osc_corner_keepout_track"\n\t(constraint disallow track)\n'
        "\t(condition \"A.Type == 'Track'%s && %s\"))\n\n"
        '(rule "osc_corner_keepout_footprint"\n\t(constraint disallow footprint)\n'
        "\t(condition \"A.Type == 'Footprint' && A.Library_Link != '*MountingHole*'%s && %s\"))\n"
    ) % (pad_ex, pos, cy_ex, pos, cy_ex, track, fp_ex, pos)


def build_dru(project):
    cfg = PROJECT_CFG.get(project, {})
    main = cfg.get("main_rail", [])
    parts = [
        "(version 1)\n\n"
        "# OSC2026 shared design rules for JLCPCB (2-layer, 1.6mm, 1oz). GENERATED by\n"
        "# hardware/design_rules/apply_design_rules.py - edit that script, not this file.\n"
        "# Syntax notes (KiCad 10.0.3): last matching rule of a constraint wins; no regex in conditions;\n"
        "# a parse error is NOT reported by kicad-cli (all rules silently dropped) - run check_design_rules.py.\n\n"
        '(rule "osc_3v3_min_track_0p3"\n\t(constraint track_width (min 0.3mm))\n'
        "\t(condition \"%s\"))\n\n" % _names(NETS_3V3)
        + '(rule "osc_power_min_track_0p5"\n\t(constraint track_width (min 0.5mm))\n'
        "\t(condition \"%s\"))\n\n" % _names(["+5V"] + NETS_5V_LOAD)
    ]
    if main:
        parts.append('(rule "osc_main_rail_min_track_1p0"\n\t(constraint track_width (min 1.0mm))\n'
                     "\t(condition \"%s\"))\n\n" % _names(main))
    parts.append(
        '(rule "osc_pth_min_ring_0p18"\n\t(constraint annular_width (min 0.18mm))\n'
        "\t(condition \"A.Type == 'Pad' && A.isPlated()\"))\n\n"
        '(rule "osc_pth_min_drill_0p5"\n\t(constraint hole_size (min 0.5mm))\n'
        "\t(condition \"A.Type == 'Pad' && A.isPlated()\"))\n\n"
        '(rule "osc_npth_min_drill_0p5"\n\t(constraint hole_size (min 0.5mm))\n'
        "\t(condition \"A.Type == 'Pad' && A.Pad_Type == 'NPTH, mechanical'\"))\n\n"
    )
    if cfg.get("led_window_edge"):
        refs = sk6812_refs(_pcb(project))
        if refs:
            cond = " || ".join("A.memberOfFootprint('%s')" % r for r in refs)
            parts.append(
                "# SK6812MINI-E reverse-mount footprints (%s) carry their own Edge.Cuts light window,\n"
                "# 0.2467 mm from the pads; JLCPCB's routed-edge floor is 0.2 mm.\n"
                '(rule "osc_led_window_edge"\n\t(constraint edge_clearance (min 0.2mm))\n'
                "\t(condition \"A.Type == 'Pad' && (%s)\"))\n\n" % (", ".join(refs), cond))
        elif os.path.exists(_pcb(project)):
            WARNINGS.append("%s: no SK6812MINI-E footprints found - osc_led_window_edge not generated" % project)
    if cfg.get("panel"):
        origin = detect_panel(_pcb(project))
        if origin:
            parts.append(corner_rules(origin[0], origin[1], cfg.get("corner_exceptions", [])))
        elif os.path.exists(_pcb(project)):
            WARNINGS.append("%s: corner keep-out NOT generated (no 80 mm wide Edge.Cuts outline found)" % project)
            parts.append("# corner keep-out: NOT generated (no 80 mm wide Edge.Cuts outline found in the PCB)\n")
        else:
            parts.append("# corner keep-out: generated once the PCB exists (re-run apply_design_rules.py)\n")
    return "".join(parts)


def write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def is_open_in_kicad(project_dir, name):
    pat = os.path.join(glob.escape(project_dir), "~%s.*.lck" % glob.escape(name))
    return bool(glob.glob(pat))


def apply_pro(path):
    j = json.load(open(path, encoding="utf-8"))
    ds = j.setdefault("board", {}).setdefault("design_settings", {})
    ds.setdefault("rules", {}).update(RULES)
    ds.setdefault("rule_severities", {}).update(RULE_SEVERITIES)
    if ds.get("defaults"):
        ds["defaults"].update(DEFAULTS_SILK)
    ns = j.setdefault("net_settings", {})
    classes = ns.setdefault("classes", [])
    full = {"bus_width": 12, "clearance": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
            "tuning_profile": "", "wire_width": 6}
    by_name = {c.get("name"): c for c in classes}
    if "Default" not in by_name:
        d = dict(full)
        d.update({"name": "Default", "priority": 2147483647, "track_width": 0.2,
                  "via_diameter": 0.6, "via_drill": 0.3})
        classes.insert(0, d)
        by_name["Default"] = d
    by_name["Default"].update(CLASS_DEFAULT)
    for spec in (CLASS_POWER, CLASS_MAIN):
        c = by_name.get(spec["name"])
        if c is None:
            c = dict(full)
            classes.append(c)
        c.update(spec)
    return j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-pro", action="store_true", help="edit .kicad_pro even if KiCad has it open")
    ap.add_argument("projects", nargs="*")
    a = ap.parse_args()
    status = 0
    for p in a.projects or DEFAULT_PROJECTS:
        d = os.path.join(HW, p)
        pro = os.path.join(d, p + ".kicad_pro")
        if not os.path.exists(pro):
            print("%-18s ERROR: no project file %s" % (p, pro))
            status = max(status, 3)
            continue
        write_atomic(os.path.join(d, p + ".kicad_dru"), build_dru(p))
        msg = ".kicad_dru written"
        if is_open_in_kicad(d, p) and not a.force_pro:
            msg += "; .kicad_pro NOT changed (KiCad has it open - close KiCad and re-run)"
            status = max(status, 2)
        else:
            j = apply_pro(pro)
            bak = pro + ".bak"
            if not os.path.exists(bak):
                shutil.copyfile(pro, bak)
            cfg = PROJECT_CFG.get(p, {})
            ns = j["net_settings"]
            keep = [x for x in (ns.get("netclass_patterns") or [])
                    if x.get("netclass") not in ("Power", "Power_Main")]
            ns["netclass_patterns"] = keep + pattern_assignments(cfg)
            write_atomic(pro, json.dumps(j, ensure_ascii=False, indent=2) + "\n")
            msg += "; .kicad_pro updated"
        print("%-18s %s" % (p, msg))
    for w in WARNINGS:
        print("WARNING:", w)
        status = max(status, 3)
    return status


if __name__ == "__main__":
    sys.exit(main())
