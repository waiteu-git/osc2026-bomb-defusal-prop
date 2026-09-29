# Button module: 回路図の検証スクリプト(2026-09-27)。
# kicad-cliでERCを実行して違反件数を表示し、ネットリストを出力して、意図した接続表(全60ネット)と
# 1対1で機械照合する。接続表を変える場合(部品追加・GPIO変更)はこのファイルのexp_named/exp_anonも更新すること。
import re, json, subprocess, os
D = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\button"
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
subprocess.run([CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", os.path.join(D, "button_erc.json"), os.path.join(D, "button.kicad_sch")], capture_output=True)
subprocess.run([CLI, "sch", "export", "netlist", "-o", os.path.join(D, "button_netlist.net"), os.path.join(D, "button.kicad_sch")], capture_output=True)
d = json.load(open(os.path.join(D, "button_erc.json"), encoding="utf-8"))
v = []
def walk(o):
    if isinstance(o, dict):
        if "violations" in o: v.extend(o["violations"])
        for x in o.values(): walk(x)
    elif isinstance(o, list):
        for x in o: walk(x)
walk(d)
print("ERC violations:", len(v), [x.get("type") for x in v])

s = open(os.path.join(D, "button_netlist.net"), encoding="utf-8").read()
nets = re.findall(r'\(net\s*\(code "(\d+)"\)\s*\(name "([^"]*)"\)\s*\(class "[^"]*"\)(.*?)\n\t\t\)\n', s, re.S)
got = {name: frozenset(f"{r}.{p}" for r, p in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', body)) for _, name, body in nets}

# GP5-GP12 = 8色LEDチャンネル(ch index -> (物理pin, RBref, Qref, LEDref, Rref))
CH = [(7,"RB1","Q1","LED1","R1"), (9,"RB2","Q2","LED2","R2"), (10,"RB3","Q3","LED3","R3"),
      (11,"RB4","Q4","LED4","R4"), (12,"RB5","Q5","LED5","R5"), (14,"RB6","Q6","LED6","R6"),
      (15,"RB7","Q7","LED7","R7"), (16,"RB8","Q8","LED8","R8")]
SW = ["SW1", "SW2", "SW3", "SW4"]

exp_named = {
 "GND": ({"J1.4", "J2.3", "C1.2", "LED9.1"} | {f"{s}.1" for s in SW}
         | {f"{q}.1" for _, _, q, _, _ in CH}
         | {f"U1.{p}" for p in (3, 8, 13, 18, 23, 28, 33, 38, 42)}),
 "+3.3V": {"J2.4", "U1.36"},
 "+5V": ({"J1.3", "U1.39", "C1.1"} | {f"{r}.2" for _, _, _, _, r in CH}),
}
exp_anon = [
    {"J1.1", "U1.1"}, {"J1.2", "U1.2"}, {"J2.1", "U1.4"}, {"J2.2", "U1.5"},
    {"R9.1", "U1.20"}, {"R9.2", "LED9.2"},
    {f"U1.6"} | {f"{s}.2" for s in SW},  # GP4: ボタン押下スイッチ4個並列
] + [{f"{rb}.1", f"U1.{p}"} for p, rb, _, _, _ in CH] \
  + [{f"{rb}.2", f"{q}.3"} for _, rb, q, _, _ in CH] \
  + [{f"{q}.2", f"{l}.1"} for _, _, q, l, _ in CH] \
  + [{f"{l}.2", f"{r}.1"} for _, _, _, l, r in CH] \
  + [{f"U1.{p}"} for p in (17, 19, 21, 22, 24, 25, 26, 27, 29, 30, 31, 32, 34, 35, 37, 40, 41, 43)]
ok = True
for n, m in exp_named.items():
    if got.get(n) != frozenset(m):
        ok = False
        print("MISMATCH", n, sorted(got.get(n, [])), sorted(m))
rem = [x for k, x in got.items() if k not in exp_named]
for e in exp_anon:
    fe = frozenset(e)
    if fe in rem:
        rem.remove(fe)
    else:
        ok = False
        print("MISSING", sorted(e))
for r in rem:
    ok = False
    print("UNEXPECTED", sorted(r))
print("nets:", len(got), "ALL MATCH" if ok else "MISMATCH")
