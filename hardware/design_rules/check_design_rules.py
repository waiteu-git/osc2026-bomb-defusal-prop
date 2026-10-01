#!/usr/bin/env python3
"""Verify the OSC2026 shared design rules on every board project (read-only for the project files).

Per project it checks:
  1. <name>.kicad_dru equals what apply_design_rules.py generates (and has no BOM);
  2. <name>.kicad_pro carries constraints, severities, net classes and net-class patterns;
  3. (PCB present) kicad-cli DRC on the real PCB: any error-severity violation fails;
  4. (PCB present) a probe: one violating item per generated rule is inserted into a TEMP COPY of the PCB and
     every rule must fire - kicad-cli 10.0.3 silently ignores a broken .kicad_dru, so this is the real syntax check;
  5. (PCB present, panel boards) mounting holes H1-H4: NPTH, drill 2.6, 9 mm from the panel edges (62 mm pitch).

Usage: python check_design_rules.py [--no-drc] [--parity] [project ...]
"""
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apply_design_rules as A  # noqa: E402

KC = shutil.which("kicad-cli") or r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"


def run_drc(pcb, out_json, extra=()):
    subprocess.run([KC, "pcb", "drc", "--format", "json", "--severity-all", "--all-track-errors",
                    "--units", "mm", "-o", out_json] + list(extra) + [pcb], capture_output=True)
    if not os.path.exists(out_json):
        return None
    return json.load(open(out_json, encoding="utf-8", errors="replace"))


def check_pro(pro, project):
    j = json.load(open(pro, encoding="utf-8"))
    ds = j.get("board", {}).get("design_settings", {})
    rules = ds.get("rules", {})
    bad = ["%s=%s (want %s)" % (k, rules.get(k), v) for k, v in A.RULES.items()
           if abs(float(rules.get(k, -1)) - v) > 1e-9]
    for k, v in A.RULE_SEVERITIES.items():
        if ds.get("rule_severities", {}).get(k) != v:
            bad.append("severity %s != %s" % (k, v))
    cls = {c["name"]: c for c in j.get("net_settings", {}).get("classes", [])}
    for spec in (A.CLASS_POWER, A.CLASS_MAIN):
        c = cls.get(spec["name"])
        for k, v in spec.items():
            if not c or c.get(k) != v:
                bad.append("class %s.%s != %s" % (spec["name"], k, v))
    d = cls.get("Default", {})
    for k, v in A.CLASS_DEFAULT.items():
        if abs(d.get(k, -1) - v) > 1e-9:
            bad.append("Default.%s=%s (want %s)" % (k, d.get(k), v))
    have = sorted((x["netclass"], x["pattern"]) for x in j.get("net_settings", {}).get("netclass_patterns") or []
                  if x.get("netclass") in ("Power", "Power_Main"))
    want = sorted((x["netclass"], x["pattern"]) for x in A.pattern_assignments(A.PROJECT_CFG.get(project, {})))
    if have != want:
        bad.append("netclass_patterns differ from the generated set")
    return bad


def netref(t, name):
    """(form for segment/via, form for pad) following the PCB's own convention, or None."""
    m = re.search(r'\(net\s+(\d+)\s+"%s"\)' % re.escape(name), t)
    if m:
        return "(net %s)" % m.group(1), '(net %s "%s")' % (m.group(1), name)
    if '(net "%s")' % name in t:
        return '(net "%s")' % name, '(net "%s")' % name
    return None


def _u():
    return str(uuid.uuid4())


def seg(x1, y1, x2, y2, w, net):
    return ('\t(segment\n\t\t(start %s %s)\n\t\t(end %s %s)\n\t\t(width %s)\n\t\t(layer "F.Cu")\n\t\t%s\n'
            '\t\t(uuid "%s")\n\t)\n' % (x1, y1, x2, y2, w, net, _u()))


def via(x, y, net):
    return ('\t(via\n\t\t(at %s %s)\n\t\t(size 0.8)\n\t\t(drill 0.4)\n\t\t(layers "F.Cu" "B.Cu")\n\t\t%s\n'
            '\t\t(uuid "%s")\n\t)\n' % (x, y, net, _u()))


