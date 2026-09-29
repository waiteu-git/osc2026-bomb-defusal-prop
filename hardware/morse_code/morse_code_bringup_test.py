# Morse Code module - hardware bring-up test (MicroPython, Raspberry Pi Pico 2)
# 目的: 配線確認 + 仕様(モールス点滅/周波数16段巡回/TX判定)の試作動作確認。
#       本番のファームウェアはソフト担当がShizuku(C++/Pico SDK)で別途実装する。
#
# 配線 (hardware/morse_code/morse_code.kicad_sch と一致。kicad-cliのnetlistで全ネット確認済み):
#   GPIO2 : ランプLED(オレンジ)  GPIO2 → 330Ω → LEDアノード、LEDカソード → GND  (約3.6mA。47Ωだと理論25mAでGPIOの許容超過)
#   GPIO3 : TM1637 CLK
#   GPIO4 : TM1637 DIO
#   GPIO5 : ◀ボタン(周波数DOWN)  もう片方はGND、内部プルアップ使用(外付け抵抗なし)
#   GPIO6 : ▶ボタン(周波数UP)    同上
#   GPIO7 : TXボタン              同上
#   GPIO8 : 状態LED(緑)          GPIO8 → 47Ω → LEDアノード、LEDカソード → GND
#   GPIO0/1 : UART0(ホスト通信用、予約) このテストでは未使用
#   (E9対策: GPIO2/GPIO8のLED駆動ピンは起動直後に出力Lowにし、入力に切り替えない)
#   TM1637: VDD=5V、GND共通、GRID1〜4 = 表示器の桁(DIG1〜4 = 左から)、SEG1〜8 = 表示器のA,B,C,D,E,F,G,DP
#           (表示器 OSL40562-IR = アノードコモン。SEGn↔物理セグメントの対応はデータシート図から確定済み→ステップ3で点灯確認)
#
# 使い方: Thonny等でPico 2に書き込んで実行(F5)。詳細な手順・期待される出力は
#         hardware/morse_code/morse_code_bringup_procedure.md を参照。

from machine import Pin
import time
import random

# ---- ピン ---------------------------------------------------------------
LAMP_PIN = 2
CLK_PIN = 3
DIO_PIN = 4
BTN_DOWN_PIN = 5
BTN_UP_PIN = 6
BTN_TX_PIN = 7
STATUS_PIN = 8

# ---- 仕様パラメータ(設計メモ§4) ---------------------------------------
T_MS = 200          # 単位時間T
DOT = 1             # 点 = 1T
DASH = 3            # 線 = 3T
INTRA_GAP = 1       # 符号内の間隔 = 1T
LETTER_GAP = 3      # 文字間 = 3T
REPEAT_GAP = 7      # 単語の繰り返し前の長休止 = 7T
WRAP = True         # ◀▶で端に達したとき反対側へ回り込む
BRIGHTNESS = 2      # 0..7 = パルス幅 1/16,2/16,4/16,10/16,11/16,12/16,13/16,14/16 (電流を抑えるため低め)

# 16語と周波数(公式マニュアル/KTANE Wikiの表)
WORDS = [
    ("shell", "3.505"), ("halls", "3.515"), ("slick", "3.522"), ("trick", "3.532"),
    ("boxes", "3.535"), ("leaks", "3.542"), ("strobe", "3.545"), ("bistro", "3.552"),
    ("flick", "3.555"), ("bombs", "3.565"), ("break", "3.572"), ("brick", "3.575"),
    ("steak", "3.582"), ("sting", "3.592"), ("vector", "3.595"), ("beats", "3.600"),
]

# 国際モールス符号(16語で使う18文字のみ)
MORSE = {
    "a": ".-", "b": "-...", "c": "-.-.", "e": ".", "f": "..-.", "g": "--.",
    "h": "....", "i": "..", "k": "-.-", "l": ".-..", "m": "--", "n": "-.",
    "o": "---", "r": ".-.", "s": "...", "t": "-", "v": "...-", "x": "-..-",
}

# 7セグのフォント: bit0=A ... bit6=G, bit7=DP (論理セグメント)
FONT = {"0": 0x3F, "1": 0x06, "2": 0x5B, "3": 0x4F, "4": 0x66,
        "5": 0x6D, "6": 0x7D, "7": 0x07, "8": 0x7F, "9": 0x6F}
DP_BIT = 0x80
SEG_NAMES = ["A", "B", "C", "D", "E", "F", "G", "DP"]
SEG_POS = ["上", "右上", "右下", "下", "左下", "左上", "中", "小数点"]

# 論理セグメント(A,B,C,D,E,F,G,DP) → TM1637のSEGビット番号(0=SEG1 ... 7=SEG8)、桁ごと。
# ステップ3の実測で対応がずれていたら、ここを書き換えれば回路変更なしで吸収できる。
REMAP = [list(range(8)) for _ in range(4)]


