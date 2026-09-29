# Keypad module - game-logic demo (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認用のkeypad_bringup_test.pyとは別に、「正しい順番でボタンを押すと解除、
#       間違えるとストライク」という実際のキーパッドのゲームロジックの動きだけを試すデモ。
#       本物の記号対応表(26記号×6列)はまだ使っておらず、仮の正解順です。
#       ボタンキャップに本物の記号を印刷したら、正解順の決め方(対応表)を差し替える想定。
#       本番ファームウェア(Shizuku)はソフト担当が別途実装します。
#
# 正解順(仮): SW1(GPIO2) -> SW2(GPIO3) -> SW3(GPIO4) -> SW4(GPIO5)
#
# 配線はkeypad_bringup_test.pyと同じ:
#   SW1-4: GPIO2/3/4/5(内部プルアップ、押すとLow)
#   LED1 : GPIO6(47Ω経由)
#
# 使い方: Thonnyで実行。
#   - 正解順に4個押すと「解除!」と表示されLEDが点灯したまま停止する(実機と同じく解除後は変化しない)
#   - 途中で違うボタンを押すと「ストライク!」と表示されLEDが素早く6回点滅し、最初からやり直しになる

from machine import Pin
import time

BUTTON_GPIOS = [2, 3, 4, 5]
buttons = {gp: Pin(gp, Pin.IN, Pin.PULL_UP) for gp in BUTTON_GPIOS}
led = Pin(6, Pin.OUT)

CORRECT_ORDER = [2, 3, 4, 5]  # 仮の正解順。本物の記号対応表を使う場合はここを差し替える


def wait_for_press():
    # 押下(Low)を検出→デバウンス→離される(High に戻る)まで待ってから戻る。
    # 離されるまで待たないと、指を離す前に次の呼び出しが来たときに
    # 同じ1回の押下を「新しい押下」として二重検出してしまう。
    while True:
        for gp, pin in buttons.items():
            if pin.value() == 0:
                time.sleep(0.02)  # デバウンス
                if pin.value() == 0:
                    while pin.value() == 0:
                        time.sleep(0.005)
                    return gp
        time.sleep(0.005)


def strike():
    print("ストライク! 最初からやり直しです")
    for _ in range(6):
        led.value(1)
        time.sleep(0.08)
        led.value(0)
        time.sleep(0.08)


def solved():
    print("解除!")
    led.value(1)



print("=== Keypad game-logic demo start ===")
print("正解順(仮): GPIO{} -> GPIO{} -> GPIO{} -> GPIO{}".format(*CORRECT_ORDER))

progress = 0
while True:
    gp = wait_for_press()
    print("GPIO{} pressed".format(gp))
    if gp == CORRECT_ORDER[progress]:
        progress += 1
        if progress == len(CORRECT_ORDER):
            solved()
            while True:
                time.sleep(1)  # 解除後は状態を維持したまま停止
    else:
        strike()
        progress = 0
