# -*- coding: utf-8 -*-
"""wires.kicad_sch の検証: kicad-cli で ERC とネットリスト(XML)を出力し、expected_nets.json(生成スクリプトが書く期待ネット)と突き合わせる。
ERCが通っても配線が正しい保証にはならないため、ネットのメンバーを部品参照子・ピン番号で照合する。
使い方: python verify_wires_sch.py
"""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
SCH = str(HERE / "wires.kicad_sch")
ERC = HERE / "wires_erc.json"
NET = HERE / "wires_netlist.xml"

subprocess.run([CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", str(ERC), SCH], capture_output=True)
subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(NET), SCH], check=True, capture_output=True)

# --- ERC
erc = json.loads(ERC.read_text(encoding="utf-8"))
viol = [v for sh in erc["sheets"] for v in sh["violations"]]
print("ERC violations: %d  %s" % (len(viol), dict(Counter(v["type"] for v in viol))))
for v in viol:
    print("  -", v["type"], "|", "; ".join(i["description"] for i in v["items"]))

# --- ネットリスト
root = ET.parse(NET).getroot()
nets = {}
for net in root.find("nets"):
    members = frozenset("%s.%s" % (n.get("ref"), n.get("pin")) for n in net.findall("node"))
    nets[net.get("name")] = members
got = {frozenset(m) for m in nets.values() if len(m) >= 2}
exp_raw = json.loads((HERE / "expected_nets.json").read_text(encoding="utf-8"))
exp = {frozenset(v) for v in exp_raw.values()}

ok = True
missing = [k for k, v in exp_raw.items() if frozenset(v) not in got]
extra = [sorted(m) for m in got if m not in exp]
print("expected nets: %d  netlist nets (>=2 members): %d" % (len(exp), len(got)))
if missing:
    ok = False
    print("MISSING (expected but not in netlist):", missing)
if extra:
    ok = False
    print("EXTRA (in netlist but not expected):")
    for e in extra:
        print("   ", e)

# 単独ネット(=未接続ピン)の一覧
singles = sorted(next(iter(m)) for m in nets.values() if len(m) == 1)
print("unconnected single-pin nets: %d" % len(singles))
print("  ", singles)

# 重要ネットの内訳を人間が目で確認できるように表示
for name in ("GND", "+5V", "+5V_NEO", "+3.3V"):
    for nm, m in nets.items():
        if nm.strip("/") == name:
            print("%s (%d): %s" % (name, len(m), sorted(m)))
print("RESULT:", "OK" if ok else "MISMATCH")
