# Keypad module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2 / Pico 2 W)
# 目的: 配線確認のみ。本番のファームウェアはソフト担当が別途実装する。
#
# 配線:
#   GPIO2-5 : ボタン x4 (もう片方はGND直結、内部プルアップを使うので外付け抵抗は無し)
#   GPIO6   : ステータスLED (47Ω経由でLED→GND)
#   GPIO0/1 : ホスト通信専用(UART0 TX/RX、区画ごとの専用線。今回のテストでは未使用)
#
# 使い方: Thonny等でPicoに書き込んで実行。起動時にLEDが3回点滅すればLED回路はOK。
#         その後、ボタンを1個ずつ押して、対応する番号がREPLに表示され、
#         押している間だけLEDが点灯すれば配線OK。

from machine import Pin
import time

BUTTON_PINS = {2: 2, 3: 3, 4: 4, 5: 5}  # GPIO番号: ラベル用に同じ番号を使う
buttons = {gp: Pin(gp, Pin.IN, Pin.PULL_UP) for gp in BUTTON_PINS}
led = Pin(6, Pin.OUT)

def blink(n, interval=0.15):
    for _ in range(n):
        led.value(1)
        time.sleep(interval)
        led.value(0)
        time.sleep(interval)

print("=== Keypad bring-up test start ===")
blink(3)  # LED回路の生存確認

prev_state = {gp: 1 for gp in BUTTON_PINS}  # プルアップなので未押下=1

while True:
    any_pressed = False
    for gp in BUTTON_PINS:
        val = buttons[gp].value()
        if val == 0:
            any_pressed = True
            if prev_state[gp] == 1:
                print("GPIO{} pressed".format(gp))
        else:
            if prev_state[gp] == 0:
                print("GPIO{} released".format(gp))
        prev_state[gp] = val
    led.value(1 if any_pressed else 0)
    time.sleep(0.02)
