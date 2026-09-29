# Simon module - game-logic demo (MicroPython, Raspberry Pi Pico 2 / Pico 2 W)
# 目的: 配線確認用のsimon_bringup_test.pyとは別に、公式マニュアル8ページ「サイモン」の
#       ゲームロジック(点滅シーケンス、母音・ストライク数で変わる対応表、ストライク、解除)が
#       実機で一通り動く様子を確認するデモ。本番ファームウェア(Shizuku)はソフト担当が別途実装する。
#
# 配線は simon_bringup_test.py と同じ (GPIO2-5=ボタン, GPIO6-9=色LEDドライバ, GPIO10=状態LED)。
#
# ホスト通信(UART)はまだ無いため、本来ホストから受け取る2つの値をここでは手元で決める:
#   HAS_VOWEL : シリアルナンバーに母音を含むか (共有情報バイトのbit1に相当)
#   ストライク数: ホスト側の爆弾全体のストライク数の代わりに、このデモが自分で数える
#
# 挙動 (design_notes.md §6 の設計判断。公式マニュアルに書かれていない値は調整用の定数):
#   - 起動時に3〜5段のシーケンス(赤/青/緑/黄のランダム)を決める
#   - 段が進むごとに、先頭から1個ずつ増やして光らせる(段k: 先頭からk個)
#   - プレイヤーは対応表で変換した色のボタンを、同じ順に押す
#   - 間違えるとストライク: 全色が1回光り、同じ段の点滅をやり直す。ストライク数が増えると
#     対応表の行が変わるので、その段の入力を最初からやり直す
#   - 最後の段を正しく押し切ると解除: 全色が2回点滅し、状態LED(緑)が点灯して停止する
#
# 使い方: Thonnyで実行。REPLに進行状況が表示される。

from machine import Pin
import os
import time

RED, BLUE, GREEN, YELLOW = 0, 1, 2, 3
NAMES = ("RED", "BLUE", "GREEN", "YELLOW")
BTN_GPIO = (2, 3, 4, 5)
LED_GPIO = (6, 7, 8, 9)
STATUS_GPIO = 10

HAS_VOWEL = True          # ホストの共有情報バイトbit1の代わり。False にすると母音なし表を使う

FLASH_ON_MS = 450         # 1回の点灯時間 (設計値)
FLASH_GAP_MS = 250        # 点灯と点灯の間 (設計値)
REPLAY_IDLE_MS = 5000     # 入力が無いまま経過したら点滅をやり直す (設計値)
STAGE_PAUSE_MS = 700      # 段クリア・ストライク後の待ち。この後に FLASH_GAP_MS の前置きが入り、暗い時間は約950ms (設計値)
DEBOUNCE_MS = 20

# 対応表: TABLE[(母音あり, ストライク行)][点滅した色] = 押すべき色。色の添字は 赤0/青1/緑2/黄3
# ストライク行: 0=ストライク無し, 1=1回, 2=2回以上
# 出典: 公式マニュアル日本語版8ページ「サイモン」(ktane.timwi.de の英語版と6行×4列すべて一致を確認済み)。
#       日本語版の行ラベルは ミスなし/1ミス/2ミス で、2ミスは英語版の 2+ に相当
TABLE = {
    (True, 0): (BLUE, RED, YELLOW, GREEN),
    (True, 1): (YELLOW, GREEN, BLUE, RED),
    (True, 2): (GREEN, RED, YELLOW, BLUE),
    (False, 0): (BLUE, YELLOW, GREEN, RED),
    (False, 1): (RED, BLUE, YELLOW, GREEN),
    (False, 2): (YELLOW, GREEN, BLUE, RED),
}

buttons = [Pin(g, Pin.IN, Pin.PULL_UP) for g in BTN_GPIO]
leds = [Pin(g, Pin.OUT, value=0) for g in LED_GPIO]
status = Pin(STATUS_GPIO, Pin.OUT, value=0)

seq = []
strikes = 0


def rand_below(n):
    # os.urandom は MicroPython(RP2)でも使える。4や3で割るので偏りは無視できる程度
    return os.urandom(1)[0] % n


def press_for(flash_color):
    return TABLE[(HAS_VOWEL, min(strikes, 2))][flash_color]


def all_leds(v):
    for led in leds:
        led.value(v)


def flash_all(times, on_ms=250, off_ms=200):
    for _ in range(times):
        all_leds(1)
        time.sleep_ms(on_ms)
        all_leds(0)
        time.sleep_ms(off_ms)


def play_sequence(stage):
    # 段 stage(0始まり)では、先頭から stage+1 個を光らせる
    time.sleep_ms(FLASH_GAP_MS)
    for i in range(stage + 1):
        c = seq[i]
        leds[c].value(1)
        time.sleep_ms(FLASH_ON_MS)
        leds[c].value(0)
        time.sleep_ms(FLASH_GAP_MS)


def read_press(timeout_ms):
    # 押されたボタンの色を返す。押している間はその色のLEDを点灯し、離されるまで待つ。
    # timeout_ms の間何も押されなければ None。
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
        for i in range(4):
            if buttons[i].value() == 0:
                time.sleep_ms(DEBOUNCE_MS)
                if buttons[i].value() == 0:
                    leds[i].value(1)
                    while buttons[i].value() == 0:
                        time.sleep_ms(5)
                    leds[i].value(0)
                    return i
        time.sleep_ms(5)
    return None


def solved():
    print("解除! ストライク{}回で完了".format(strikes))
    flash_all(2)
    status.value(1)
    while True:
        time.sleep_ms(100)


def main():
    global seq, strikes
    n_stages = 3 + rand_below(3)
    seq = [rand_below(4) for _ in range(n_stages)]
    strikes = 0
    print("=== Simon game-logic demo start ===")
    print("段数={} 母音={}".format(n_stages, HAS_VOWEL))
    print("点滅シーケンス(答え合わせ用): {}".format([NAMES[c] for c in seq]))
    flash_all(1)

    stage = 0
    while True:
        print("段{}/{}: 点滅".format(stage + 1, n_stages))
        play_sequence(stage)
        pos = 0
        while pos <= stage:
            c = read_press(REPLAY_IDLE_MS)
            if c is None:
                print("入力が無いので点滅をやり直します")
                play_sequence(stage)
                pos = 0
                continue
            expected = press_for(seq[pos])
            if c == expected:
                pos += 1
            else:
                strikes += 1
                print("ストライク! (押した={} 正解={}) ストライク合計{}".format(NAMES[c], NAMES[expected], strikes))
                flash_all(1, 300, 0)
                time.sleep_ms(STAGE_PAUSE_MS)
                play_sequence(stage)
                pos = 0
        if stage == n_stages - 1:
            solved()
        print("段{} クリア".format(stage + 1))
        time.sleep_ms(STAGE_PAUSE_MS)
        stage += 1


if __name__ == "__main__":
    main()
