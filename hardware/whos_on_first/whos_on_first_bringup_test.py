# Who's on First module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認のみ。パズルロジック(単語対応表)は本番ファームウェア(ソフト担当がShizuku/C++で実装)の
#       範囲であり、このスクリプトには含まない。
#
# 2026-09-27(2) TFT->OLED変更(ハブ決定、「再現の方針」による): 表示器を1.54インチTFT(ST7789,SPI)から
# 0.96インチOLED(SSD1315,I2C)に変更、6ボタンの単語を固定(印刷キャップ)にした。旧版のSPIドライバ・
# ボタンのGPIO配置(GP8-13)は本版で置き換えた。詳細は whos_on_first_design_notes.md 参照。
#
# 配線 (詳細は whos_on_first_design_notes.md、回路図は whos_on_first.kicad_sch):
#   GP0/1   : UART0 (TX/RX, ホストリンク。本テストでは未使用)
#   GP2-7   : 6ボタン(TL/TR/ML/MR/BL/BR)、内部プルアップ、もう片方はGND直結
#   GP8/9   : OLED(0.96インチ 128x64 SSD1315, 秋月#112031, I2C0) — GP8=SDA, GP9=SCL, アドレス0x3C
#   GP14-16 : ステージ進捗LED x3(赤、330Ω経由)
#   GP17    : 状態表示LED(緑、47Ω経由、解除済みの間だけ点灯という仕様だが本テストでは単純に点滅確認のみ)
#
# 使い方: Thonny等でPico 2に書き込んで実行。
#   1. 起動直後、状態LED(GP17)とステージLED x3(GP14-16)が順番に1回ずつ点灯すればLED回路はOK。
#   2. その後、I2Cバスをスキャンして0x3Cが見つかるか確認し、OLEDの簡易初期化+塗りつぶし/反転を試みる
#      (OLED未実装/未接続でも例外を捕まえて続行する)。画面が白→黒→反転の順に変われば配線OK。
#      SSD1306/SSD1315用の外部ドライバライブラリは使わず、素のI2Cコマンドのみ(配線確認専用、文字描画なし)。
#   3. 最後にボタン読み取りループに入る。6個のボタンを1個ずつ押して、対応する位置名(TL等)が
#      REPLに表示されれば配線OK。Ctrl+Cで終了。
#
# 注意: 2026-09-27時点でOLED本体(秋月#112031)は在庫あり(TFTと違い在庫僅少ではない)。
#       実機でのブリングアップは本セッションではまだ実施していない(回路図・netlistの検算のみ)。

from machine import Pin, I2C
import time

# --- ピン定義 ---
# 2026-09-27(2): TFT(GP2-7 SPI)を廃止しOLED(GP8/9 I2C0)に変更。ボタンはGP8-13からGP2-7へ移動
# (回路図・netlist検算済み、tools/check_consistency.py参照)。
OLED_SDA, OLED_SCL = 8, 9
BUTTON_PINS = {
    "TL": 2, "TR": 3, "ML": 4, "MR": 5, "BL": 6, "BR": 7,
}
STAGE_LED_PINS = [14, 15, 16]  # stage 1,2,3
STATUS_LED_PIN = 17

stage_leds = [Pin(gp, Pin.OUT) for gp in STAGE_LED_PINS]
status_led = Pin(STATUS_LED_PIN, Pin.OUT)
buttons = {name: Pin(gp, Pin.IN, Pin.PULL_UP) for name, gp in BUTTON_PINS.items()}


def blink(pin, n=1, interval=0.15):
    for _ in range(n):
        pin.value(1)
        time.sleep(interval)
        pin.value(0)
        time.sleep(interval)


def step1_led_test():
    print("--- STEP 1: LED test (status + stage x3) ---")
    blink(status_led, 1, 0.3)
    for i, led in enumerate(stage_leds, start=1):
        print("stage LED {} on".format(i))
        blink(led, 1, 0.3)
    print("STEP 1 done: 4回の点灯(状態→stage1→stage2→stage3)が見えたらOK\n")