# ---- ハードウェア非依存のロジック(PC上でも模擬検証できる) ---------------
def morse_events(word):
    """単語 → [(ランプ状態, 長さ[T単位]), ...]。末尾に繰り返し前の長休止(REPEAT_GAP)を含む。"""
    ev = []
    letters = list(word)
    for li, ch in enumerate(letters):
        code = MORSE[ch]
        for ei, sym in enumerate(code):
            ev.append((1, DOT if sym == "." else DASH))
            if ei != len(code) - 1:
                ev.append((0, INTRA_GAP))
        if li != len(letters) - 1:
            ev.append((0, LETTER_GAP))
    ev.append((0, REPEAT_GAP))
    return ev


def loop_ms(events):
    return sum(d for _, d in events) * T_MS


def encode_digit(pattern, digit):
    """論理パターン(bit0=A..bit7=DP)を、桁digit(0..3)のREMAPに従ってTM1637のSEGビットへ変換。"""
    out = 0
    for logical in range(8):
        if pattern & (1 << logical):
            out |= 1 << REMAP[digit][logical]
    return out


def freq_patterns(freq):
    """'3.505' → GRID1..4に書くバイト列(先頭の桁にだけ小数点DPを付ける)。"""
    digits = freq.replace(".", "")
    assert len(digits) == 4
    pats = []
    for i, d in enumerate(digits):
        p = FONT[d] | (DP_BIT if i == 0 else 0)
        pats.append(encode_digit(p, i))
    return pats


def next_index(idx, delta, n=16, wrap=True):
    j = idx + delta
    if wrap:
        return j % n
    return max(0, min(n - 1, j))


# ---- ハードウェア ---------------------------------------------------------
# RP2350エラッタE9対策(ハブ連絡事項): LED駆動ピンは起動直後に出力Lowにし、入力モードで使わない。
# 点灯中(High)のピンを入力に切り替えない。(影響はRP2350のA2ステッピングのみ、A3以降は修正済み)
LAMP = Pin(LAMP_PIN, Pin.OUT, value=0)
STATUS = Pin(STATUS_PIN, Pin.OUT, value=0)
CLK = Pin(CLK_PIN, Pin.OUT)
DIO = Pin(DIO_PIN, Pin.OUT)


def _dly():
    time.sleep_us(5)


def tm_start():
    DIO.init(Pin.OUT)
    DIO.value(1)
    CLK.value(1)
    _dly()
    DIO.value(0)
    _dly()


def tm_stop():
    CLK.value(0)
    _dly()
    DIO.value(0)
    _dly()
    CLK.value(1)
    _dly()
    DIO.value(1)
    _dly()


def tm_write_byte(b):
    """1バイト送信(LSBファースト)。ACKを読んでTrue/Falseで返す(配線・電圧レベルの診断用)。"""
    for i in range(8):
        CLK.value(0)
        DIO.value((b >> i) & 1)
        _dly()
        CLK.value(1)
        _dly()
    CLK.value(0)
    DIO.init(Pin.IN, Pin.PULL_UP)   # 8クロック目の立ち下がり直後にDIOを開放してACKを読む(CLKがHighの間はDIOを変えられない=STOP/STARTになるため、TM1637がLowに引き始めるのと数us重なり得る)
    _dly()
    CLK.value(1)
    ack = (DIO.value() == 0)
    _dly()
    CLK.value(0)
    DIO.init(Pin.OUT)
    DIO.value(0)
    _dly()
    return ack


def tm_write_grid(g, data):
    """固定アドレスモードで1桁(GRID g=0..5)に1バイト書く。全ACKがOKならTrue。"""
    tm_start()
    a = tm_write_byte(0x44)
    tm_stop()
    tm_start()
    b = tm_write_byte(0xC0 | g)
    c = tm_write_byte(data)
    tm_stop()
    tm_start()
    d = tm_write_byte(0x88 | BRIGHTNESS)
    tm_stop()
    return a and b and c and d


def tm_show(pats):
    """4桁分(GRID1..4)のバイト列を自動インクリメントで一括表示。GRID5/6は消灯。"""
    tm_start()
    a = tm_write_byte(0x40)
    tm_stop()
    tm_start()
    b = tm_write_byte(0xC0)
    ok = a and b
    for byte in list(pats) + [0, 0]:
        r = tm_write_byte(byte)
        ok = ok and r
    tm_stop()
    tm_start()
    r = tm_write_byte(0x88 | BRIGHTNESS)
    tm_stop()
    return ok and r


def tm_clear():
    return tm_show([0, 0, 0, 0])


class Button:
    """内部プルアップ入力のデバウンス付きボタン(押下の瞬間だけ .fell が True)。"""

    def __init__(self, pin_no):
        self.pin = Pin(pin_no, Pin.IN, Pin.PULL_UP)
        self.stable = 1
        self.last = 1
        self.t = 0
        self.fell = False

    def update(self, now):
        self.fell = False
        v = self.pin.value()
        if v != self.last:
            self.last = v
            self.t = now
        elif v != self.stable and time.ticks_diff(now, self.t) >= 20:
            self.stable = v
            if v == 0:
                self.fell = True


