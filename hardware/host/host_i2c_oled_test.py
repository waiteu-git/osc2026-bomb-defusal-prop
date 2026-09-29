# Host board - I2C communication test using an OLED (SSD1306/SSD1315) as a stand-in slave
# 目的: モジュール側にI2Cスレーブ実装がまだ無い段階で、ホストのI2Cマスター側の配線・実装が
#       本当に機能するかを、動作が保証された市販I2Cデバイス(OLED)を使って確認する。
#       本番のモジュール<->ホスト通信そのものの確認ではない(それはShizuku側で別途行う)。
#
# 準備:
#   1. MicroPython公式の定番ssd1306ドライバ(ssd1306.py)を入手し、このファイルと
#      同じ場所(Pico上)に一緒にアップロードしておくこと(micropython-lib配布のもの)
#   2. OLED(0.96インチ, SSD1315/SSD1306, I2C)をブレッドボードに配置し、
#      SDA->GPIO0, SCL->GPIO1, VCC->3.3V, GND->GND で接続
#      (このホスト用ブレッドボードには別途4.7kΩのプルアップ抵抗をSDA/SCLそれぞれに
#      3.3Vへ接続しておくこと。モジュール側には付けない、という設計方針通り)
#
# 使い方: Thonny等でPicoに書き込んで実行。
#   1. i2c.scan()でOLEDのアドレス(通常0x3C)が見えるか確認
#   2. 見えたら実際に文字列を描画してみて、画面に表示されれば通信成功

from machine import Pin, I2C
import time

try:
    import ssd1306
except ImportError:
    print("ssd1306.py が見つかりません。事前にPicoへアップロードしてください。")
    raise

I2C_ID = 0
SDA_PIN = 0
SCL_PIN = 1
FREQ = 400000

i2c = I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=FREQ)

print("=== Host I2C OLED communication test start ===")
addrs = i2c.scan()
print("Found devices:", ["0x{:02X}".format(a) for a in addrs])

if not addrs:
    print("デバイスが見つかりません。プルアップ抵抗(4.7kΩ x2)・配線を確認してください。")
else:
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    oled.fill(0)
    oled.text("I2C OK!", 0, 0)
    oled.text("Host <-> Slave", 0, 16)
    oled.show()
    print("OLEDに表示しました。画面に「I2C OK!」が見えれば、ホスト側のI2Cマスター実装は正常です。")
