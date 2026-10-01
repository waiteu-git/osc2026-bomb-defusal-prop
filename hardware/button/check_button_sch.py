# Button module: 回路図の検証スクリプト(2026-09-27)。
# kicad-cliでERCを実行して違反件数を表示し、ネットリストを出力して、意図した接続表(全ネット)と
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

# ストリップLED 4ch: GP9-GP12 = 物理pin 12/14/15/16 (RBref, Qref, LEDref, Rref)。面LED4chは2026-09-30に撤去(カラー液晶に置換)
CH = []   # 単色LED4ch+NPNは2026-09-30にNeoPixel(J3+R10)へ置換
SW = ["SW1"]
# キートップ表示器J2(8ピン、Waveshare GC9A01付属ケーブル順): 1=VCC(+3.3V) 2=GND 3=DIN(GP19,pin25) 4=CLK(GP18,pin24)
# 5=CS(GP17,pin22) 6=DC(GP20,pin26) 7=RST(GP21,pin27) 8=BL(GP22,pin29)
LCD = {3: 25, 4: 24, 5: 22, 6: 26, 7: 27, 8: 29}

exp_named = {
 "GND": ({"J1.4", "J2.2", "C1.2", "LED9.1"} | {f"NP{i}.3" for i in range(1, 7)} | {f"{s}.1" for s in SW}
         | {f"{q}.1" for _, _, q, _, _ in CH}
         | {f"U1.{p}" for p in (3, 8, 13, 18, 23, 28, 33, 38)}),
 "+3.3V": {"J2.1", "U1.36"},
 "+5V": ({"J1.3", "U1.39", "C1.1"} | {f"NP{i}.1" for i in range(1, 7)} | {f"{r}.2" for _, _, _, _, r in CH}),
}
exp_anon = [{f"NP{i}.2", f"NP{i+1}.4"} for i in range(1, 6)] + [{"NP6.2"}] + [
    {"J1.1", "U1.1"}, {"J1.2", "U1.2"},
    {"R9.1", "U1.20"}, {"R9.2", "LED9.2"}, {"R10.2", "NP1.4"}, {"R10.1", "U1.12"},
    {f"U1.6"} | {f"{s}.2" for s in SW},  # GP4: ボタン押下スイッチ4個並列
] + [{f"J2.{j}", f"U1.{p}"} for j, p in LCD.items()]   + [{f"{rb}.1", f"U1.{p}"} for p, rb, _, _, _ in CH]   + [{f"{rb}.2", f"{q}.3"} for _, rb, q, _, _ in CH]   + [{f"{q}.2", f"{l}.1"} for _, _, q, l, _ in CH]   + [{f"{l}.2", f"{r}.1"} for _, _, _, l, r in CH]   + [{f"U1.{p}"} for p in (4, 5, 7, 9, 10, 11, 14, 15, 16, 17, 19, 21, 30, 31, 32, 34, 35, 37, 40)]
ok = True
for n, m in exp_named.items():
    if got.get(n) != frozenset(m):
        ok = False
        print("MISMATCH", n, sorted(got.get(n, [])), sorted(m))
# ラベル付きネットの名前も確認する(名前付きラベル方式に変更した2026-09-30以降)
exp_labeled = {"/BTN": {"U1.6"} | {f"{s}.2" for s in SW}}
exp_labeled.update({f"/{n}": {f"J2.{j}", f"U1.{p}"} for j, p, n in
                    [(3, 25, "LCD_DIN"), (4, 24, "LCD_CLK"), (5, 22, "LCD_CS"), (6, 26, "LCD_DC"), (7, 27, "LCD_RST"), (8, 29, "LCD_BL")]})
exp_labeled.update({f"/STRIP_{c}": {f"{rb}.1", f"U1.{p}"} for (p, rb, _, _, _), c in zip(CH, "WBRY")})
exp_labeled["/STATUS_LED"] = {"R9.1", "U1.20"}
exp_labeled["/NEO_DIN"] = {"R10.1", "U1.12"}
for n, m in exp_labeled.items():
    if got.get(n) != frozenset(m):
        ok = False
        print("LABEL MISMATCH", n, sorted(got.get(n, [])), sorted(m))

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
