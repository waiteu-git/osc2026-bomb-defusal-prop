# Button module: 自動配線の手順(2026-10-01)。KiCad付属Pythonで実行する:
#   "C:\Program Files\KiCad\10.0\bin\python.exe" route_button.py
# gen_button_pcb.py で作った未配線のbutton.kicad_pcbを、インストール済みのFreerouting 2.3.0(新規ダウンロードなし)で配線し、
# GNDベタを塗って保存する。※gen_button_pcb.pyを再実行すると配線は消える(その後にこのスクリプトを再実行すること)。
# GNDはベタ(表裏)で結ぶため、DSNからGNDネットを外してから配線させる。ネットクラス(信号0.25/電源0.5、ビア0.8/0.4)は.kicad_proのものがDSNに入る。
import os, subprocess
import pcbnew

D = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(D, "route")
JAR = "C:/Users/ysou5/Documents/KiCad/10.0/3rdparty/plugins/app_freerouting_kicad-plugin/jar/freerouting-2.3.0.jar"
PCB = os.path.join(D, "button.kicad_pcb")
os.makedirs(R, exist_ok=True)

b = pcbnew.LoadBoard(PCB)
pcbnew.ExportSpecctraDSN(b, os.path.join(R, "button.dsn"))
s = open(os.path.join(R, "button.dsn"), encoding="utf-8").read()
a = s.index("    (net GND\n")
e = s.index("    (net ", a + 10)
s = s[:a] + s[e:]
s = s.replace("(class Power +3.3V +5V GND", "(class Power +3.3V +5V")
open(os.path.join(R, "button_nognd.dsn"), "w", encoding="utf-8").write(s)
subprocess.run(["java", "-jar", JAR, "-de", os.path.join(R, "button_nognd.dsn"), "-do", os.path.join(R, "button.ses"),
                "-mp", "60", "-mt", "1"], check=True)
pcbnew.ImportSpecctraSES(b, os.path.join(R, "button.ses"))
for z in b.Zones():
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # 熱リリーフだと2.54mmピッチのGNDパッドでスポーク不足(starved_thermal)になる
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("tracks", len(list(b.GetTracks())))
