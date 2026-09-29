# Timer/strike-count display module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認と「TM1637のVDD(5V/3.3V)・CLK/DIO駆動方式・プルアップ」の実測比較のみ。
#       本番のファームウェアはソフト担当が別途実装する。
#
# 配線:
#   GPIO0/1 : ホストとのUART専用線(GPIO0=UART0 TX→ホスト、GPIO1=UART0 RX←ホスト、通信専用で予約)。今回のテストでは未使用
#             (2026-09-24 ハブ確定: I2C共有バスは廃止、区画ごとのUART専用線に変更。I2Cアドレスの概念は無い)
#   GPIO2   : TM1637 CLK
#   GPIO3   : TM1637 DIO
#   GPIO4   : 失敗回数LED1 (330Ω経由でLED→GND)
#   GPIO5   : 失敗回数LED2 (330Ω経由でLED→GND)
#
# TM1637 - 表示器間の配線(このユニット内で固定、Pico側からは関与しない):
#   GRID1-4 = 7セグ表示器4桁(MM:SS)の桁選択(GRID1=分の十の位 ... GRID4=秒の一の位)
#   GRID5/6 = コロンLED2個(アノード)。カソードはSEG1側に共通接続(SEG1=A と同じ線)
#   SEG1-8  = 7セグのA,B,C,D,E,F,G,DPセグメント共通バス(SEG1=A, SEG2=B, ... SEG7=G, SEG8=DP)
#
# ★ VDDの比較(ブレッドボードで「VDDの線だけ」付け替える。他の配線は変えない):
#   3.3Vモード: TM1637 VDD → Picoの3V3(OUT)(物理ピン36)
#   5Vモード  : TM1637 VDD → PicoのVBUS(物理ピン40、USB給電時に約5V)
#   どちらもVDD-GND間に0.1uF(セラミック)+100uF(電解)をICの近くに入れる。
#   下の3つの設定(VDD_LABEL / DRIVE / PULLUP_LABEL)を、実際の配線に合わせて書き換えてから実行する。
#   VDD_LABELとPULLUP_LABELはログ表示用のみ(動作は変わらない)。DRIVEだけが動作を変える。
#
# ★ 比較する組み合わせ(動作確認手順.md §4の表と同じ):
#   A. VDD=3V3, DRIVE=push-pull,  プルアップ無し           ← 現行設計(回路図のJP1=1-2)
#   B. VDD=5V,  DRIVE=push-pull,  プルアップ無し           ← Picoの3.3V出力がHighしきい値(0.7×VDD=3.5V)未満
#   C. VDD=5V,  DRIVE=open-drain, CLK/DIOに10kΩ→VDD(5V)   ← Highが5Vになる。5V印加時のGPIO耐圧に注意(下記)
#   D. VDD=3V3, DRIVE=open-drain, CLK/DIOに10kΩ→3V3        ← プルアップ有り/無しの比較用(任意)
#   ※ push-pull駆動のまま10kΩプルアップを足してもHigh電圧は上がらない(意味が無い)。
#   ※ Cは、RP2350のGPIOが5V耐性を持つのは電源が入っている間だけ(要確認)。Pico側の電源を先に入れてから
#      5Vを印加すること(USB給電のPicoのVBUSを使えば自然にそうなる)。不安ならCは省略してよい。
#
# 使い方: Thonny等でPicoに書き込んで実行。
#   0. 起動時に失敗回数LED2個が3回点滅すればLED回路はOK
#   1. [comm]  6グリッド書き込みを繰り返し、TM1637のACK率をREPLに表示(通信成否の客観的な指標)
#   2. [bright] 全点灯のまま輝度レベル0〜7を2秒ずつ切替(明るさとチラつきを目視。スマホのカメラで撮ると縞で見える)
#   3. [walk]  桁ごと・セグメントごとに1箇所ずつ点灯(REPLの表示名と実際に光る位置が一致するか)
#   4. [digits] "12:34" → ゲーム風の"06:19" → 00:05からのカウントダウン(失敗回数LEDも連動)
#   5. [hold]  全桁・全セグメント・コロン・失敗回数LEDを最大輝度で同時点灯して停止
#              (USBパワーメーター等で消費電流を実測する)

from machine import Pin
import time

VDD_LABEL = "3V3"        # "3V3" or "5V"   (ログ表示用)
DRIVE = "push-pull"      # "push-pull" or "open-drain"  (open-drainは外付け10kΩプルアップ必須)
PULLUP_LABEL = "none"    # "none" / "10k->3V3" / "10k->VDD"  (ログ表示用)

BIT_DELAY_US = 5

if DRIVE == "open-drain":
    CLK = Pin(2, Pin.OPEN_DRAIN, value=1)
    DIO = Pin(3, Pin.OPEN_DRAIN, value=1)
else:
    CLK = Pin(2, Pin.OUT, value=1)
    DIO = Pin(3, Pin.OUT, value=1)
LED1 = Pin(4, Pin.OUT, value=0)
LED2 = Pin(5, Pin.OUT, value=0)

SEG_NAMES = ["A", "B", "C", "D", "E", "F", "G", "DP"]
# 0-9のセグメントパターン(bit0=SEG1=A ... bit6=SEG7=G, bit7=DP)
FONT = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F]
COLON = 0x01  # コロンLEDはSEG1(=A)を共通カソードにしている

ack_ok = 0
ack_total = 0


