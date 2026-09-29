#!/usr/bin/env python3
# simon_game_demo.py のゲームロジックを、実機なし(PC上)で検証するハーネス。
#   python simon_sim_check.py             # 7シナリオ x 40回 (数秒)
#   SIMON_DEMO=壊したコピー.py python simon_sim_check.py   # 対応表などを壊したコピーで失敗することの確認(ミューテーション)
#
# 仕組み: machine.Pin と time.sleep_ms/ticks_ms を仮想の時計とスクリプトで動くプレイヤーに差し替え、demo.main() を走らせる。
# プレイヤーの対応表は、マニュアル(英語版)の表から色名で独立に起こしたもので、demo の TABLE は使わない。
#
# 検証できること: 対応表の全行(母音あり/なし x ストライク0/1/2以上)、ストライクで同じ段のまま行が変わること、
#   無入力での再点滅、段数3/4/5、点滅列が答えの先頭部分列であること、最終的な解除。
# 検証できないこと(限界): 単独点灯が400ms以上のLEDだけを点滅として観測するため、点滅時間・間の長さ・演出のタイミングの誤りは見逃す。
#   実機の押し心地・明るさ・デバウンスも対象外。ストライク演出の内容(全色点灯)は検査していない。
import sys
sys.dont_write_bytecode = True
import os
import types, importlib.util, time, random

DEMO = os.environ.get("SIMON_DEMO", os.path.join(os.path.dirname(os.path.abspath(__file__)), "simon_game_demo.py"))
NAMES = ["Red", "Blue", "Green", "Yellow"]
BTN_GPIO = (2, 3, 4, 5)
LED_GPIO = (6, 7, 8, 9)
STATUS_GPIO = 10

# ktane.timwi.de "Simon Says" (English manual), flash colour -> button to press
MANUAL = {
    True: {  # serial contains a vowel
        0: {"Red": "Blue", "Blue": "Red", "Green": "Yellow", "Yellow": "Green"},
        1: {"Red": "Yellow", "Blue": "Green", "Green": "Blue", "Yellow": "Red"},
        2: {"Red": "Green", "Blue": "Red", "Green": "Yellow", "Yellow": "Blue"},
    },
    False: {  # no vowel
        0: {"Red": "Blue", "Blue": "Yellow", "Green": "Green", "Yellow": "Red"},
        1: {"Red": "Red", "Blue": "Blue", "Green": "Yellow", "Yellow": "Green"},
        2: {"Red": "Yellow", "Blue": "Green", "Green": "Blue", "Yellow": "Red"},
    },
}


class SimDone(Exception):
    pass


class Sim:
    def __init__(self, vowel, wrong_plan, idle_first=False, max_ms=600000):
        self.now = 0
        self.max_ms = max_ms
        self.vowel = vowel
        self.wrong_plan = list(wrong_plan)      # list of (display_index, position) presses to get wrong
        self.idle_first = idle_first
        self.btn = [1, 1, 1, 1]
        self.led = [0, 0, 0, 0]
        self.status = 0
        self.on_since = [None] * 4
        self.flashes = []                        # single-LED display flashes in current sequence
        self.last_flash_t = None
        self.displays = []                       # completed sequences (list of colour names)
        self.events = []                         # (t, idx, val)
        self.player_strikes = 0
        self.errors = []
        self.wrong_done = 0
        self.busy_until = 0
        self.idle_used = False

    # ---- fake hardware
    def on_out(self, gpio, v):
        if gpio in LED_GPIO:
            c = LED_GPIO.index(gpio)
            if v and not self.led[c]:
                self.on_since[c] = self.now
            if (not v) and self.led[c]:
                dur = self.now - (self.on_since[c] or self.now)
                others = sum(self.led) - 1
                if dur >= 400 and others == 0 and not any(b == 0 for b in self.btn):
                    self.flashes.append(NAMES[c])
                    self.last_flash_t = self.now
            self.led[c] = 1 if v else 0
        elif gpio == STATUS_GPIO:
            self.status = 1 if v else 0
            if v:
                raise SimDone()

    def sleep_ms(self, ms):
        for _ in range(int(ms)):
            self.now += 1
            if self.now > self.max_ms:
                raise TimeoutError("simulation exceeded %d ms" % self.max_ms)
            self.step()

    def ticks_ms(self):
        return self.now

    # ---- scripted player
    def step(self):
        while self.events and self.events[0][0] <= self.now:
            _, idx, val = self.events.pop(0)
            self.btn[idx] = val
        if (self.flashes and self.last_flash_t is not None and self.now - self.last_flash_t >= 900
                and not self.events and self.now >= self.busy_until):
            self.on_display(self.flashes)
            self.flashes = []
            self.last_flash_t = None

    def on_display(self, seq):
        idx = len(self.displays)
        self.displays.append(list(seq))
        if self.idle_first and not self.idle_used:
            self.idle_used = True
            self.busy_until = self.now + 6500     # deliberately do nothing past REPLAY_IDLE_MS
            return
        t = self.now + 300
        for pos, colour in enumerate(seq):
            row = min(self.player_strikes, 2)
            target = MANUAL[self.vowel][row][colour]
            press = NAMES.index(target)
            if (idx, pos) in self.wrong_plan and (idx, pos) not in getattr(self, "_used", set()):
                self._used = getattr(self, "_used", set()) | {(idx, pos)}
                press = (press + 1) % 4
                self.events += [(t, press, 0), (t + 120, press, 1)]
                self.player_strikes += 1
                self.wrong_done += 1
                return
            self.events += [(t, press, 0), (t + 120, press, 1)]
            t += 350


