# Wire Sequence module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認のみ。本番のファームウェア(ページ判定・ストライク通知)はソフト担当が別途実装する。
#
# 配線(回路図 wire_sequence.kicad_sch と一致):
#   GPIO2-9  : ワイヤー切断検知 x8 (W1..W8)。各ワイヤーの信号極 -> 直列1kΩ -> GPIO、GPIOと3.3Vの間に外付け10kΩ、
#              GND極は共通GND。内部プルアップは使わない(wires/複雑ワイヤ担当と同じ構成)。
#              ワイヤーが繋がっている(導通) -> LOW(約0.3V) / 切断・未接続 -> HIGH
#              (外付け10kΩを付けずにブレッドボードで試す場合だけ WIRE_PULL = Pin.PULL_UP にする)
#   GPIO10   : NeoPixel(WS2812B) x8 のデータ。330Ωを介して1個目のDINへ、DOUT->次段DINでチェーン(W1..W8の順)
#              NeoPixelのVDDは5V(USB給電のブリングアップではVBUS=物理ピン40)、GNDは共通
#   GPIO11-14: ステージインジケーターLED x4 (それぞれ330Ω経由でLED->GND)
#   GPIO15   : UPボタン   (もう片方はGND、内部プルアップ)
#   GPIO16   : DOWNボタン (もう片方はGND、内部プルアップ)
#   GPIO17   : 状態表示LED(緑、47Ω経由でLED->GND)
#   GPIO0/1  : ホストとのUART0(専用線)。通常のテストでは未使用。
#              UART_LOOPBACK_TEST = True にして、JSTのPin1(TX)とPin2(RX)を短絡すると通信線を確認できる。
#
# 使い方: Thonny等でPicoに書き込んで実行(手順は wire_sequence_bringup_procedure.md)。
#   1. 起動時に状態LEDが0.15秒間隔で3回点滅(生存確認)。
#   2. ステージLED4個が順に点灯 -> 全消灯。
#   3. NeoPixelが W1->W8 の順に1個ずつ白く点灯(配線順・断線確認)。続けて全灯で赤/緑/青/白を順に点灯(色チャンネル確認)。
#   4. NeoPixelの3.3V直結マージン確認(DIN_SOAK_SECONDS秒間、高速に書き込み続ける)。目視でチラつき・色ずれを見る。
#   5. 監視ループ: 各ワイヤーの割り当て色(赤/青/黒=弱い白)をNeoPixelで表示。ワイヤーを切る/外すと、そのNeoPixelが消え、
#      REPLに「Wn(GPIOx, 色=...): 切断」と表示される。戻すと再点灯。UP/DOWNでステージLEDの点灯数が増減する。
#      ボタンを押している間は状態LEDが点灯する。
#
# 電流について: NeoPixel8灯を全灯させるテストは、輝度を絞って(MAX_BRIGHTNESS)モジュールの200mA上限に余裕を持たせる。

from machine import Pin, UART
import neopixel
import time

NUM_WIRES = 8
WIRE_GPIO = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9}  # ワイヤー番号 -> GPIO番号(NeoPixelのチェーン順もW1..W8)
NEO_GPIO = 10
STAGE_GPIO = [11, 12, 13, 14]
BTN_UP_GPIO = 15
BTN_DOWN_GPIO = 16
STATUS_GPIO = 17

MAX_BRIGHTNESS = 20         # 0-255。8灯を全灯しても200mAに余裕がある値(迷路モジュールと同じ)
DIN_SOAK_SECONDS = 5        # 3.3V直結のマージン確認に書き込みを続ける秒数
UART_LOOPBACK_TEST = False  # True: JSTのPin1(GPIO0=TX)とPin2(GPIO1=RX)を短絡して通信線を確認する
WIRE_PULL = None            # 外付け10kΩプルアップを付けた本番配線ではNone。付けない仮組みでは Pin.PULL_UP

wires = {w: Pin(gp, Pin.IN, WIRE_PULL) for w, gp in WIRE_GPIO.items()}
np = neopixel.NeoPixel(Pin(NEO_GPIO), NUM_WIRES)
stage = [Pin(gp, Pin.OUT) for gp in STAGE_GPIO]
btn_up = Pin(BTN_UP_GPIO, Pin.IN, Pin.PULL_UP)
btn_down = Pin(BTN_DOWN_GPIO, Pin.IN, Pin.PULL_UP)
status = Pin(STATUS_GPIO, Pin.OUT)

