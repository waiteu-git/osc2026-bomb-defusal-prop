#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ブリングアップスクリプト(morse_code_bringup_test.py)を、実機なしでPC上で検証するテスト。

    python tools/test_bringup_offdevice.py            # 通常のテスト
    python tools/test_bringup_offdevice.py --mutants  # スクリプトを壊して(変異させて)テストが検出できるか確認

仕組み: 偽の machine.Pin と仮想クロック(MicroPythonと同じ 2^30 で折り返すティック)を用意し、
スクリプトを読み込んで次を検証する。
  * 語/周波数の表が公式表と一致、モールス符号が独立に書いたITU符号表と一致(設計メモの表とも一致)
  * モールスのイベント列を、テスト側で独立に組み立てた期待値と比較、1周の長さが手順書の表と一致
  * 7セグの符号化、REMAPの桁ごとの適用、周波数の巡回/端止め
  * TM1637のビット送信を、CLK/DIOの変化+時刻から復号(バイト列、クロック幅、ACKクロックでDIOが入力になっていること)
  * 1ラウンドの模擬: ボタンのチャタリング、8msの短いグリッチ(無視されること)、ストライク→▶→1周以上経ってから正解、
    ランプの全ての変化時刻が理想の時刻表と±3ms以内(ティックの折り返しをまたぐ)。仮想時間の上限つき(無限ループ防止)
