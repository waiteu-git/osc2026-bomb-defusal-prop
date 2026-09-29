# Password module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認のみ。本番のファームウェア(35語のパズル生成・正誤判定)はソフト担当が別途実装する。
#
# 配線(password.kicad_sch / password_design_notes.md で確定):
#   GPIO0/1 (UART0 TX/RX) : ホストとの通信専用(このテストでは未使用、配線不要)
#   GPIO2 (I2C1 SDA), GPIO3 (I2C1 SCL) : 0.96インチOLED(SSD1315, アドレス0x3C, モジュール内蔵プルアップ)
#   GPIO4-8  (UP1-UP5)   : 各桁の▲ボタン(内部プルアップ、もう片方はGND直結)
#   GPIO9-13 (DOWN1-DOWN5): 各桁の▼ボタン(同上)
#   GPIO14   (SUBMIT)     : 送信ボタン(同上)
#   GPIO15   (状態LED、緑) : 47Ω経由でLED→GND、解除済みの間だけ点灯する想定(本テストでは生存確認の点滅のみ)
#
# 準備:
#   1. MicroPython公式の定番ssd1306ドライバ(ssd1306.py)を、このファイルと同じ場所に
#      一緒にアップロードしておくこと(host_i2c_oled_test.py / shared_param_widget_bringup_test.pyと同じもの)
#   2. 上記の配線を行う
#
# 使い方: Thonny等でPicoに書き込んで実行。
#   1. 起動時にLEDが3回点滅すればLED回路はOK
#   2. i2c.scan()の結果に0x3Cが出て、OLEDに5文字のテスト表示が出ればOLED回路もOK
#      (OLEDブレイクアウト基板側の実ピン順(GND,VCC,SCL,SDA等)は現物到着後に要確認。
#       0x3Cが出ない場合はまずSDA/SCLの配線を疑うこと)
#   3. UP1-5・DOWN1-5・SUBMITのいずれかを押すと、対応するラベルがREPLに表示され、
#      押している間だけLEDが点灯すれば配線OK。あわせてOLED上の対応する文字位置が
#      "^"(UP)/"v"(DOWN)/実際の桁送りではなく単なる押下マーカーに変わり、
#      どのボタンがどのGPIOに対応するか目視でも確認できるようにしてある
#      (本番の文字送りロジックはソフト担当の実装範囲、このテストでは行わない)

from machine import Pin, I2C
import time

try:
    import ssd1306
except ImportError:
    print("ssd1306.py が見つかりません。事前にPicoへアップロードしてください。")
    raise

BUTTON_PINS = {
    "UP1": 4, "UP2": 5, "UP3": 6, "UP4": 7, "UP5": 8,
    "DOWN1": 9, "DOWN2": 10, "DOWN3": 11, "DOWN4": 12, "DOWN5": 13,
    "SUBMIT": 14,
}
buttons = {name: Pin(gp, Pin.IN, Pin.PULL_UP) for name, gp in BUTTON_PINS.items()}
led = Pin(15, Pin.OUT)

I2C_ID = 1
SDA_PIN = 2
SCL_PIN = 3
FREQ = 400000
OLED_ADDR = 0x3C

COLUMN_LABELS = ["UP1/DOWN1", "UP2/DOWN2", "UP3/DOWN3", "UP4/DOWN4", "UP5/DOWN5"]
display_chars = ["A", "A", "A", "A", "A"]  # 本番の文字送りではなく、押下確認用のダミー表示


def blink(n, interval=0.15):
    for _ in range(n):
        led.value(1)
        time.sleep(interval)
        led.value(0)
        time.sleep(interval)


def draw(oled, marker_col=None, marker_char=None):
    oled.fill(0)
    oled.text("PASSWORD TEST", 0, 0)
    chars = list(display_chars)
    if marker_col is not None:
        chars[marker_col] = marker_char
    oled.text(" ".join(chars), 0, 24)
    oled.text("SUBMIT=*" if buttons["SUBMIT"].value() == 0 else "", 0, 48)
    oled.show()


print("=== Password module bring-up test start ===")
blink(3)  # LED回路の生存確認

i2c = I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=FREQ)
addrs = i2c.scan()
print("Found I2C devices:", ["0x{:02X}".format(a) for a in addrs])

oled = None
if OLED_ADDR not in addrs:
    print("OLED(0x3C)が見つかりません。SDA(GPIO2)/SCL(GPIO3)の配線を確認してください。")
else:
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    draw(oled)
    print("OLEDに表示しました。5文字(AAAAA)が見えればOLED回路は正常です。")

prev_state = {name: 1 for name in BUTTON_PINS}  # プルアップなので未押下=1

while True:
    any_pressed = False
    for name, gp in BUTTON_PINS.items():
        val = buttons[name].value()
        if val == 0:
            any_pressed = True
            if prev_state[name] == 1:
                print("{} (GPIO{}) pressed".format(name, gp))
                if oled is not None and name not in ("SUBMIT",):
                    col = int(name[-1]) - 1  # "UP3"/"DOWN3" -> col index 2
                    marker = "^" if name.startswith("UP") else "v"
                    draw(oled, marker_col=col, marker_char=marker)
                elif oled is not None:
                    draw(oled)
        else:
            if prev_state[name] == 0:
                print("{} (GPIO{}) released".format(name, gp))
                if oled is not None:
                    draw(oled)
        prev_state[name] = val
    led.value(1 if any_pressed else 0)
    time.sleep(0.02)