def fp(ref, x, y, pad_kind, dx, size, drill, net):
    netpart = "\n\t\t\t%s" % net if net else ""
    return ('\t(footprint "OscProbe:P"\n\t\t(layer "F.Cu")\n\t\t(uuid "%s")\n\t\t(at %s %s)\n'
            '\t\t(property "Reference" "%s"\n\t\t\t(at 0 0 0)\n\t\t\t(layer "F.SilkS")\n\t\t\t(uuid "%s")\n'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1 1)\n\t\t\t\t\t(thickness 0.15)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
            '\t\t(attr through_hole)\n'
            '\t\t(pad "1" %s circle\n\t\t\t(at %s 0)\n\t\t\t(size %s %s)\n\t\t\t(drill %s)\n'
            '\t\t\t(layers "*.Cu" "*.Mask")%s\n\t\t\t(uuid "%s")\n\t\t)\n\t)\n'
            % (_u(), x, y, ref, _u(), pad_kind, dx, size, size, drill, netpart, _u()))


def probe_geometry(project, t, rule_names):
    """One violating item per rule; returns (text_to_inject, list_of_rules_that_could_not_be_probed)."""
    frag, missing = "", []
    origin = A.detect_panel(A._pcb(project))
    n3 = next((netref(t, n) for n in A.NETS_3V3 if netref(t, n)), None)
    n5 = netref(t, "+5V")
    nv = netref(t, "VCC_J1") or netref(t, "/VCC_J1") or n5
    gnd = netref(t, "GND")
    plan = {
        "osc_3v3_min_track_0p3": (n3, lambda n: seg(-100, -100, -90, -100, 0.2, n[0])),
        "osc_power_min_track_0p5": (nv, lambda n: seg(-100, -110, -90, -110, 0.2, n[0])),
        "osc_main_rail_min_track_1p0": (n5, lambda n: seg(-100, -120, -90, -120, 0.6, n[0])),
        "osc_pth_min_ring_0p18": (gnd, lambda n: fp("ZR1", -60, -60, "thru_hole", 0, 0.9, 0.6, n[1])),
        "osc_pth_min_drill_0p5": (gnd, lambda n: fp("ZD1", -60, -70, "thru_hole", 0, 1.6, 0.4, n[1])),
        "osc_npth_min_drill_0p5": (("", ""), lambda n: fp("ZN1", -60, -80, "np_thru_hole", 0, 0.4, 0.4, None)),
    }
    if origin:
        x0, y0 = origin
        plan.update({
            "osc_corner_keepout_via": (gnd, lambda n: via(x0 + 2, y0 + 2, n[0])),
            "osc_corner_keepout_track": (gnd, lambda n: seg(x0 + 1, y0 + 6, x0 + 1.5, y0 + 6, 0.25, n[0])),
            "osc_corner_keepout_pad": (gnd, lambda n: fp("ZP1", x0 + 14, y0 + 74, "thru_hole", -10, 1.6, 0.9, n[1])),
            "osc_corner_keepout_footprint": (gnd, lambda n: fp("ZF1", x0 + 76, y0 + 74, "thru_hole", -10, 1.6, 0.9, n[1])),
        })
    for rule, (net, mk) in plan.items():
        if rule not in rule_names:
            continue
        if net is None:
            missing.append(rule)
            continue
        frag += mk(net)
    return frag, missing


def probe(project, workdir):
    pcb = A._pcb(project)
    t = open(pcb, encoding="utf-8").read()
    dru_path = os.path.join(A.HW, project, project + ".kicad_dru")
    names = set(re.findall(r'\(rule "(osc_[a-z0-9_]+)"', open(dru_path, encoding="utf-8").read()))
    frag, cannot = probe_geometry(project, t, names)
    d = os.path.join(workdir, "probe_" + project)
    os.makedirs(d, exist_ok=True)
    t2 = t.rstrip()
    assert t2.endswith(")")
    open(os.path.join(d, project + ".kicad_pcb"), "w", encoding="utf-8", newline="\n").write(t2[:-1] + frag + ")\n")
    for ext in (".kicad_pro", ".kicad_dru"):
        shutil.copyfile(os.path.join(A.HW, project, project + ext), os.path.join(d, project + ext))
    out = os.path.join(d, "probe.json")
    j = run_drc(os.path.join(d, project + ".kicad_pcb"), out)
    if j is None:
        return "FAIL: kicad-cli produced no report for the probe board"
    fired = set(re.findall(r"osc_[a-z0-9_]+", open(out, "rb").read().decode("utf-8", errors="replace")))
    observable = names - {"osc_led_window_edge"}
    problems = sorted(observable - fired)
    if cannot:
        problems += ["%s (no suitable net in the PCB to probe it)" % c for c in cannot]
    if A.PROJECT_CFG.get(project, {}).get("panel") and A.detect_panel(pcb) and \
            not any(n.startswith("osc_corner_keepout_") for n in names):
        problems.append("osc_corner_keepout_* missing from the .kicad_dru")
    if problems:
        return "FAIL: rules that did not fire / are missing: %s" % ", ".join(problems)
    return "OK (%d rules fired on a probe board)" % len(observable)


