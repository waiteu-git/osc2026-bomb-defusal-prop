# Wires module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認と、端子台サンプルの実測(交換時間・チャタリング)の補助。本番のファームウェア(判定・ラウンド生成)はソフト担当が別途実装する。
# 2026-09-24 新方針(実際に切る/端子台で交換/NeoPixelで色表示)版。旧ジャンパー方式のテストは廃止。
#
# 配線(wires_design_notes.md の GPIO表と同じ):
#   GPIO0/1 : UART0 TX/RX (ホストとの専用線。通信専用で予約、このテストでは使わない)
#   GPIO2-7 : 断線検出 ワイヤー1-6 (端子台の信号極 -> 直列1kΩ -> GPIO。GPIO側に外付け10kΩプルアップ(3V3(OUT)へ))
#             ワイヤーが繋がっている -> 端子がGNDに落ちる -> LOW / 切られた -> プルアップでHIGH
#             外付けプルアップを使うので内部プルアップは無効にする(Pin.IN)
#   GPIO8   : 状態表示LED(緑, OSG58A3131A, 47Ω経由, 解除済みで点灯する全モジュール共通仕様)
#   GPIO9   : NeoPixel(WS2812B) チェーンのDIN (直列330Ω経由、チェーンの順番=ワイヤー1..6)
#
# 使い方: Thonny等でPicoに書き込んで実行(F5)。
#   1) 状態LEDが3回点滅(生存確認)
#   2) NeoPixelを1個ずつ白→赤→青→緑で点灯(チェーンの順番とDINの動作確認。3.3V直結が動くかの確認も兼ねる)
#   3) 論理色(赤/青/黄/白)をワイヤーごとに並べて表示(見た目の確認)
#   4) 監視ループ: ワイヤーを切る/端子に挿すたびにREPLへ表示し、切ったワイヤーのNeoPixelは消灯、
#      全ワイヤーが接続されている間だけ状態LEDが点灯(=交換後の「全結線OK」セルフテストの代わり)
#      さらに「切断が始まってから全部つながるまで」の経過時間を表示する(端子台の交換時間の実測用)
#
# 端子台サンプルが3個(=3本分)しかない場合は ACTIVE_WIRES = [1, 2, 3] にして、使わないGPIOは未配線のままにする
# (未配線のGPIOは外付けプルアップが無いので、その場合はプルアップ無し=不定になるため、ACTIVE_WIRESで監視から外すこと)。

from machine import Pin
import neopixel
import time

WIRE_GPIO = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7}
STATUS_GPIO = 8
NEOPIXEL_GPIO = 9

# 実際に配線したワイヤーの番号。サンプルが少ないときはここを減らす。
ACTIVE_WIRES = [1, 2, 3, 4, 5, 6]

# NeoPixelの輝度上限(0-255)。パネルのピーク電流200mA以内を守るためソフトで制限する。
# 白(3色点灯)は1個あたり約 60mA x (上限/255)。6個で 360mA x (上限/255)。30なら約42mA。
MAX_BRIGHTNESS = 30

DEBOUNCE_MS = 50   # 切断/接続が50ms続いたら確定

wires = {w: Pin(gp, Pin.IN) for w, gp in WIRE_GPIO.items()}   # 外付けプルアップを使うので内部プルアップは無効
status = Pin(STATUS_GPIO, Pin.OUT, value=0)
np = neopixel.NeoPixel(Pin(NEOPIXEL_GPIO), 6)


def scale(rgb):
    return tuple(v * MAX_BRIGHTNESS // 255 for v in rgb)


WHITE = scale((255, 255, 255))
RED = scale((255, 0, 0))
BLUE = scale((0, 0, 255))
GREEN = scale((0, 255, 0))
YELLOW = scale((255, 170, 0))
OFF = (0, 0, 0)

# ワイヤーごとの論理色(ラウンドごとにファームが決める想定のダミー)。黒は消灯だと見えないため表現方法が未決。
LOGICAL = {1: RED, 2: BLUE, 3: YELLOW, 4: WHITE, 5: RED, 6: BLUE}


def fill(color):
    for i in range(6):
        np[i] = color
    np.write()


def wire_text(val):
    return "接続" if val == 0 else "切断"


print("=== Wires module bring-up test start ===")
print("監視するワイヤー:", ACTIVE_WIRES)

# 1) 生存確認
for _ in range(3):
    status.value(1)
    time.sleep(0.15)
    status.value(0)
    time.sleep(0.15)

# 2) NeoPixelを1個ずつ、白→赤→青→緑
print("NeoPixel: 1個ずつ 白/赤/青/緑 (チェーンの順番が1→6の順に光ればOK。光らない/おかしな色ならDINのしきい値を疑う)")
for color in (WHITE, RED, BLUE, GREEN):
    for i in range(6):
        fill(OFF)
        np[i] = color
        np.write()
        time.sleep(0.25)
fill(OFF)

# 3) 論理色の見た目確認
print("論理色の表示確認: 1=赤 2=青 3=黄 4=白 5=赤 6=青")
for w in range(1, 7):
    np[w - 1] = LOGICAL[w]
np.write()
time.sleep(2)

# 4) 監視ループ
now = time.ticks_ms
prev = {}
for w in ACTIVE_WIRES:
    prev[w] = wires[w].value()
    print("ワイヤー{}(GPIO{}): {}".format(w, WIRE_GPIO[w], wire_text(prev[w])))


def show(w, val):
    np[w - 1] = LOGICAL[w] if val == 0 else OFF
    np.write()


for w in prev:
    show(w, prev[w])

print("--- 監視開始(ワイヤーを切る/端子に挿して確認してください) ---")

cycle_start = None            # 全接続→切断が始まった時刻
was_all_connected = all(prev[w] == 0 for w in ACTIVE_WIRES)

while True:
    for w in ACTIVE_WIRES:
        val = wires[w].value()
        if val != prev[w]:
            # チャタリングの目安: 50ms間の生の遷移回数を数える
            t0 = now()
            edges = 0
            last = val
            while time.ticks_diff(now(), t0) < DEBOUNCE_MS:
                v = wires[w].value()
                if v != last:
                    edges += 1
                    last = v
            val = last
            if val != prev[w]:
                print("ワイヤー{}: {}{}".format(w, wire_text(val), "  (50ms内に追加の遷移 {} 回=チャタリング)".format(edges) if edges else ""))
                prev[w] = val
                show(w, val)
    all_connected = all(prev[w] == 0 for w in ACTIVE_WIRES)
    if was_all_connected and not all_connected:
        cycle_start = now()
    if (not was_all_connected) and all_connected and cycle_start is not None:
        print("交換完了: 全ワイヤー接続。最初の切断から {:.1f} 秒".format(time.ticks_diff(now(), cycle_start) / 1000))
        cycle_start = None
    was_all_connected = all_connected
    status.value(1 if all_connected else 0)   # 全ワイヤー接続中だけ状態LEDが点灯
    time.sleep(0.01)
