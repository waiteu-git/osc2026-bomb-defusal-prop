# Memory module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認 + TM1637のVDD=5V/3.3V比較(輝度・チラつき・CLK/DIO通信の成否)。
#       本番のファームウェア(パズル生成・ステージ判定)はソフト担当が別途実装する。
#
# 配線 (memory_design_notes.md の GPIO表と一致させること):
#   GPIO0/1 : UART0 (TX/RX, ホストとの通信用。今回のテストでは未使用)
#   GPIO2   : TM1637 CLK
#   GPIO3   : TM1637 DIO
#   GPIO4-7 : ボタン位置1〜4 (もう片方はGND直結、内部プルアップを使うので外付け抵抗は無し)
#   GPIO8   : 状態LED(緑、解除済みの間だけ点灯) (47Ω経由でLED→GND)
#   TM1637 VDD : 【比較対象】5Vモード=Picoの VBUS(物理ピン40) / 3.3Vモード=Picoの 3V3(OUT)(物理ピン36)
#                → このVDDの1本だけを付け替えて2回実行し、結果を比べる(他の配線は変えない)
#
# TM1637 - 表示器間の配線(このユニット内で固定、Pico側からは関与しない):
#   GRID1   = メイン表示部(OSL10391-IRA、0.39インチ、ステージ表示の数字。5個とも同一部品)
#   GRID2-5 = ボタン位置1〜4のラベル表示(OSL10391-IRA、それぞれのボタンの真上に配置)
#   ※ OSL10391-IRAはピンピッチ2.54mm・列間7.52mm。ピン対応(A=10,B=9,C=7,D=5,E=4,F=2,G=1,DP=6,COM=3/8)と
#      配線の手順は 動作確認手順.md の「7. メモリー」の7-1を参照。
#   GRID6   = ステージ進行ランプ5個(SEG_A〜SEG_Eの5本だけ使用、SEG_F/G/DPは未使用)
#   SEG1-8  = 7セグのA,B,C,D,E,F,G,DPセグメント共通バス(bit0=A ... bit6=G, bit7=DP)
#
# 使い方: Thonny等でPicoに書き込んで実行。下の VDD_LABEL を実際の配線に合わせて書き換えてから実行する。
#   [1] 通信テスト  : TM1637へ多数回書き込み、ACKが返った/返らなかった回数を表示(CLK/DIOが通じているかの客観的な指標)
#   [2] 輝度スイープ: 全表示器・全ランプを点灯したまま輝度8段階を順に切替(目視で明るさ・チラつきを確認)
#   [3] セグメント歩行: 表示器ごとに8セグメントを1個ずつ点灯(配線・セグメント対応の確認)
#   [4] 数字テスト  : 各表示器に 1,2,3,4 を順に表示(セグメント対応が正しければ数字が正しく読める)
#   [5] ランプ・ボタン: ステージランプを1個ずつ点灯 → 全点灯のままボタン監視ループ
#      (ボタンを押すと位置番号がREPLに表示され、押している間だけ状態LEDが点灯)

from machine import Pin
import time

VDD_LABEL = "5V"   # ← TM1637のVDDの接続先に合わせて "5V" か "3V3" に書き換える(ログ表示用のラベルだけで、動作は変わらない)

OPEN_DRAIN = False  # False: CLK/DIOをpush-pull出力(現行設計、プルアップ無し)。
                    # True : CLK/DIOをオープンドレイン駆動(切り分け用。CLKとDIOそれぞれ10kΩをTM1637のVDDへプルアップすること。
                    #        High=VDDになるが、Pico側は5V入力になるので電源が入っている間のみ使うこと)

PIN_DRIVE = Pin.OPEN_DRAIN if OPEN_DRAIN else Pin.OUT
CLK = Pin(2, PIN_DRIVE)
DIO = Pin(3, PIN_DRIVE)
STATUS_LED = Pin(8, Pin.OUT)