M = MAX_BRIGHTNESS
COLOR = {"red": (M, 0, 0), "blue": (0, 0, M), "black": (M // 2, M // 2, M // 2)}  # 黒は「弱い白」で表現する
# 監視ループで使う、各ワイヤーの論理色(本番は毎ラウンドランダム。ここでは確認用に固定)
ASSIGNED = ["red", "blue", "black", "red", "black", "blue", "red", "blue"]


def state_text(val):
    # 外付けプルアップなので: LOW(0)=GND極に導通=ワイヤーあり, HIGH(1)=未導通=切断
    return "接続" if val == 0 else "切断"


def blink(pin, n, interval=0.15):
    for _ in range(n):
        pin.value(1)
        time.sleep(interval)
        pin.value(0)
        time.sleep(interval)


def np_clear():
    for i in range(NUM_WIRES):
        np[i] = (0, 0, 0)
    np.write()


def np_fill(color):
    for i in range(NUM_WIRES):
        np[i] = color
    np.write()


def chase_test(color=(40, 40, 40), interval=0.25):
    # 1個ずつの点灯なので電流は問題にならない。W1..W8の順に光れば、チェーン配線と各LEDの生存が確認できる。
    np_clear()
    for i in range(NUM_WIRES):
        np[i] = color
        np.write()
        print("NeoPixel {} (W{}) 点灯".format(i + 1, i + 1))
        time.sleep(interval)
        np[i] = (0, 0, 0)
    np.write()


def flash_all(name, color, duration=0.5):
    print("全灯: " + name)
    np_fill(color)
    time.sleep(duration)
    np_clear()
    time.sleep(0.15)


def din_soak(seconds):
    # 3.3V直結のDIN入力マージン確認: 青と赤をLED番号の偶奇で分け、毎フレーム入れ替えて高速に書き続け、チラつき・色ずれを目視で見る。
    print("3.3V直結マージン確認 {}秒: チラつき・色ずれ・消えるLEDが無いか目視してください".format(seconds))
    end = time.ticks_add(time.ticks_ms(), seconds * 1000)
    a = (0, 0, M)
    b = (M, 0, 0)
    flip = False
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        for i in range(NUM_WIRES):
            np[i] = a if ((i % 2 == 0) != flip) else b
        np.write()
        flip = not flip
        time.sleep_ms(10)
    np_clear()


def uart_loopback():
    u = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))
    u.write(b"WSEQ")
    time.sleep(0.05)
    r = u.read()
    print("UART loopback: 送信 b'WSEQ' -> 受信 {}".format(r))
    print("OK" if r == b"WSEQ" else "NG (JSTのPin1とPin2を短絡しましたか?)")


print("=== Wire Sequence bring-up test start ===")
blink(status, 3)  # 状態LEDの生存確認

for i, s in enumerate(stage):  # ステージLEDを順に点灯 -> 全消灯
    s.value(1)
    print("ステージLED {} 点灯".format(i + 1))
    time.sleep(0.25)
time.sleep(0.3)
for s in stage:
    s.value(0)

chase_test()
flash_all("赤", (M, 0, 0))
flash_all("緑", (0, M, 0))
flash_all("青", (0, 0, M))
flash_all("白", (M, M, M))
din_soak(DIN_SOAK_SECONDS)
if UART_LOOPBACK_TEST:
    uart_loopback()

print("--- ワイヤー・ボタン監視開始(ワイヤーを切る/外す、UP/DOWNを押して確認してください) ---")
stable = {w: wires[w].value() for w in wires}   # デバウンス後の状態
pending = {w: (stable[w], 0) for w in wires}     # (直近の読み値, その連続回数)
for w in sorted(wires):
    print("W{}(GPIO{}): {}".format(w, WIRE_GPIO[w], state_text(stable[w])))

stage_count = 0
prev_up = prev_down = 1


def refresh_np():
    for w in wires:
        np[w - 1] = COLOR[ASSIGNED[w - 1]] if stable[w] == 0 else (0, 0, 0)  # 切れたワイヤーは消灯
    np.write()


def refresh_stage():
    for i, s in enumerate(stage):
        s.value(1 if i < stage_count else 0)


refresh_np()
refresh_stage()

while True:
    for w in wires:
        v = wires[w].value()
        last, n = pending[w]
        n = n + 1 if v == last else 1
        pending[w] = (v, n)
        if n >= 3 and v != stable[w]:  # 3回連続(約60ms)同じ値なら確定
            stable[w] = v
            print("W{}(GPIO{}, 色={}): {}".format(w, WIRE_GPIO[w], ASSIGNED[w - 1], state_text(v)))
            refresh_np()
    up = btn_up.value()
    down = btn_down.value()
    if up == 0 and prev_up == 1:
        print("UP (GPIO{}) pressed".format(BTN_UP_GPIO))
        stage_count = max(0, stage_count - 1)
        refresh_stage()
    if down == 0 and prev_down == 1:
        print("DOWN (GPIO{}) pressed".format(BTN_DOWN_GPIO))
        stage_count = min(len(stage), stage_count + 1)
        refresh_stage()
    if (up == 1 and prev_up == 0) or (down == 1 and prev_down == 0):
        print("button released")
    prev_up, prev_down = up, down
    status.value(1 if (up == 0 or down == 0) else 0)
    time.sleep(0.02)