def blink(pins, n, interval=0.15):
    for _ in range(n):
        for p in pins:
            p.value(1)
        time.sleep(interval)
        for p in pins:
            p.value(0)
        time.sleep(interval)


def show_freq(freq):
    return tm_show(freq_patterns(freq))


# ---- 試験ステップ ---------------------------------------------------------
def step1_leds():
    print("[ステップ1] 状態LED(緑)とランプ(オレンジ)を3回ずつ点滅")
    blink([STATUS], 3)
    blink([LAMP], 3)


def step2_ack():
    print("[ステップ2] TM1637との通信(ACK)確認")
    ok = tm_clear()
    print("  TM1637 ACK:", "OK" if ok else "NG (配線/電源5V/CLK・DIOの電圧レベルを確認)")
    return ok


def step3_segment_scan():
    print("[ステップ3] 桁ごと・SEGごとに1箇所ずつ点灯。実際に光った位置を記録すること")
    print("  期待(データシート図に基づく対応): SEG1=A(上) SEG2=B(右上) SEG3=C(右下) SEG4=D(下) SEG5=E(左下) SEG6=F(左上) SEG7=G(中) SEG8=DP")
    for g in range(4):
        for s in range(8):
            tm_clear()
            tm_write_grid(g, 1 << s)
            print("  GRID%d(左から%d桁目) SEG%d  期待=%s(%s)" % (g + 1, g + 1, s + 1, SEG_NAMES[s], SEG_POS[s]))
            time.sleep(0.6)
    tm_clear()


def step4_show_freq():
    print("[ステップ4] 全セグメント点灯 → 「3.505」表示(REMAPが正しければ数字が正しく読める)")
    tm_show([0xFF, 0xFF, 0xFF, 0xFF])
    time.sleep(1.0)
    show_freq("3.505")
    print("  「3.505」(左端の桁の後ろに小数点)と読めればOK。乱れていればREMAPを実測に合わせて修正")
    time.sleep(3.0)


def game():
    """1ラウンド: ランダムな語をモールスで点滅。◀▶で周波数、TXで判定。正解で状態LED点灯→次ラウンド。"""
    target = random.randint(0, len(WORDS) - 1)
    idx = 0 if target != 0 else 8            # 開始周波数(正解と一致しないようにする)
    word, tfreq = WORDS[target]
    events = morse_events(word)
    print("[新ラウンド] 送信語=%s  正解周波数=%s MHz  (テスト用に表示。本番では表示しない)" % (word, tfreq))
    print("  1周の長さ = %d ms" % loop_ms(events))
    show_freq(WORDS[idx][1])
    b_down = Button(BTN_DOWN_PIN)
    b_up = Button(BTN_UP_PIN)
    b_tx = Button(BTN_TX_PIN)
    STATUS.value(0)
    ev = 0
    t_next = time.ticks_ms()
    solved_until = None
    while True:
        now = time.ticks_ms()
        if solved_until is None and time.ticks_diff(now, t_next) >= 0:
            level, dur = events[ev]
            LAMP.value(level)
            t_next = time.ticks_add(t_next, dur * T_MS)   # 前回の目標時刻に足す(ポーリング遅れを累積させない)
            ev = (ev + 1) % len(events)
        b_down.update(now)
        b_up.update(now)
        b_tx.update(now)
        if solved_until is not None:
            if time.ticks_diff(now, solved_until) >= 0:
                STATUS.value(0)
                return
        else:
            if b_down.fell:
                idx = next_index(idx, -1, len(WORDS), WRAP)
                show_freq(WORDS[idx][1])
                print("  ◀ 周波数 %s MHz" % WORDS[idx][1])
            if b_up.fell:
                idx = next_index(idx, +1, len(WORDS), WRAP)
                show_freq(WORDS[idx][1])
                print("  ▶ 周波数 %s MHz" % WORDS[idx][1])
            if b_tx.fell:
                if idx == target:
                    print("  TX: 正解! 解除(状態LED点灯、ランプ消灯)")
                    LAMP.value(0)
                    STATUS.value(1)
                    solved_until = time.ticks_add(now, 3000)
                else:
                    print("  TX: ストライク(周波数 %s は誤り。ホストへ通知する想定)" % WORDS[idx][1])
                    LAMP.value(0)
                    for _ in range(3):
                        LAMP.value(1)
                        time.sleep_ms(100)
                        LAMP.value(0)
                        time.sleep_ms(100)
                    ev = len(events) - 1               # 繰り返し前の長休止から再開(語頭が分かるように)
                    t_next = time.ticks_ms()
        time.sleep_ms(2)


def main():
    print("=== Morse Code module bring-up test start ===")
    step1_leds()
    step2_ack()
    step3_segment_scan()
    step4_show_freq()
    print("[ステップ5] 対話デモ: ◀▶で周波数、TXで判定。Ctrl+Cで終了")
    while True:
        game()


if __name__ == "__main__":
    main()
