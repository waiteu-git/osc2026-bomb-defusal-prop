# Maze module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認のみ。本番のファームウェア(迷路9パターンの生成・正誤判定)はソフト担当が別途実装する。
#
# 配線(maze.kicad_sch / maze_design_notes.md で確定、2026-09-27: 位置表示は案A 0.96インチOLEDに決定):
#   GPIO0/1 (UART0 TX/RX) : ホストとの通信専用(このテストでは未使用、配線不要)
#   GPIO2-5 (UP/LEFT/DOWN/RIGHT) : 方向ボタン(内部プルアップ、もう片方はGND直結)
#   GPIO7   (状態LED、緑) : 47Ω経由でLED→GND、解除済みの間だけ点灯する想定(本テストでは生存確認の点滅のみ)
#   GPIO8 (I2C0 SDA), GPIO9 (I2C0 SCL) : 0.96インチOLED(SSD1315, アドレス0x3C, モジュール内蔵プルアップ)
#   GPIO6, GPIO10-13 : 未使用(旧WS2812B用GPIO6は解放、TFT案B/B'は不採用のためGPIO10-13も未使用)
#
# 準備:
#   1. MicroPython公式の定番ssd1306ドライバ(ssd1306.py)を、このファイルと同じ場所に
#      一緒にアップロードしておくこと(password_bringup_test.py等と同じもの)
#   2. 上記の配線を行う
#
# 使い方: Thonny等でPicoに書き込んで実行。
#   1. 起動時に状態LEDが3回点滅すればLED回路はOK
#   2. i2c.scan()の結果に0x3Cが出て、OLEDに簡易迷路(6x6グリッド+現在地)が表示されればOLED回路もOK
#      (OLEDブレイクアウト基板側の実ピン順(GND,VCC,SCL,SDA等)は現物到着後に要確認。
#       0x3Cが出ない場合はまずSDA(GPIO8)/SCL(GPIO9)の配線を疑うこと)
#   3. UP/LEFT/DOWN/RIGHTのいずれかを押すと、対応するラベルがREPLに表示され、
#      押している間だけ状態LEDが点灯し、OLED上の現在地マーカーが1マス動けば配線OK
#      (盤面の壁・ゴール・ランドマーク判定は本番のゲームロジックに含まれないため、このテストでは行わない)

from machine import Pin, I2C
import time

try:
    import ssd1306
except ImportError:
    print("ssd1306.py が見つかりません。事前にPicoへアップロードしてください。")
    raise

BUTTON_PINS = {"UP": 2, "LEFT": 3, "DOWN": 4, "RIGHT": 5}  # GPIO番号: 方向ラベル
buttons = {name: Pin(gp, Pin.IN, Pin.PULL_UP) for name, gp in BUTTON_PINS.items()}
status_led = Pin(7, Pin.OUT)

I2C_ID = 0
SDA_PIN = 8
SCL_PIN = 9
FREQ = 400000
OLED_ADDR = 0x3C

GRID_N = 6
CELL_PX = 8  # 6x6 x 8px = 48px、128x64のOLEDに収まる
ORIGIN_X, ORIGIN_Y = 8, 8
pos = [GRID_N // 2, GRID_N // 2]  # [col, row]、配線確認用の仮の開始位置


def blink(n, interval=0.15):
    for _ in range(n):
        status_led.value(1)
        time.sleep(interval)
        status_led.value(0)
        time.sleep(interval)


def draw(oled):
    oled.fill(0)
    oled.text("MAZE TEST", 0, 0)
    for r in range(GRID_N + 1):
        oled.hline(ORIGIN_X, ORIGIN_Y + r * CELL_PX, GRID_N * CELL_PX, 1)
    for c in range(GRID_N + 1):
        oled.vline(ORIGIN_X + c * CELL_PX, ORIGIN_Y, GRID_N * CELL_PX, 1)
    cx = ORIGIN_X + pos[0] * CELL_PX + CELL_PX // 2
    cy = ORIGIN_Y + pos[1] * CELL_PX + CELL_PX // 2
    oled.fill_rect(cx - 2, cy - 2, 4, 4, 1)  # 現在地(塗りつぶし四角、簡易表示)
    oled.show()


print("=== Maze bring-up test start ===")
blink(3)  # 状態LED回路の生存確認

i2c = I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=FREQ)
addrs = i2c.scan()
print("Found I2C devices:", ["0x{:02X}".format(a) for a in addrs])

oled = None
if OLED_ADDR not in addrs:
    print("OLED(0x3C)が見つかりません。SDA(GPIO8)/SCL(GPIO9)の配線を確認してください。")
else:
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    draw(oled)
    print("OLEDに表示しました。6x6グリッドと中央の現在地マーカーが見えればOLED回路は正常です。")

DELTA = {"UP": (0, -1), "LEFT": (-1, 0), "DOWN": (0, 1), "RIGHT": (1, 0)}
prev_state = {name: 1 for name in BUTTON_PINS}  # プルアップなので未押下=1

while True:
    any_pressed = False
    for name, gp in BUTTON_PINS.items():
        val = buttons[name].value()
        if val == 0:
            any_pressed = True
            if prev_state[name] == 1:
                print("{} (GPIO{}) pressed".format(name, gp))
                dx, dy = DELTA[name]
                pos[0] = max(0, min(GRID_N - 1, pos[0] + dx))  # 壁判定はせず、盤端で止めるだけ(配線確認用)
                pos[1] = max(0, min(GRID_N - 1, pos[1] + dy))
                if oled is not None:
                    draw(oled)
        else:
            if prev_state[name] == 0:
                print("{} (GPIO{}) released".format(name, gp))
        prev_state[name] = val
    status_led.value(1 if any_pressed else 0)
    time.sleep(0.02)