BUTTON_PINS = {4: 1, 5: 2, 6: 3, 7: 4}  # GPIO番号: ボタン位置(左から1〜4)
buttons = {gp: Pin(gp, Pin.IN, Pin.PULL_UP) for gp in BUTTON_PINS}

SEG_NAMES = ["A", "B", "C", "D", "E", "F", "G", "DP"]
GRID_LABELS = ["GRID1 (main display)", "GRID2 (button1 label)", "GRID3 (button2 label)",
               "GRID4 (button3 label)", "GRID5 (button4 label)", "GRID6 (stage lamps)"]
# 数字のセグメントパターン (bit0=A ... bit6=G, bit7=DP)
DIGIT = {0: 0x3F, 1: 0x06, 2: 0x5B, 3: 0x4F, 4: 0x66, 5: 0x6D, 6: 0x7D, 7: 0x07, 8: 0x7F, 9: 0x6F}
# TM1637の輝度コマンド 0x88|level : level 0..7 = デューティ 1/16, 2/16, 4/16, 10/16, 11/16, 12/16, 13/16, 14/16
BRIGHTNESS_DUTY = ["1/16", "2/16", "4/16", "10/16", "11/16", "12/16", "13/16", "14/16"]

ack_ok = 0
ack_ng = 0
current_brightness = 7


def blink(pin, n, interval=0.15):
    for _ in range(n):
        pin.value(1)
        time.sleep(interval)
        pin.value(0)
        time.sleep(interval)


# ---- 最小限のTM1637プロトコル実装(配線確認用。本番ドライバではない) ----
# 9番目のクロックでDIOを解放(内部プルアップ付き入力)してACKを読み取り、成否をバイト単位で数える。
def _start():
    DIO.value(1)
    CLK.value(1)
    time.sleep_us(2)
    DIO.value(0)


def _stop():
    CLK.value(0)
    time.sleep_us(2)
    DIO.value(0)
    time.sleep_us(2)
    CLK.value(1)
    time.sleep_us(2)
    DIO.value(1)


def _write_byte(b):
    global ack_ok, ack_ng
    for i in range(8):
        CLK.value(0)
        DIO.value((b >> i) & 1)
        time.sleep_us(3)
        CLK.value(1)
        time.sleep_us(3)
    CLK.value(0)                        # 8番目のクロックの立ち下がり: TM1637がACK(DIOをLow)を出す
    DIO.init(Pin.IN, Pin.PULL_UP)       # Pico側はDIOを解放(ACKが無ければ内部プルアップでHighに見える)
    time.sleep_us(5)
    CLK.value(1)                        # 9番目のクロック
    time.sleep_us(3)
    if DIO.value() == 0:
        ack_ok += 1
    else:
        ack_ng += 1
    CLK.value(0)
    time.sleep_us(3)
    DIO.init(PIN_DRIVE)


def set_brightness(level):
    """level 0..7 (0x88|level = 表示ON)。"""
    global current_brightness
    current_brightness = level
    _start()
    _write_byte(0x88 | level)
    _stop()


def tm1637_write_grid(grid_index, seg_byte):
    """grid_index: 0-5 (GRID1-6), seg_byte: bit0=SEG1(=SEG_A) ... bit7=SEG8(=SEG_DP)"""
    _start()
    _write_byte(0x44)  # 固定アドレスモードで書き込み
    _stop()
    _start()
    _write_byte(0xC0 | grid_index)  # 表示アドレス指定(C0H-C5H)
    _write_byte(seg_byte)
    _stop()
    set_brightness(current_brightness)


def tm1637_clear():
    for g in range(6):
        tm1637_write_grid(g, 0x00)


def report_ack(title):
    total = ack_ok + ack_ng
    pct = (100.0 * ack_ok / total) if total else 0.0
    print("  [{}] ACK: {}/{} ({:.1f}%) NG={}".format(title, ack_ok, total, pct, ack_ng))


