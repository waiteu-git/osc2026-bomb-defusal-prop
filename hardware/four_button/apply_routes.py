# route_paths.py が見つけた経路(route_paths_2layer.json)を実トラック・ビアとして盤面に適用する。
# KiCad付属Pythonで実行: "C:\Program Files\KiCad\10.0\bin\python.exe" apply_routes.py
import json
import pcbnew

PCB = "four_button.kicad_pcb"
b = pcbnew.LoadBoard(PCB)
paths = json.load(open("route_paths_2layer.json", encoding="utf-8"))

LAYER_MAP = {0: pcbnew.F_Cu, 2: pcbnew.B_Cu}
WIDTH = {"+5V": 0.5, "/LEDDRV_R": 0.25, "/MODE_SEL": 0.25, "/LEDDRV_B": 0.25}

def get_net(name):
    return b.FindNet(name)

def net_name_for(result_key):
    # route_paths.pyのresultsキーは識別用のラベル(例: "+5V_1")であって実ネット名ではない場合がある。
    # ネット名そのもの(例: "+5V"そのままのキー)が優先、"+5V_1"のような接尾辞付きは先頭部分を使う。
    if result_key in WIDTH:
        return result_key
    base = result_key.rsplit("_", 1)[0]
    if base in WIDTH:
        return base
    raise KeyError(result_key)

for result_key, pts in paths.items():
    net_name = net_name_for(result_key)
    net = get_net(net_name)
    w = pcbnew.FromMM(WIDTH[net_name])
    for i in range(len(pts) - 1):
        x1, y1, l1 = pts[i]
        x2, y2, l2 = pts[i + 1]
        if l1 == l2:
            if x1 == x2 and y1 == y2:
                continue
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
            t.SetWidth(w)
            t.SetLayer(LAYER_MAP[l1])
            t.SetNet(net)
            b.Add(t)
        else:
            # layer change at same (x1,y1)==(x2,y2): add a via
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
            v.SetWidth(pcbnew.FromMM(0.8))
            v.SetDrill(pcbnew.FromMM(0.4))
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(net)
            b.Add(v)

for z in b.Zones():
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("tracks now", len(list(b.GetTracks())))
