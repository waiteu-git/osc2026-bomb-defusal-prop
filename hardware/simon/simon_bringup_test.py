# Simon module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2 / Pico 2 W)
# 目的: 配線確認のみ。本番のファームウェアはソフト担当が別途実装する。
#
# 配線 (simon.kicad_sch と一致。色の並びは公式マニュアルの対応表の列順 赤/青/緑/黄):
#   GPIO2-5  : ボタン 赤/青/緑/黄 (もう片方はGND直結、内部プルアップを使うので外付け抵抗は無し)
#   GPIO6-9  : LEDドライバ 赤/青/緑/黄 (4.7kΩ経由で2SC1815のベース、HIGH=点灯)
#              LEDは 5V(VSYS) -> 抵抗(赤/黄330Ω, 青/緑150Ω) -> LEDアノード、カソード -> 2SC1815のコレクタ
#   GPIO10   : 状態LED (緑、47Ω経由でLED->GND、HIGH=点灯)
#   GPIO0/1  : UART0 (ホスト通信専用、このテストでは使わない)
#
# 使い方: Thonny等でPicoに書き込んで実行。
#   1. 状態LEDが3回点滅 (状態LED回路の生存確認)
#   2. 赤 -> 青 -> 緑 -> 黄 の順に色LEDが0.6秒ずつ点灯、続いて全色同時に1秒点灯
#      (順番が違う/光らない色があれば、その色のトランジスタ・抵抗・LEDの向きを確認)
#   3. 各色LEDが順番にゆっくり明滅 (PWMで調光できることの確認。不要なら RUN_PWM_TEST = False)
#   4. ボタンを1個ずつ押す: REPLに「RED (GPIO2) pressed」のように表示され、
#      押している間だけ同じ色のLEDが点灯し、状態LEDも点灯すれば配線OK

from machine import Pin, PWM
import time

NAMES = ("RED", "BLUE", "GREEN", "YELLOW")
BTN_GPIO = (2, 3, 4, 5)
LED_GPIO = (6, 7, 8, 9)
STATUS_GPIO = 10
RUN_PWM_TEST = True

buttons = [Pin(g, Pin.IN, Pin.PULL_UP) for g in BTN_GPIO]
leds = [Pin(g, Pin.OUT, value=0) for g in LED_GPIO]
status = Pin(STATUS_GPIO, Pin.OUT, value=0)


def blink_status(n, interval_ms=150):
    for _ in range(n):
        status.value(1)
        time.sleep_ms(interval_ms)
        status.value(0)
        time.sleep_ms(interval_ms)


def led_order_test():
    for i in range(4):
        print("LED {} (GPIO{}) ON".format(NAMES[i], LED_GPIO[i]))
        leds[i].value(1)
        time.sleep_ms(600)
        leds[i].value(0)
        time.sleep_ms(200)
    print("ALL LEDs ON (1秒。USBメーターで消費電流を読んで記録: パネルの電流予算は平均200mA)")
    for led in leds:
        led.value(1)
    time.sleep_ms(1000)
    for led in leds:
        led.value(0)


def pwm_test():
    for i in range(4):
        print("PWM breathing {} (GPIO{})".format(NAMES[i], LED_GPIO[i]))
        pwm = PWM(Pin(LED_GPIO[i]), freq=1000, duty_u16=0)
        for duty in list(range(0, 65535, 2048)) + list(range(65535, 0, -2048)):
            pwm.duty_u16(duty)
            time.sleep_ms(25)
        pwm.deinit()
        leds[i] = Pin(LED_GPIO[i], Pin.OUT, value=0)


print("=== Simon bring-up test start ===")
blink_status(3)
led_order_test()
if RUN_PWM_TEST:
    pwm_test()
print("Button test: press each button (RED / BLUE / GREEN / YELLOW)")
print("状態LEDが点灯している間(ボタンを押し続ける)に、R9(47Ω)の両端の電圧をテスタで測って記録: 電流=電圧÷47 (見込み約4〜8mA)")

prev = [1, 1, 1, 1]
while True:
    any_pressed = False
    for i in range(4):
        val = buttons[i].value()
        if val == 0:
            any_pressed = True
            leds[i].value(1)
            if prev[i] == 1:
                print("{} (GPIO{}) pressed".format(NAMES[i], BTN_GPIO[i]))
        else:
            leds[i].value(0)
            if prev[i] == 0:
                print("{} (GPIO{}) released".format(NAMES[i], BTN_GPIO[i]))
        prev[i] = val
    status.value(1 if any_pressed else 0)
    time.sleep_ms(20)