def run(vowel, wrong_plan, idle_first=False):
    sim = Sim(vowel, wrong_plan, idle_first)

    class FakePin:
        IN, OUT, PULL_UP = 0, 1, 2

        def __init__(self, gpio, mode=None, pull=None, value=None):
            self.gpio, self.mode = gpio, mode
            self._v = 0
            if value is not None:
                self.value(value)

        def value(self, v=None):
            if v is None:
                if self.mode == FakePin.IN:
                    return sim.btn[BTN_GPIO.index(self.gpio)]
                return self._v
            self._v = v
            sim.on_out(self.gpio, v)

    machine = types.ModuleType("machine")
    machine.Pin = FakePin
    sys.modules["machine"] = machine
    time.sleep_ms = sim.sleep_ms
    time.ticks_ms = sim.ticks_ms
    time.ticks_diff = lambda a, b: a - b

    spec = importlib.util.spec_from_file_location("simon_game_demo", DEMO)
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    demo.HAS_VOWEL = vowel

    import io, contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            demo.main()
    except SimDone:
        pass
    out = buf.getvalue()
    res = {"solved": sim.status == 1, "displays": sim.displays, "seq": [NAMES[c] for c in demo.seq],
           "demo_strikes": demo.strikes, "player_strikes": sim.player_strikes, "out": out}
    return res


def check(res, label, expect_strikes, idle=False):
    errs = []
    seq = res["seq"]
    n = len(seq)
    if not (3 <= n <= 5):
        errs.append("stage count %d not in 3..5" % n)
    if not res["solved"]:
        errs.append("not solved")
    if res["demo_strikes"] != expect_strikes:
        errs.append("demo strikes %d != expected %d" % (res["demo_strikes"], expect_strikes))
    disp = res["displays"]
    # every display must be a prefix of the secret sequence; lengths must be non-decreasing 1..n
    for d in disp:
        if d != seq[:len(d)]:
            errs.append("display %s is not a prefix of %s" % (d, seq))
    lens = [len(d) for d in disp]
    if lens and lens[-1] != n:
        errs.append("last displayed length %d != %d" % (lens[-1], n))
    if any(b < a for a, b in zip(lens, lens[1:])):
        errs.append("display length decreased: %s" % lens)
    if idle and not (len(disp) >= 2 and disp[0] == disp[1]):
        errs.append("idle replay did not re-display the same sequence: %s" % lens)
    return errs


if __name__ == "__main__":
    scenarios = [
        ("vowel, perfect", True, [], False, 0),
        ("no vowel, perfect", False, [], False, 0),
        ("vowel, 1 strike at first press", True, [(0, 0)], False, 1),
        ("vowel, 2 strikes (rows 0,1,2)", True, [(0, 0), (1, 0)], False, 2),
        ("no vowel, 3 strikes (rows 0,1,2,2)", False, [(0, 0), (1, 0), (2, 0)], False, 3),
        ("no vowel, 1 strike mid-sequence", False, [(1, 1)], False, 1),
        ("vowel, idle replay then perfect", True, [], True, 0),
    ]
    total_fail = 0
    for name, vowel, plan, idle, exp_strikes in scenarios:
        fails = 0
        stage_counts = set()
        for trial in range(40):
            try:
                res = run(vowel, plan, idle)
                errs = check(res, name, exp_strikes, idle)
            except Exception as e:      # noqa
                errs = ["exception: %r" % (e,)]
                res = None
            if errs:
                fails += 1
                if fails <= 2:
                    print("  FAIL[%s] trial %d: %s" % (name, trial, errs))
                    if res:
                        print("    seq=%s displays=%s" % (res["seq"], res["displays"]))
            elif res:
                stage_counts.add(len(res["seq"]))
        total_fail += fails
        print("%-40s trials=40 fails=%d stage counts seen=%s" % (name, fails, sorted(stage_counts)))
    print("TOTAL FAILS:", total_fail)
    sys.exit(1 if total_fail else 0)