# --- 最小限のSSD1315(SSD1306互換)生I2Cドライバ(配線確認専用、フォント描画等は無し) ---
SSD1306_SET_CONTRAST = 0x81
SSD1306_SET_DISP = 0xAE          # |0x00=off, |0x01=on (last bit)
SSD1306_SET_MEM_ADDR = 0x20
SSD1306_SET_DISP_START_LINE = 0x40
SSD1306_SET_SEG_REMAP = 0xA0     # |0x01
SSD1306_SET_MUX_RATIO = 0xA8
SSD1306_SET_COM_OUT_DIR = 0xC0   # |0x08
SSD1306_SET_DISP_OFFSET = 0xD3
SSD1306_SET_COM_PIN_CFG = 0xDA
SSD1306_SET_DISP_CLK_DIV = 0xD5
SSD1306_SET_PRECHARGE = 0xD9
SSD1306_SET_VCOM_DESEL = 0xDB
SSD1306_SET_CHARGE_PUMP = 0x8D
SSD1306_SET_ENTIRE_ON = 0xA4     # |0x01=all-white (ignore RAM), test only
SSD1306_SET_NORM_INV = 0xA6      # |0x01=inverted


class MinimalSSD1315:
    """配線確認専用の最小実装(SSD1306互換コマンド)。本番描画(文字表示等)はソフト担当が別ドライバで行う想定。"""

    def __init__(self, i2c, addr=0x3C, width=128, height=64):
        self.i2c = i2c
        self.addr = addr
        self.width = width
        self.height = height
        self.pages = height // 8

    def _cmd(self, c):
        self.i2c.writeto(self.addr, bytearray([0x00, c]))

    def _data(self, buf):
        # control byte 0x40 = data stream; chunk to keep writes small
        self.i2c.writeto(self.addr, b"\x40" + buf)

    def init(self):
        for c in (
            SSD1306_SET_DISP | 0x00,
            SSD1306_SET_DISP_CLK_DIV, 0x80,
            SSD1306_SET_MUX_RATIO, self.height - 1,
            SSD1306_SET_DISP_OFFSET, 0x00,
            SSD1306_SET_DISP_START_LINE,
            SSD1306_SET_CHARGE_PUMP, 0x14,
            SSD1306_SET_MEM_ADDR, 0x00,
            SSD1306_SET_SEG_REMAP | 0x01,
            SSD1306_SET_COM_OUT_DIR | 0x08,
            SSD1306_SET_COM_PIN_CFG, 0x12,
            SSD1306_SET_CONTRAST, 0x7F,
            SSD1306_SET_PRECHARGE, 0xF1,
            SSD1306_SET_VCOM_DESEL, 0x40,
            SSD1306_SET_ENTIRE_ON | 0x00,
            SSD1306_SET_NORM_INV | 0x00,
            SSD1306_SET_DISP | 0x01,
        ):
            self._cmd(c)

    def fill(self, on):
        pattern = 0xFF if on else 0x00
        line = bytearray([pattern] * self.width)
        for page in range(self.pages):
            self._cmd(0xB0 | page)          # page address
            self._cmd(0x00)                 # lower column = 0
            self._cmd(0x10)                 # higher column = 0
            self._data(line)

    def invert(self, on):
        self._cmd(SSD1306_SET_NORM_INV | (1 if on else 0))


def step2_oled_test():
    print("--- STEP 2: OLED fill test (white -> black -> invert) ---")
    try:
        i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400_000)
        found = i2c.scan()
        print("I2C scan result:", [hex(a) for a in found])
        if 0x3C not in found:
            raise RuntimeError("0x3C not found on the bus (OLED未接続/未実装の可能性)")
        oled = MinimalSSD1315(i2c)
        oled.init()
        print("filling white")
        oled.fill(True)
        time.sleep(1.0)
        print("filling black")
        oled.fill(False)
        time.sleep(1.0)
        print("invert on/off")
        oled.fill(True)
        oled.invert(True)
        time.sleep(1.0)
        oled.invert(False)
        time.sleep(1.0)
        oled.fill(False)
        print("STEP 2 done: 画面が白->黒->反転の順に変わったらOK\n")
    except Exception as e:
        print("STEP 2 SKIPPED/FAILED (OLED未接続、配線ミス、または未実装の可能性):", e)
        print("(LED/ボタンのテストは続行します)\n")


def step3_button_loop():
    print("--- STEP 3: button test (Ctrl+C で終了) ---")
    print("6個のボタンを1個ずつ押してください。位置名が表示されればOK。")
    prev = {name: 1 for name in buttons}  # プルアップなので未押下=1
    try:
        while True:
            for name, pin in buttons.items():
                val = pin.value()
                if val == 0 and prev[name] == 1:
                    print("button {} pressed  (GPIO{})".format(name, BUTTON_PINS[name]))
                    status_led.value(1)
                elif val == 1 and prev[name] == 0:
                    print("button {} released".format(name))
                    status_led.value(0)
                prev[name] = val
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("STEP 3 stopped by user")


print("=== Who's on First bring-up test start ===")
step1_led_test()
step2_oled_test()
step3_button_loop()