def blink(pins, n, interval=0.15):
    for _ in range(n):
        for p in pins:
            p.value(1)
        time.sleep(interval)
        for p in pins:
            p.value(0)
        time.sleep(interval)


# ---- 最小限のTM1637プロトコル実装(配線確認用。本番ドライバではない) ----
def _dio_release():
    if DRIVE == "push-pull":
        DIO.init(Pin.IN, Pin.PULL_UP)
    else:
        DIO.value(1)


def _dio_drive():
    if DRIVE == "push-pull":
        DIO.init(Pin.OUT)


def _start():
    DIO.value(1)
    CLK.value(1)
    time.sleep_us(BIT_DELAY_US)
    DIO.value(0)
    time.sleep_us(BIT_DELAY_US)


def _stop():
    CLK.value(0)
    time.sleep_us(BIT_DELAY_US)
    DIO.value(0)
    time.sleep_us(BIT_DELAY_US)
    CLK.value(1)
    time.sleep_us(BIT_DELAY_US)
    DIO.value(1)
    time.sleep_us(BIT_DELAY_US)


def _write_byte(b):
    """1バイト(LSBファースト)を送り、ACKビットを読む。ACKあり(DIOがLow)ならTrue。"""
    global ack_ok, ack_total
    for i in range(8):
        CLK.value(0)
        DIO.value((b >> i) & 1)
        time.sleep_us(BIT_DELAY_US)
        CLK.value(1)
        time.sleep_us(BIT_DELAY_US)
    CLK.value(0)
    _dio_release()  # 8クロック目の立ち下がり後、TM1637がDIOをLowにしてACKを返す
    time.sleep_us(BIT_DELAY_US)
    CLK.value(1)
    time.sleep_us(BIT_DELAY_US)
    ack = (DIO.value() == 0)
    CLK.value(0)
    _dio_drive()
    DIO.value(0)
    time.sleep_us(BIT_DELAY_US)
    ack_total += 1
    if ack:
        ack_ok += 1
    return ack


def tm1637_show(data6, brightness=7, on=True):
    """data6: GRID1..GRID6に出す6バイト(bit0=SEG1 ... bit7=SEG8)。brightness: 0..7(デューティ1/16〜14/16)"""
    _start()
    _write_byte(0x40)  # データ書き込み、アドレス自動加算
    _stop()
    _start()
    _write_byte(0xC0)  # 先頭アドレス(GRID1)
    for b in data6:
        _write_byte(b)
    _stop()
    _start()
    _write_byte((0x88 if on else 0x80) | (brightness & 7))  # 表示ON/OFFと輝度
    _stop()


def digits_pattern(d1, d2, d3, d4, colon=True):
    return [FONT[d1], FONT[d2], FONT[d3], FONT[d4], COLON if colon else 0, COLON if colon else 0]


def report_ack(label):
    pct = (100.0 * ack_ok / ack_total) if ack_total else 0.0
    print("[{}] ACK: {}/{} ({:.1f}%)".format(label, ack_ok, ack_total, pct))


print("=== Timer module bring-up test start ===")
print("設定: VDD={}, DRIVE={}, プルアップ={}".format(VDD_LABEL, DRIVE, PULLUP_LABEL))
blink([LED1, LED2], 3)  # 失敗回数LED回路の生存確認

tm1637_show([0] * 6)

print("[comm] 100回 x 6グリッドの書き込み(全点灯)でACK率を測定...")
for _ in range(100):
    tm1637_show([0xFF] * 6)
report_ack("comm")

print("[bright] 全点灯のまま輝度レベル0-7を2秒ずつ切替。明るさ・チラつきを目視で確認")
for level in range(8):
    tm1637_show([0xFF] * 6, brightness=level)
    print("  level {} (duty {}/16)".format(level, [1, 2, 4, 10, 11, 12, 13, 14][level]))
    time.sleep(2)

print("[walk] 桁(GRID1-4) x セグメント(SEG1-8)を1箇所ずつ点灯")
for g in range(4):
    for s in range(8):
        data = [0] * 6
        data[g] = 1 << s
        tm1637_show(data)
        print("  GRID{} (digit {}) SEG{} ({})".format(g + 1, g + 1, s + 1, SEG_NAMES[s]))
        time.sleep(0.3)

print("[walk] コロンLED(GRID5/6、SEG1経由)")
for g in (4, 5):
    data = [0] * 6
    data[g] = COLON
    tm1637_show(data)
    print("  GRID{} (colon LED)".format(g + 1))
    time.sleep(0.7)

print("[digits] 12:34 -> 06:19 -> 00:05からカウントダウン(失敗回数LEDも連動)")
tm1637_show(digits_pattern(1, 2, 3, 4))
time.sleep(3)
tm1637_show(digits_pattern(0, 6, 1, 9))
time.sleep(3)
LED1.value(1)
LED2.value(1)
for sec in range(5, -1, -1):
    tm1637_show(digits_pattern(0, 0, sec // 10, sec % 10))
    if sec == 3:
        LED2.value(0)
    if sec == 1:
        LED1.value(0)
    time.sleep(1)

report_ack("total")
print("[hold] 全桁・全セグメント・コロン・失敗回数LEDを最大輝度で同時点灯して停止。消費電流を実測してください")
tm1637_show([0xFF] * 6, brightness=7)
LED1.value(1)
LED2.value(1)
