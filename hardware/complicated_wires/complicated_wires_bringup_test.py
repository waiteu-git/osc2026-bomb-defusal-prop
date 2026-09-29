# Complicated Wires module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認のみ。本番のファームウェア(ベン図の判定・ラウンド生成)はソフト担当が別途実装する。
#
# 配線(complicated_wires_design_notes.md の GPIO表と同じ):
#   GPIO0/1 : UART0 TX/RX (ホストとの専用線。通信専用で予約、このテストでは使わない)
#   GPIO2-7 : 断線検出 ワイヤー1-6 (端子台の信号極。外付け10kΩプルアップ+直列1kΩ)
#             ワイヤーが繋がっている -> GNDに落ちる -> LOW / 切られた -> プルアップでHIGH
#   GPIO8   : NeoPixel(SK6812MINI-E)**20個**デイジーチェーンのDIN (直列330Ω経由)
#             2026-09-28確定(ユーザー指示): 複雑ワイヤの属性(色・★・LED点灯)は、パネル端の
#             専用バンドではなく、各端子(ワイヤーが挿さる場所そのもの)に置いたNeoPixelの
#             光り方で再現する。信号側端子台10極(スタート)+GND側端子台10極(ゴール)=20個。
#             チェーン順: index 0-9=信号側10極(スタート)、10-19=GND側10極(ゴール)。
#             各極がどの物理位置(端子台Ref・pole・ワイヤー番号)かはSTART_MAP/GOAL_MAPを参照。
#             データシート上VIH=0.7*VDD=3.5V@5Vで3.3V直結は理論上0.2V不足(design_notes.md §8参照)。
#   GPIO9   : 状態表示LED(緑, 47Ω経由, 解除済みで点灯する全モジュール共通仕様。単純LEDのまま)

from machine import Pin
import neopixel
import time

WIRE_GPIO = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7}
NEOPIXEL_GPIO = 8
STATUS_GPIO = 9
N_PIXELS = 20

# gen_complicated_wires_sch.py の TERMINAL_GROUPS/SIGNAL_POLES/GND_POLESと同じ並び。
# 各要素は (端子台Ref, pole番号, ワイヤー番号 or None=予備極)。
TERMINAL_GROUPS = [(1,), (2,), (3, 4), (5,), (6,)]


def _poles(prefix):
    poles = []
    for group in TERMINAL_GROUPS:
        label = "".join(str(n) for n in group)
        if len(group) == 1:
            n = group[0]
            poles.append((prefix + label, "1", n))
            poles.append((prefix + label, "2", None))
        else:
            n1, n2 = group
            poles.append((prefix + label, "1", n1))
            poles.append((prefix + label, "2", n2))
    return poles


SIGNAL_POLES = _poles("S")   # index 0-9 = チェーンのSTART(D1-D10)
GND_POLES = _poles("G")      # index 0-9 = チェーンのGOAL(D11-D20)

# ワイヤー番号(1-6) -> チェーンindex。スタート側・ゴール側それぞれの、そのワイヤーの主極を指す。
START_IDX = {n: i for i, (_, _, n) in enumerate(SIGNAL_POLES) if n is not None}
GOAL_IDX = {n: 10 + i for i, (_, _, n) in enumerate(GND_POLES) if n is not None}

# NeoPixelの輝度上限(0-255)。パネルのピーク電流200mA以内を守るためソフトで制限する。
# 20個(旧12個から増加)をフル点灯できる構成なので、実測してから最終値を決める(design_notes.md §5-4参照)。
MAX_BRIGHTNESS = 20

wires = {w: Pin(gp, Pin.IN) for w, gp in WIRE_GPIO.items()}   # 外付けプルアップを使うので内部プルアップは無効
status = Pin(STATUS_GPIO, Pin.OUT, value=0)
np = neopixel.NeoPixel(Pin(NEOPIXEL_GPIO), N_PIXELS)


def scale(rgb):
    return tuple(v * MAX_BRIGHTNESS // 255 for v in rgb)


WHITE = scale((255, 255, 255))
RED = scale((255, 0, 0))
BLUE = scale((0, 0, 255))
GREEN = scale((0, 255, 0))
AMBER = scale((255, 160, 0))
OFF = (0, 0, 0)


def fill(color):
    for i in range(N_PIXELS):
        np[i] = color
    np.write()


def wire_text(val):
    return "接続" if val == 0 else "切断"


print("=== Complicated Wires module bring-up test start ===")

# 1) 生存確認
for _ in range(3):
    status.value(1)
    time.sleep(0.15)
    status.value(0)
    time.sleep(0.15)

# 2) NeoPixelを1個ずつ、白→赤→青→緑(チェーン全20個、順番とDINの動作確認)
print("NeoPixel: 1個ずつ 白/赤/青/緑 (チェーンの順番が0->19の順に光ればOK。0-9=信号側端子(スタート)、10-19=GND側端子(ゴール))")
for color in (WHITE, RED, BLUE, GREEN):
    for i in range(N_PIXELS):
        fill(OFF)
        np[i] = color
        np.write()
        time.sleep(0.15)
fill(OFF)

# 3) 各ワイヤーのスタート側インジケータ(実際に使う6個、index=START_IDX[w])を順に点灯
print("スタート側インジケータ(ワイヤー1-6が挿さる信号側端子)を順に点灯")
for w in range(1, 7):
    np[START_IDX[w]] = AMBER
    np.write()
    time.sleep(0.3)
    np[START_IDX[w]] = OFF
    np.write()

# 4) 各ワイヤーのゴール側インジケータ(GND側端子)を順に点灯
print("ゴール側インジケータ(ワイヤー1-6が挿さるGND側端子)を順に点灯")
for w in range(1, 7):
    np[GOAL_IDX[w]] = AMBER
    np.write()
    time.sleep(0.3)
    np[GOAL_IDX[w]] = OFF
    np.write()

# 5) 監視ループ: 断線検出(WIRE1-6)の結果を、そのワイヤーのスタート側・ゴール側の両方の
#    NeoPixelで表示する(緑=接続、赤=切断)。色・★の実際の符号化はソフト担当が実装する
#    (design_notes.md §3-1・§8)。ここでは配線確認のみが目的。
prev = {}
for w in sorted(WIRE_GPIO):
    prev[w] = wires[w].value()
    print("ワイヤー{}(GPIO{}): {}".format(w, WIRE_GPIO[w], wire_text(prev[w])))


def show(w, val):
    color = GREEN if val == 0 else RED
    np[START_IDX[w]] = color
    np[GOAL_IDX[w]] = color
    np.write()


for w in prev:
    show(w, prev[w])

print("--- 監視開始(ワイヤーを切る/端子に挿して確認してください) ---")

while True:
    all_connected = True
    for w in sorted(WIRE_GPIO):
        val = wires[w].value()
        if val != prev[w]:
            time.sleep(0.03)   # 簡易デバウンス
            val = wires[w].value()
            if val != prev[w]:
                print("ワイヤー{}: {}".format(w, wire_text(val)))
                prev[w] = val
                show(w, val)
        if prev[w] != 0:
            all_connected = False
    status.value(1 if all_connected else 0)   # 全ワイヤー接続中だけ状態LEDが点灯
    time.sleep(0.02)
