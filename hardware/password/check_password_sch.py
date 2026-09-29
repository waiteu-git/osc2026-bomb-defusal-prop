# Password module: 回路図の検証スクリプト(2026-09-27)。
# kicad-cli で ERC を実行して違反件数を表示し、ネットリストを出力して、意図した接続表(全36ネット)と
# 1対1で機械照合する。接続表を変える場合(部品追加・GPIO変更)はこのファイルの sw / exp_named / exp_anon も更新すること。
import re, json, subprocess, os
D = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\password"
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
subprocess.run([CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", os.path.join(D, "password_erc.json"), os.path.join(D, "password.kicad_sch")], capture_output=True)
subprocess.run([CLI, "sch", "export", "netlist", "-o", os.path.join(D, "password_netlist.net"), os.path.join(D, "password.kicad_sch")], capture_output=True)
d = json.load(open(os.path.join(D, "password_erc.json"), encoding="utf-8"))
v = []
def walk(o):
    if isinstance(o, dict):
        if "violations" in o: v.extend(o["violations"])
        for x in o.values(): walk(x)
    elif isinstance(o, list):
        for x in o: walk(x)
walk(d)
print("ERC violations:", len(v), [x.get("type") for x in v])

s = open(os.path.join(D, "password_netlist.net"), encoding="utf-8").read()
nets = re.findall(r'\(net\s*\(code "(\d+)"\)\s*\(name "([^"]*)"\)\s*\(class "[^"]*"\)(.*?)\n\t\t\)\n', s, re.S)
got = {name: frozenset(f"{r}.{p}" for r, p in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', body)) for _, name, body in nets}
sw = {"SW1":6,"SW2":7,"SW3":9,"SW4":10,"SW5":11,"SW6":12,"SW7":14,"SW8":15,"SW9":16,"SW10":17,"SW11":19}
exp_named = {
 "GND": {"J1.4","J2.3","LED1.1","C1.2"} | {f"{k}.1" for k in sw} | {f"U1.{p}" for p in (3,8,13,18,23,28,33,38,42)},
 "+3.3V": {"J2.4","U1.36"},
 "+5V": {"J1.3","U1.39","C1.1"},
}
exp_anon = [{"J1.1","U1.1"},{"J1.2","U1.2"},{"J2.1","U1.4"},{"J2.2","U1.5"},{"R1.1","U1.20"},{"R1.2","LED1.2"}] \
  + [{f"{k}.2", f"U1.{p}"} for k, p in sw.items()] + [{f"U1.{p}"} for p in (21,22,24,25,26,27,29,30,31,32,34,35,37,40,41,43)]
ok = True
for n, m in exp_named.items():
    if got.get(n) != frozenset(m):
        ok = False; print("MISMATCH", n, sorted(got.get(n, [])), sorted(m))
rem = [x for k, x in got.items() if k not in exp_named]
for e in exp_anon:
    fe = frozenset(e)
    if fe in rem: rem.remove(fe)
    else: ok = False; print("MISSING", sorted(e))
for r in rem: ok = False; print("UNEXPECTED", sorted(r))
print("nets:", len(got), "ALL MATCH" if ok else "MISMATCH")