def check_holes(project):
    pcb = A._pcb(project)
    origin = A.detect_panel(pcb)
    if not origin:
        return "SKIP (no 80 mm panel outline)"
    t = open(pcb, encoding="utf-8").read()
    found = {}
    for blk in re.split(r"\n\t\(footprint ", t)[1:]:
        r = re.search(r'\(property "Reference" "(H\d+)"', blk)
        if not r:
            continue
        at = re.search(r"\(at\s+([\-\d.]+)\s+([\-\d.]+)", blk)
        ok = "np_thru_hole" in blk and re.search(r"\(drill 2\.6\)", blk) is not None
        found[r.group(1)] = (float(at.group(1)) - origin[0], float(at.group(2)) - origin[1], ok)
    want = [(9, 9), (71, 9), (9, 71), (71, 71)]
    got = sorted((round(x, 2), round(y, 2)) for x, y, _ in found.values())
    if got != sorted(want) or not all(ok for _, _, ok in found.values()):
        return "FAIL: mounting holes %s (want NPTH drill 2.6 at %s)" % (sorted(found.items()), want)
    return "OK (4 x NPTH 2.6 at 9 mm inset, 62 mm pitch)"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_drc = "--no-drc" not in sys.argv
    parity = "--parity" in sys.argv
    tmp = tempfile.mkdtemp(prefix="osc_rules_")
    fail = 0
    for p in args or A.DEFAULT_PROJECTS:
        d = os.path.join(A.HW, p)
        pro = os.path.join(d, p + ".kicad_pro")
        dru = os.path.join(d, p + ".kicad_dru")
        pcb = A._pcb(p)
        print("== %s" % p)
        if not os.path.exists(pro):
            print("   ERROR: no project file")
            fail += 1
            continue
        A.WARNINGS.clear()
        want = A.build_dru(p)
        for w in A.WARNINGS:
            print("   WARNING:", w)
            fail += 1
        raw = open(dru, "rb").read() if os.path.exists(dru) else None
        if raw is None:
            print("   dru : MISSING"); fail += 1
        elif raw.startswith(b"\xef\xbb\xbf"):
            print("   dru : has a UTF-8 BOM - KiCad ignores the whole file"); fail += 1
        elif raw.decode("utf-8") != want:
            print("   dru : DIFFERS from generated (re-run apply_design_rules.py)"); fail += 1
        else:
            print("   dru : OK (%d rules)" % want.count("(rule "))
        bad = check_pro(pro, p)
        if bad:
            lock = " (KiCad has the project open?)" if A.is_open_in_kicad(d, p) else ""
            print("   pro : NOT APPLIED%s: %s" % (lock, "; ".join(bad[:4]) + (" ..." if len(bad) > 4 else "")))
            fail += 1
        else:
            print("   pro : OK")
        if not os.path.exists(pcb):
            print("   pcb : none yet (rules are in place; re-run apply after the PCB exists)")
            continue
        if not do_drc:
            continue
        j = run_drc(pcb, os.path.join(tmp, p + ".json"))
        if j is None:
            print("   drc : FAIL (kicad-cli produced no report)"); fail += 1
            continue
        c = collections.Counter((v["type"], v["severity"]) for v in j.get("violations", []))
        errs = {k[0]: n for k, n in c.items() if k[1] == "error"}
        warns = {k[0]: n for k, n in c.items() if k[1] != "error"}
        print("   drc : errors %s | warnings %s | %d unconnected" % (
            errs or "none", warns or "none", len(j.get("unconnected_items", []))))
        if errs:
            fail += 1
        if parity:
            jp = run_drc(pcb, os.path.join(tmp, p + "_parity.json"), ["--schematic-parity"])
            if jp:
                print("   parity: %s" % dict(collections.Counter(v["type"] for v in jp.get("schematic_parity", []))))
        r = probe(p, tmp)
        print("   probe: %s" % r)
        if not r.startswith("OK"):
            fail += 1
        if A.PROJECT_CFG.get(p, {}).get("panel"):
            r = check_holes(p)
            print("   holes: %s" % r)
            if r.startswith("FAIL"):
                fail += 1
    shutil.rmtree(tmp, ignore_errors=True)
    print("\nRESULT:", "ALL OK" if not fail else "%d problem(s)" % fail)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
