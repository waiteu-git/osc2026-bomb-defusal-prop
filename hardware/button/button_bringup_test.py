# Button module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認のみ。本番のファームウェア(ゲームロジック・タイマー連携)はソフト担当が別途実装する。
#
# 配線(button.kicad_sch / button_design_notes.md で確定、2026-09-30: 面LED撤去・カラー液晶GC9A01):
#   GPIO0/1 (UART0 TX/RX) : ホストとの通信専用(このテストでは未使用、配線不要)
#   GPIO4 (BTN)          : 押下検出用タクトスイッチ4個を並列(内部プルアップ、もう片方はGND直結)
#   GPIO9-12             : 側面ストリップLED(白/青/赤/黄)、NPN(2SC1815)ローサイド駆動、HIGHで点灯
#   GPIO15               : 状態LED(緑)、47Ω経由でLED->GND
#   GPIO17-22 (SPI0)     : キートップ表示器(Waveshare 1.28インチ丸型 GC9A01)
#                          CS=GP17, SCK=GP18, MOSI(DIN)=GP19, DC=GP20, RST=GP21, BL=GP22
#                          コネクタJ2のピン順: 1=VCC(3.3V) 2=GND 3=DIN 4=CLK 5=CS 6=DC 7=RST 8=BL
#                          (付属ケーブルの色・ピン順は現物で要確認)
#
# 準備:
#   1. GC9A01用のMicroPythonドライバを、このファイルと同じ場所にアップロードする
#      (例: russhughes/gc9a01_mpy の gc9a01.py。※このスクリプトのAPI呼び出しは記憶に基づく仮のもので
#       未検証。ドライバによって初期化・fillの書き方が違うので、手元のドライバに合わせて直すこと)
#   2. 上記の配線を行う
#
# 使い方: Thonny等でPicoに書き込んで実行。
#   1. 起動時に状態LEDが3回点滅し、NeoPixelが点灯していないこと(ちらつきの有無を目視で記録)
#   2. 液晶に赤/緑/青/黄/白/黒を順に全面表示(ボタンの色5種の見え方を確認)
#   3. NeoPixelを白/青/赤/黄で1色ずつ2秒点灯(明るさ20%、USBパワーメーターで電流を記録。点かない・色化けならDINの3.3V問題を疑う)
#   4. タクトスイッチを押すと液晶が「押下」の色に変わる(押下検出GP4の確認)

from machine import Pin, SPI, PWM
import time

import neopixel
NEO_PIN = 9        # GP9 -> R10(330) -> J3 pin2(DIN)
NEO_COUNT = 8      # つないだテープ/スティックの画素数に合わせる(要調整)
BRIGHT = 0.2       # 明るさ(1.0=最大。全白最大は1画素50〜60mA程度でパネル予算200mAを超える)
np = neopixel.NeoPixel(Pin(NEO_PIN), NEO_COUNT)
btn = Pin(4, Pin.IN, Pin.PULL_UP)
status_led = Pin(15, Pin.OUT, value=0)

CS, SCK, MOSI, DC, RST, BL = 17, 18, 19, 20, 21, 22


def blink(n, interval=0.15):
    for _ in range(n):
        status_led.value(1)
        time.sleep(interval)
        status_led.value(0)
        time.sleep(interval)


print("=== Button module bring-up test start ===")
np.fill((0, 0, 0))
np.write()
blink(3)

backlight = PWM(Pin(BL))
backlight.freq(1000)
backlight.duty_u16(65535)  # バックライト最大(約40mA級、電流を実測して記録)

tft = None
try:
    import gc9a01
    spi = SPI(0, baudrate=40_000_000, sck=Pin(SCK), mosi=Pin(MOSI))
    tft = gc9a01.GC9A01(spi, 240, 240, reset=Pin(RST, Pin.OUT), cs=Pin(CS, Pin.OUT),
                        dc=Pin(DC, Pin.OUT), rotation=0)
    tft.init()
except ImportError:
    print("gc9a01.py が見つかりません。ドライバをアップロードしてください(液晶以外のテストは続行)。")

COLORS = {"RED": 0xF800, "GREEN": 0x07E0, "BLUE": 0x001F, "YELLOW": 0xFFE0,
          "WHITE": 0xFFFF, "BLACK": 0x0000}
if tft is not None:
    for name, c in COLORS.items():
        print("LCD fill", name)
        tft.fill(c)
        time.sleep(1.0)

print("--- NeoPixelの色確認(1色ずつ2秒、USBパワーメーターで電流を記録) ---")
STRIP_COLORS = {"White": (255, 255, 255), "Blue": (0, 0, 255), "Red": (255, 0, 0), "Yellow": (255, 200, 0)}
for name, (r, g, b) in STRIP_COLORS.items():
    print("NeoPixel", name)
    np.fill((int(r * BRIGHT), int(g * BRIGHT), int(b * BRIGHT)))
    np.write()
    time.sleep(2.0)
    np.fill((0, 0, 0))
    np.write()
    time.sleep(0.3)

print("--- ボタン押下検出(GPIO4、内部プルアップ)。押すと液晶が赤、離すと黒 ---")
prev = 1
while True:
    val = btn.value()
    if val == 0 and prev == 1:
        print("BTN pressed")
        if tft is not None:
            tft.fill(COLORS["RED"])
    elif val == 1 and prev == 0:
        print("BTN released")
        if tft is not None:
            tft.fill(COLORS["BLACK"])
    prev = val
    time.sleep(0.02)
