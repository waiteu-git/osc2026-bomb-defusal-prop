# Host board module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2 W)
# 目的: 配線確認のみ。本番のファームウェアはソフト担当が別途実装する。
#
# 配線:
#   GPIO0 : I2C0 SDA
#   GPIO1 : I2C0 SCL
#   ホスト基盤がI2Cバスのマスタ。6区画分のJSTコネクタは全て同じI2Cバスに
#   星型配線で接続されている(プルアップ抵抗はホスト側に1組のみ実装、
#   各モジュール側には付けない)。
#
# 使い方: Thonny等でPicoに書き込んで実行。I2Cバスを.scan()で走査し、
#         応答のあったアドレスを一覧でREPLに表示するだけ。
#         6区画のうち実際にモジュールが挿さっている区画の数だけアドレスが
#         表示されるはず(何も挿さっていない区画は検出されなくて正常)。
#         想定と違う個数/アドレスが出た場合は配線または該当モジュール側の
#         I2C回路を確認すること。

from machine import Pin, I2C

I2C_ID = 0
SDA_PIN = 0
SCL_PIN = 1
FREQ = 400000

i2c = I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=FREQ)

print("=== Host I2C bus bring-up test start ===")
print("I2C{} scanning (SDA=GPIO{}, SCL=GPIO{})...".format(I2C_ID, SDA_PIN, SCL_PIN))

addrs = i2c.scan()

if not addrs:
    print("No devices found. 配線またはプルアップを確認すること。")
else:
    print("Found {} device(s):".format(len(addrs)))
    for a in addrs:
        print("  0x{:02X}".format(a))
