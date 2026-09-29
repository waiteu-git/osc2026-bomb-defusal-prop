# Shared parameter widget - hardware bring-up test (MicroPython, Raspberry Pi Pico 2 / Pico 2 W)
# 目的: 配線確認のみ。本番のファームウェア(共有情報バイトの生成・OLED描画内容)はソフト担当が別途実装する。
#
# 注意: このウィジェットは他モジュール(キーパッド等)と違い、専用マイコン・専用I2Cアドレスを
#       持たない。ホストのPico 2 WのGPIOに直接配線される設計なので、このテストは
#       「ホストと同じGPIO配置(GP2-7, I2C0=GP0/GP1)を持つPico」で実行する想定。
#       本番のホスト基板そのものでも、配線検証用の予備Picoでもどちらでもよい。
#
# 配線(host_design_notes.md J7/J8で確定済み):
#   GPIO2 (SHARED_ODDEVEN) : スライドスイッチ(SS-12D00G3) - シリアル末尾奇偶
#   GPIO3 (SHARED_VOWEL)   : スライドスイッチ - シリアル母音有無
#   GPIO4 (SHARED_BATT2)   : スライドスイッチ - バッテリー2本以上
#   GPIO5 (SHARED_BATT3)   : スライドスイッチ - バッテリー3本以上(優先度低)
#   GPIO6 (SHARED_PORT)    : スライドスイッチ - パラレルポート有無
#     -> 上記5個はいずれも内部プルアップ使用。スイッチのもう片方はGND直結、外付け抵抗なし。
#        Low(0) = 有効(スイッチが倒れている/該当する側)。
#   GPIO7 (SHARED_LED)     : 白色LED(OSW54K3131A) + 電流制限抵抗(100〜150Ω、実測して調整)
#     -> 本番ではホストが能動的にHigh/Lowを切り替える(インジケーター表示の点灯/消灯)。
#   GPIO0/1 (I2C0 SDA/SCL) : 既存の6モジュール共有I2Cバスに相乗り。OLED(SSD1315, 0.96インチ)、
#     アドレス0x3C(SA0がモジュール基板側でGNDに繋がっている前提、現物到着後に要確認)。
#     プルアップ抵抗はホスト側の分配ポイントに既設のものを流用(このウィジェット側には付けない)。
#
# 準備:
#   1. MicroPython公式の定番ssd1306ドライバ(ssd1306.py)を、このファイルと同じ場所に
#      一緒にアップロードしておくこと(host_i2c_oled_test.pyと同じもの)
#   2. 上記の配線を行う
#
# 使い方: Thonny等でPicoに書き込んで実行。
#   1. 起動時にLEDが3回点滅すればLED回路はOK
#   2. i2c.scan()の結果に0x3Cが出て、OLEDに"I2C OK!"が表示されればOLED回路もOK
#   3. スイッチを1個ずつ倒して、対応するラベル(SHARED_ODDEVEN等)がREPLに表示され、
#      倒している間だけLEDが点灯すれば配線OK
#      (このLED連動はブリングアップテスト専用の簡易確認用。本番ではLEDはスイッチと無関係に
#       ホストが独立して点灯/消灯を制御する)

from machine import Pin, I2C
import time

try:
    import ssd1306
except ImportError:
    print("ssd1306.py が見つかりません。事前にPicoへアップロードしてください。")
    raise

SWITCH_PINS = {
    "SHARED_ODDEVEN": 2,
    "SHARED_VOWEL": 3,
    "SHARED_BATT2": 4,
    "SHARED_BATT3": 5,
    "SHARED_PORT": 6,
}
switches = {name: Pin(gp, Pin.IN, Pin.PULL_UP) for name, gp in SWITCH_PINS.items()}
led = Pin(7, Pin.OUT)

I2C_ID = 0
SDA_PIN = 0
SCL_PIN = 1
FREQ = 400000
OLED_ADDR = 0x3C


def blink(n, interval=0.15):
    for _ in range(n):
        led.value(1)
        time.sleep(interval)
        led.value(0)
        time.sleep(interval)


print("=== Shared parameter widget bring-up test start ===")
blink(3)  # LED回路の生存確認

i2c = I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=FREQ)
addrs = i2c.scan()
print("Found I2C devices:", ["0x{:02X}".format(a) for a in addrs])

if OLED_ADDR not in addrs:
    print("OLED(0x3C)が見つかりません。配線・SA0の設定を確認してください。")
else:
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    oled.fill(0)
    oled.text("I2C OK!", 0, 0)
    oled.text("SharedParamWidget", 0, 16)
    oled.show()
    print("OLEDに表示しました。画面に「I2C OK!」が見えればOLED回路は正常です。")

prev_state = {name: 1 for name in SWITCH_PINS}  # プルアップなので未操作=1

while True:
    any_active = False
    for name, gp in SWITCH_PINS.items():
        val = switches[name].value()
        if val == 0:
            any_active = True
            if prev_state[name] == 1:
                print("{} (GPIO{}) active".format(name, gp))
        else:
            if prev_state[name] == 0:
                print("{} (GPIO{}) inactive".format(name, gp))
        prev_state[name] = val
    led.value(1 if any_active else 0)
    time.sleep(0.02)
