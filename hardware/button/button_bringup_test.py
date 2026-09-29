# Button module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認のみ。本番のファームウェア(ゲームロジック・タイマー連携)はソフト担当が別途実装する。
#
# 配線(button.kicad_sch / button_design_notes.md で確定、interpretation C: 電気的ゲート):
#   GPIO0/1 (UART0 TX/RX) : ホストとの通信専用(このテストでは未使用、配線不要)
#   GPIO2 (I2C1 SDA), GPIO3 (I2C1 SCL) : 0.96インチOLED(SSD1315, アドレス0x3C, モジュール内蔵プルアップ)
#   GPIO4 (BTN) : 押下検出用タクトスイッチ4個を並列(内部プルアップ、もう片方はGND直結)
#   GPIO5-8  : 面LED(白/青/赤/黄)、NPN(2SC1815)ローサイド駆動、HIGHで点灯
#   GPIO9-12 : 側面ストリップLED(白/青/赤/黄)、同上
#   GPIO15   : 状態LED(緑)、47Ω経由でLED->GND、解除済みの間だけ点灯する想定
#
# 準備:
#   1. MicroPython公式の定番ssd1306ドライバ(ssd1306.py)を、このファイルと同じ場所に
#      一緒にアップロードしておくこと(password/host_i2c_oled_test.py等と同じもの)
#   2. 上記の配線を行う(白/青LEDは電流が個体差でVfのばらつきを受けやすいので、
#      R1/R2/R5/R6=100ohm付近から実測して調整する前提。button_design_notes.md §3-C参照)
#
# 使い方: Thonny等でPicoに書き込んで実行。
#   1. 起動時に状態LEDが3回点滅すればLED回路の生存確認OK。同時に面/ストリップLEDが
#      点灯しない(起動直後に出力Lowになっている)ことを目視確認する(RP2350-E9対策の確認)
#   2. i2c.scan()の結果に0x3Cが出て、OLEDに文言テスト表示が出ればOLED回路もOK
#   3. GPIO4のタクトスイッチのいずれかを押すと、REPLに"BTN pressed"と表示され、
#      押している間だけ側面ストリップLEDが点灯する(実際の色ルール判定はソフト担当の実装範囲、
#      このテストでは白固定で「押されている」ことだけを示す)
#   4. 面LED・ストリップLEDを1色ずつ順番に点灯し、対応する色・GPIOをREPLに表示する
#      (USBパワーメーターで各色点灯時の電流を実測し、button_design_notes.md §4の見積りと
#      比較・記録すること)

from machine import Pin, I2C
import time

try:
    import ssd1306
except ImportError:
    print("ssd1306.py が見つかりません。事前にPicoへアップロードしてください。")
    raise

FACE_PINS = {"White": 5, "Blue": 6, "Red": 7, "Yellow": 8}
STRIP_PINS = {"White": 9, "Blue": 10, "Red": 11, "Yellow": 12}
face_leds = {c: Pin(gp, Pin.OUT, value=0) for c, gp in FACE_PINS.items()}
strip_leds = {c: Pin(gp, Pin.OUT, value=0) for c, gp in STRIP_PINS.items()}

btn = Pin(4, Pin.IN, Pin.PULL_UP)
status_led = Pin(15, Pin.OUT, value=0)

I2C_ID = 1
SDA_PIN = 2
SCL_PIN = 3
FREQ = 400000
OLED_ADDR = 0x3C


def blink(n, interval=0.15):
    for _ in range(n):
        status_led.value(1)
        time.sleep(interval)
        status_led.value(0)
        time.sleep(interval)


def draw(oled, line1, line2=""):
    oled.fill(0)
    oled.text("BUTTON TEST", 0, 0)
    oled.text(line1, 0, 24)
    if line2:
        oled.text(line2, 0, 40)
    oled.show()


print("=== Button module bring-up test start ===")
# 起動直後は全LEDが出力Low(=消灯)であることをまず確認(RP2350-E9対策、button_design_notes.md参照)
assert all(p.value() == 0 for p in list(face_leds.values()) + list(strip_leds.values())), \
    "起動直後にLEDが点灯しています。GPIO初期化順を確認してください。"
blink(3)  # 状態LED回路の生存確認

i2c = I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=FREQ)
addrs = i2c.scan()
print("Found I2C devices:", ["0x{:02X}".format(a) for a in addrs])

oled = None
if OLED_ADDR not in addrs:
    print("OLED(0x3C)が見つかりません。SDA(GPIO2)/SCL(GPIO3)の配線を確認してください。")
else:
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    draw(oled, "READY")
    print("OLEDに表示しました。READYが見えればOLED回路は正常です。")

print("--- 面LED・ストリップLEDの単灯確認(1色ずつ2秒点灯、USBパワーメーターで電流を記録) ---")
for group_name, group in (("Face", face_leds), ("Strip", strip_leds)):
    for color, pin in group.items():
        print("{} LED {} (GPIO{}) ON".format(group_name, color, pin))
        pin.value(1)
        time.sleep(2.0)
        pin.value(0)
        time.sleep(0.3)

print("--- ボタン押下検出(GPIO4、内部プルアップ)。押すとストリップが白で点灯 ---")
prev = 1
while True:
    val = btn.value()
    if val == 0 and prev == 1:
        print("BTN pressed")
        strip_leds["White"].value(1)
        if oled is not None:
            draw(oled, "PRESSED")
    elif val == 1 and prev == 0:
        print("BTN released")
        strip_leds["White"].value(0)
        if oled is not None:
            draw(oled, "READY")
    prev = val
    time.sleep(0.02)