"""
import sys, os, types, io, re, importlib.util, contextlib, subprocess, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
SCRIPT = os.environ.get("BRINGUP_SCRIPT", os.path.join(MOD, "morse_code_bringup_test.py"))
NOTES = os.path.join(MOD, "morse_code_design_notes.md")
PROC = os.path.join(MOD, "morse_code_bringup_procedure.md")


# ---------------------------------------------------------------------------
# 変異テスト(--mutants): 壊したスクリプトでこのテストが失敗する(=検出できる)ことを確認する
# ---------------------------------------------------------------------------
def _mutants():
    def sub(old, new):
        return lambda s: s.replace(old, new)

    def late_release(s):
        return re.sub(r"(    DIO\.init\(Pin\.IN, Pin\.PULL_UP\)[^\n]*\n)(    _dly\(\)\n    CLK\.value\(1\)\n)", r"\2    DIO.init(Pin.IN, Pin.PULL_UP)\n", s)

    def burst2(s):
        return re.sub(r"for _ in range\(3\):(\n\s+LAMP\.value\(1\))", r"for _ in range(2):\1", s)

    def status_to_input(s):
        return re.sub(r"(\n(\s+)STATUS\.value\(1\)\n)", r"\1\2STATUS.init(Pin.IN)\n", s)

    return [
        ("M1  デバウンスなし", sub("elif v != self.stable and time.ticks_diff(now, self.t) >= 20:", "elif v != self.stable:")),
        ("M2  ストライク後に語頭から再開(長休止が消える)", sub("ev = len(events) - 1", "ev = 0")),
        ("M3  1周の末尾(繰り返し休止)を飛ばす", sub("ev = (ev + 1) % len(events)", "ev = (ev + 1) % (len(events) - 1)")),
        ("M4  ティック折り返しに非対応", sub("time.ticks_diff(now, t_next) >= 0", "now >= t_next")),
        ("M5  線を1Tで送る", sub("t_next = time.ticks_add(t_next, dur * T_MS)", "t_next = time.ticks_add(t_next, (1 if level else dur) * T_MS)")),
        ("M6  クロックの待ちが無い", sub("time.sleep_us(5)", "pass")),
        ("M7  ACKでDIOを9クロック目の後に開放", late_release),
        ("M8  誤った周波数を正解と判定", sub("if idx == target:", "if idx == (target + 1) % 16:")),
        ("M9  表の周波数が1つ違う", sub('("halls", "3.515")', '("halls", "3.516")')),
        ("M10 巡回せず端止め", sub("return j % n", "return max(0, min(n - 1, j))")),
        ("M11 TXと▶のピンが入れ替わり", sub("BTN_TX_PIN = 7", "BTN_TX_PIN = 6")),
        ("M12 小数点が2桁目に付く", sub("(DP_BIT if i == 0 else 0)", "(DP_BIT if i == 1 else 0)")),
        ("M13 ストライクの点滅が2回", burst2),
        ("M14 繰り返し前の休止が5T", sub("REPEAT_GAP = 7", "REPEAT_GAP = 5")),
        ("M15 ACKを見ない", sub("ack = (DIO.value() == 0)", "ack = True")),
        ("M16 ビット順(LSB/MSB)が逆", sub("DIO.value((b >> i) & 1)", "DIO.value((b >> (7 - i)) & 1)")),
        ("M17 表示制御コマンドが違う", sub("0x88 | BRIGHTNESS", "0x80 | BRIGHTNESS")),
        ("M18 単位時間Tが違う", sub("T_MS = 200", "T_MS = 250")),
        ("M19 LED駆動ピンの起動時Low指定なし(E9)", lambda s: s.replace("Pin(LAMP_PIN, Pin.OUT, value=0)", "Pin(LAMP_PIN, Pin.OUT)")),
        ("M20 解除時に状態LEDピンを入力に切り替える(E9)", status_to_input),
    ]


if "--mutants" in sys.argv:
    src = open(SCRIPT, encoding="utf-8").read()
    missed = []
    for name, fn in _mutants():
        mutated = fn(src)
        if mutated == src:
            print("NOT APPLIED  %s (変異の置換が当たらなかった。テストの更新が必要)" % name)
            missed.append(name)
            continue
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "morse_code_bringup_test.py")
            open(p, "w", encoding="utf-8").write(mutated)
            env = dict(os.environ, BRINGUP_SCRIPT=p, PYTHONIOENCODING="utf-8")
            try:
                r = subprocess.run([sys.executable, os.path.abspath(__file__)], env=env, capture_output=True, timeout=180)
                caught = r.returncode != 0
            except subprocess.TimeoutExpired:
                caught = False
        print(("CAUGHT       " if caught else "MISSED       ") + name)
        if not caught:
            missed.append(name)
    print("\n変異%d件中、検出できなかったもの: %s" % (len(_mutants()), missed if missed else "なし"))
    sys.exit(1 if missed else 0)


# ---------------------------------------------------------------------------
# 仮想クロックと偽ハードウェア
# ---------------------------------------------------------------------------
PERIOD = 2 ** 30                 # MicroPythonのticks_msと同じ折り返し
EPOCH_MS = PERIOD - 3000         # 仮想時間0の3秒後にティックが折り返す


class World:
    now_us = 0
    log = []                     # (時刻us, ピン番号, 値 | ('mode', モード))
    ext = {}                     # 入力ピンの外部レベル(ボタン)。既定は1(プルアップ)
    sched = []                   # (時刻ms, ピン, 値) ボタン操作の予定
    ack_ok = True
    clk = 0
    limit_us = 10 ** 12


W = World


class FakePin:
    IN, OUT, PULL_UP = 0, 1, 2

    def __init__(self, n, mode=None, pull=None, value=None):
        self.n, self.mode, self.pull = n, mode, pull
        self.init_value = value                      # コンストラクタで初期値を明示したか(E9: LED駆動ピンは起動時Low)
        self.v = 0 if value is None else value

    def init(self, mode=None, pull=None):
        self.mode, self.pull = mode, pull
        W.log.append((W.now_us, self.n, ("mode", mode)))

    def value(self, v=None):
        if v is None:
            if self.mode == FakePin.IN:
                if self.n == 4:                      # DIOを開放している間、TM1637がACKでLowに引く(CLKがHighの間だけ)
                    return 0 if (W.ack_ok and W.clk == 1) else 1
                return W.ext.get(self.n, 1)
            return self.v
        self.v = v
        if self.n == 3:
            W.clk = v
        W.log.append((W.now_us, self.n, v))


def _check_limit():
    if W.now_us > W.limit_us:
        raise TimeoutError("仮想時間の上限を超えた(ラウンドが終わらない)")


def _apply_schedule():
    for item in list(W.sched):
        t_ms, pin, val = item
        if t_ms * 1000 <= W.now_us:
            W.ext[pin] = val
            W.sched.remove(item)


def sleep_us(us):
    W.now_us += us


def sleep_ms(ms):
    W.now_us += ms * 1000
    _apply_schedule()
    _check_limit()


def sleep_s(s):
    W.now_us += int(s * 1e6)
    _apply_schedule()
    _check_limit()


machine = types.ModuleType("machine")
machine.Pin = FakePin
sys.modules["machine"] = machine
import time as _t
_t.sleep_us, _t.sleep_ms, _t.sleep = sleep_us, sleep_ms, sleep_s
_t.ticks_ms = lambda: (EPOCH_MS + W.now_us // 1000) % PERIOD
_t.ticks_add = lambda a, b: (a + b) % PERIOD
_t.ticks_diff = lambda a, b: ((a - b + PERIOD // 2) % PERIOD) - PERIOD // 2

spec = importlib.util.spec_from_file_location("bringup", SCRIPT)
bu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bu)


def reset(limit_s=None):
    W.now_us = 0
    W.log = []
    W.ext = {}
    W.sched = []
    W.ack_ok = True
    W.clk = 0
    W.limit_us = int(limit_s * 1e6) if limit_s else 10 ** 12


fails = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


# ---------------------------------------------------------------------------
# 1. 表・符号(公式表/独立のITU符号表/設計メモ/手順書との照合)
# ---------------------------------------------------------------------------
OFFICIAL = [("shell", "3.505"), ("halls", "3.515"), ("slick", "3.522"), ("trick", "3.532"),
            ("boxes", "3.535"), ("leaks", "3.542"), ("strobe", "3.545"), ("bistro", "3.552"),
            ("flick", "3.555"), ("bombs", "3.565"), ("break", "3.572"), ("brick", "3.575"),
            ("steak", "3.582"), ("sting", "3.592"), ("vector", "3.595"), ("beats", "3.600")]
check(bu.WORDS == OFFICIAL, "WORDS が公式の16語/周波数表と一致")

ITU = {"a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.", "g": "--.", "h": "....", "i": "..",
       "j": ".---", "k": "-.-", "l": ".-..", "m": "--", "n": "-.", "o": "---", "p": ".--.", "q": "--.-", "r": ".-.",
       "s": "...", "t": "-", "u": "..-", "v": "...-", "w": ".--", "x": "-..-", "y": "-.--", "z": "--.."}
used = sorted(set("".join(w for w, _ in OFFICIAL)))
check(sorted(bu.MORSE) == used, "MORSE は16語で使う%d文字だけ" % len(used))
check(all(bu.MORSE[c] == ITU[c] for c in bu.MORSE), "MORSE が独立に書いたITU符号表と一致")

notes = open(NOTES, encoding="utf-8").read()
rows = re.findall(r"^\| (\w+) \| (3\.\d{3}) MHz \| ([.\- ]+) \|$", notes, re.M)
check(len(rows) == 16, "設計メモに16語の行がある(%d)" % len(rows))
check(all(" ".join(bu.MORSE[c] for c in w) == code.strip() and dict(OFFICIAL)[w] == f for w, f, code in rows),
      "設計メモの16語の表(周波数+モールス符号)がスクリプトと一致")


def expected_events(word):
    """テスト側で独立に組み立てたイベント列: 点1T/線3T/符号内1T/文字間3T/末尾に繰り返し休止7T。"""
    ev = []
    for li, ch in enumerate(word):
        code = ITU[ch]
        for ei, sym in enumerate(code):
            ev.append((1, 1 if sym == "." else 3))
            if ei != len(code) - 1:
                ev.append((0, 1))
        if li != len(word) - 1:
            ev.append((0, 3))
    ev.append((0, 7))
    return ev


check(all(bu.morse_events(w) == expected_events(w) for w, _ in OFFICIAL), "16語すべてでイベント列が独立の期待値と一致")
check(bu.T_MS == 200, "単位時間T = 200ms")
check(bu.LAMP.init_value == 0 and bu.STATUS.init_value == 0, "E9: LED駆動ピン(ランプ/状態LED)を起動時に出力Lowで初期化している")

proc = open(PROC, encoding="utf-8").read()
tbl = re.findall(r"(\w+) \| (3\.\d{3}) \| (\d+)", proc)
check(len(tbl) == 16 and all(bu.loop_ms(bu.morse_events(w)) == int(ms) and dict(OFFICIAL)[w] == f for w, f, ms in tbl),
      "手順書§3の1周の長さの表(16語)がスクリプトの計算と一致")

# ---------------------------------------------------------------------------
# 2. 7セグ符号化・周波数の巡回
# ---------------------------------------------------------------------------
check(bu.freq_patterns("3.505") == [0x4F | 0x80, 0x6D, 0x3F, 0x6D], "「3.505」は先頭桁だけDP付き")
check(bu.freq_patterns("3.600") == [0x4F | 0x80, 0x7D, 0x3F, 0x3F], "「3.600」")
saved = [r[:] for r in bu.REMAP]
bu.REMAP[0] = [1, 0, 2, 3, 4, 5, 6, 7]
check(bu.encode_digit(0x01, 0) == 0x02 and bu.encode_digit(0x01, 1) == 0x01, "REMAPが桁ごとに効く")
bu.REMAP[:] = saved
check(bu.next_index(15, +1, 16, True) == 0 and bu.next_index(0, -1, 16, True) == 15, "巡回(回り込み)")
check(bu.next_index(15, +1, 16, False) == 15 and bu.next_index(0, -1, 16, False) == 0, "端止め")


# ---------------------------------------------------------------------------
# 3. TM1637のビット送信(バイト列・クロック幅・ACKクロックでDIOが入力)
# ---------------------------------------------------------------------------
def decode(log):
    clk = dio = None
    dio_mode = None
    tx = []
    cur = None
    bits = []
    edge = 0
    t_rise = t_fall = None
    min_w = 10 ** 9
    ack_ok_mode = True
    for t_us, pin, v in log:
        if isinstance(v, tuple):
            if pin == 4:
                dio_mode = v[1]
            continue
        if pin == 3:
            if v == 1 and clk == 0:
                if t_fall is not None and cur is not None:
                    min_w = min(min_w, t_us - t_fall)
                t_rise = t_us
                if cur is not None:
                    edge += 1
                    if edge % 9 == 0:                      # 9クロック目 = ACK
                        if dio_mode != FakePin.IN:
                            ack_ok_mode = False
                    else:
                        bits.append(dio)
                    if edge % 9 == 8:
                        cur.append(sum((b << i) for i, b in enumerate(bits[-8:])))
            elif v == 0 and clk == 1 and t_rise is not None:
                if cur is not None:
                    min_w = min(min_w, t_us - t_rise)
                t_fall = t_us
            clk = v
        elif pin == 4:
            if clk == 1 and dio is not None and v != dio:
                if v == 0:
                    cur = []
                    tx.append(cur)
                    edge = 0
                    bits = []
                else:
                    cur = None
            dio = v
    return tx, min_w, ack_ok_mode


def tm_log():
    return [e for e in W.log if e[1] in (3, 4)]


reset()
ok = bu.tm_write_grid(2, 0x4F)
tx, min_w, mode_ok = decode(tm_log())
check(ok is True, "tm_write_grid: ACKありでTrue")
check(tx == [[0x44], [0xC2, 0x4F], [0x88 | bu.BRIGHTNESS]], "tm_write_grid のバイト列 %s" % [[hex(b) for b in t] for t in tx])
check(min_w >= 4, "CLKのHigh/Lowの幅が4us以上(データシートは400ns以上)  最小=%dus" % min_w)
check(mode_ok, "ACKの9クロック目でDIOが入力(開放)になっている")
reset()
bu.tm_show([1, 2, 3, 4])
tx, min_w, mode_ok = decode(tm_log())
check(tx == [[0x40], [0xC0, 1, 2, 3, 4, 0, 0], [0x88 | bu.BRIGHTNESS]], "tm_show のバイト列 %s" % [[hex(b) for b in t] for t in tx])
check(min_w >= 4 and mode_ok, "tm_show でもクロック幅とACK開放が正しい")
reset()
W.ack_ok = False
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    r = bu.step2_ack()
check(r is False and "NG" in buf.getvalue(), "ACKが無ければNGと表示")
reset()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    r = bu.step2_ack()
check(r is True and "OK" in buf.getvalue(), "ACKがあればOKと表示")

reset()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    bu.step1_leds()
    bu.step3_segment_scan()
    bu.step4_show_freq()
out = buf.getvalue()
check(out.count("GRID") >= 32 and "3.505" in out, "ステップ1/3/4が最後まで動く(セグメント走査32行)")
check(not [e for e in W.log if e[1] in (2, 8) and isinstance(e[2], tuple)], "E9: ステップ1/3/4の間、LED駆動ピンのモードを変えない(入力に切り替えない)")

# ---------------------------------------------------------------------------
# 4. 1ラウンドの模擬: チャタリング/グリッチ/ストライク/▶/1周以上後に正解
# ---------------------------------------------------------------------------
import random

reset(limit_s=40)
targets = iter([1])                                  # 正解=halls(3.515)、開始=3.505
orig_randint = random.randint
random.randint = lambda a, b: next(targets)
W.sched = [
    (300, 7, 0), (308, 7, 1),                                                    # TXに8msのグリッチ(無視されるべき)
    (600, 7, 0), (604, 7, 1), (607, 7, 0), (611, 7, 1), (614, 7, 0),             # TXの押下(チャタリング)
    (700, 7, 1), (703, 7, 0), (706, 7, 1),                                       # TXの解放(チャタリング)
    (2000, 6, 0), (2100, 6, 1),                                                  # ▶を押す
    (13000, 7, 0), (13100, 7, 1),                                                # 1周以上経ってからTX(正解)
]
buf = io.StringIO()
timeout = False
try:
    with contextlib.redirect_stdout(buf):
        bu.game()
except TimeoutError:
    timeout = True
random.randint = orig_randint
out = buf.getvalue()
print(out)
check(not timeout, "ラウンドが仮想時間の上限内に終わる")
check(out.count("ストライク") == 1, "ストライクは1回だけ(グリッチとチャタリングで増えない)  実際=%d" % out.count("ストライク"))
check("▶ 周波数 3.515" in out and out.count("▶") == 1, "▶で3.505→3.515(1回だけ)")
check("正解!" in out and out.index("ストライク") < out.index("正解!"), "ストライク→正解の順")

lamp = [(t / 1000.0, v) for (t, p, v) in W.log if p == 2 and not isinstance(v, tuple)]
status = [(t / 1000.0, v) for (t, p, v) in W.log if p == 8 and not isinstance(v, tuple)]
ev_word = expected_events("halls")


def cyc(events, start_index):
    i = start_index
    while True:
        yield events[i % len(events)]
        i += 1


def compare_timeline(writes, t0, gen, t_limit, tol=3.0):
    """writes: [(t_ms, value)]  gen: 理想のイベント(level, T数)の並び。全ての書き込みが理想の時刻±tolか。"""
    t = t0
    n = 0
    for (tw, v), (lv, d) in zip(writes, gen):
        if tw >= t_limit:
            break
        if abs(tw - t) > tol or v != lv:
            return False, n, (tw, v, t, lv)
        t += d * 200.0
        n += 1
    return True, n, None


pre = [w for w in lamp if w[0] < 600]
ok1, n1, bad1 = compare_timeline(pre, pre[0][0], cyc(ev_word, 0), 600)
check(ok1 and n1 >= 3, "ストライク前: ランプの変化%d回が理想の時刻表(200ms格子)と±3ms以内 %s" % (n1, bad1 or ""))

i0 = next(i for i, w in enumerate(lamp) if w[1] == 1 and w[0] >= 600)          # ストライクの点滅の最初の点灯
burst = lamp[i0:i0 + 6]
check([v for _, v in burst] == [1, 0, 1, 0, 1, 0] and all(abs((burst[k + 1][0] - burst[k][0]) - 100) <= 3 for k in range(5)),
      "ストライクの点滅は3回(100ms点灯/100ms消灯)  時刻=%s" % [round(t) for t, _ in burst])
post = lamp[i0 + 6:]
tb = post[0][0]
ok2, n2, bad2 = compare_timeline(post, tb, cyc(ev_word, len(ev_word) - 1), 12990)
check(ok2 and n2 >= 30, "ストライク後: 長休止から再開し、1周の折り返しとティックの折り返しをまたいで%d回の変化が全て理想どおり %s" % (n2, bad2 or ""))
check(all(v == 0 for t, v in lamp if t > 13000), "正解後はランプが点灯しない")
check(not [e for e in W.log if e[1] in (2, 8) and isinstance(e[2], tuple)], "E9: ラウンドの間(ストライク/正解を含む)LED駆動ピンを入力に切り替えない")
check(len(status) >= 3 and status[-2][1] == 1 and status[-1][1] == 0 and status[-2][0] > 13000, "正解で状態LED点灯、ラウンド終了で消灯")

print("\nSUMMARY:", "ALL PASS" if not fails else "%d FAILURES: %s" % (len(fails), fails))
sys.exit(1 if fails else 0)