print("=== Memory module bring-up test start (TM1637 VDD = {}, CLK/DIO drive = {}) ===".format(VDD_LABEL, "open-drain" if OPEN_DRAIN else "push-pull"))
blink(STATUS_LED, 3)  # 状態LED回路の生存確認

# ---------------- [1] 通信テスト ----------------
print("[1] Communication test: 100 x (6 grids write) ...")
ack_ok = ack_ng = 0
set_brightness(7)
for n in range(100):
    for g in range(6):
        tm1637_write_grid(g, 0x00)
report_ack("comm")
if ack_ng:
    print("  !! ACK failures detected. If ALL bytes fail: check CLK/DIO wiring, VDD, GND. "
          "If only some fail: suspect VIH margin (VDD=5V) or noise -> see the bring-up doc, section 7 (troubleshooting)")
else:
    print("  OK: every byte was acknowledged by the TM1637")

# ---------------- [2] 輝度スイープ ----------------
print("[2] Brightness sweep (all displays + all lamps ON). Watch brightness and flicker.")
for g in range(6):
    tm1637_write_grid(g, 0xFF)
for lv in range(8):
    set_brightness(lv)
    print("  brightness level {} (duty {})  VDD={}".format(lv, BRIGHTNESS_DUTY[lv], VDD_LABEL))
    time.sleep(2)
set_brightness(7)
report_ack("after sweep")

# ---------------- [3] セグメント歩行 ----------------
print("[3] Segment walk: displays (GRID1-5) x segments (SEG1-8), one at a time")
for g in range(5):
    for s in range(8):
        tm1637_clear()
        tm1637_write_grid(g, 1 << s)
        print("  {} SEG{} ({})".format(GRID_LABELS[g], s + 1, SEG_NAMES[s]))
        time.sleep(0.15)

# ---------------- [4] 数字テスト ----------------
print("[4] Digit test: each display shows 1, 2, 3, 4 in turn (segment mapping check)")
for d in (1, 2, 3, 4):
    tm1637_clear()
    for g in range(5):
        tm1637_write_grid(g, DIGIT[d])
    print("  all 5 displays show '{}'".format(d))
    time.sleep(1.5)
# ゲームの表示例: メイン=3、ボタン(位置1〜4)=2 4 1 3
tm1637_clear()
for g, d in enumerate((3, 2, 4, 1, 3)):
    tm1637_write_grid(g, DIGIT[d])
print("  game-like sample: main=3, buttons=2 4 1 3 (hold 3 s)")
time.sleep(3)

# ---------------- [5] ステージランプ + ボタン監視 ----------------
print("[5] Stage lamps: GRID6, SEG_A-E one at a time, then cumulative")
tm1637_clear()
for s in range(5):
    tm1637_clear()
    tm1637_write_grid(5, 1 << s)
    print("  lamp {} (SEG_{})".format(s + 1, SEG_NAMES[s]))
    time.sleep(0.3)
for s in range(5):
    tm1637_write_grid(5, (1 << (s + 1)) - 1)
    print("  stage {} cleared: lamps 1..{} ON".format(s + 1, s + 1))
    time.sleep(0.4)

print("Holding: all displays + all stage lamps ON, entering button monitor loop")
print("(press each button; the corresponding position number should print, and the status LED should light while held)")
for g in range(6):
    tm1637_write_grid(g, 0xFF)
report_ack("total so far")

prev_state = {gp: 1 for gp in BUTTON_PINS}  # プルアップなので未押下=1

while True:
    any_pressed = False
    for gp, pos in BUTTON_PINS.items():
        val = buttons[gp].value()
        if val == 0:
            any_pressed = True
            if prev_state[gp] == 1:
                print("Button position {} (GPIO{}) pressed".format(pos, gp))
        else:
            if prev_state[gp] == 0:
                print("Button position {} (GPIO{}) released".format(pos, gp))
        prev_state[gp] = val
    STATUS_LED.value(1 if any_pressed else 0)
    time.sleep(0.02)
