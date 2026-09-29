# Memory module bring-up script - OFF-DEVICE test (runs on a PC, CPython 3).
# 目的: memory_bringup_test.py を実機なしで検査する。偽のmachine.Pin/timeでCLK・DIOの波形を記録し、
#       TM1637の受信側をソフトで模擬して次を確認する:
#         - START/STOPの形、ビット順(LSBファースト)、コマンド列 [0x44] -> [0xC0|g, data] -> [0x88|輝度]
#         - 9番目のクロックでPico側がDIOを開放(入力)しており、8番目の立ち下がりから解放までの間に衝突(Pico=High/TM1637=Low)がない
#         - ACK成功/失敗の両方でack_ok/ack_ngが正しく数えられる
#         - ACKを返さない(TM1637なし)場合に通信テストが失敗を表示する
#       `--mutants` を付けると、スクリプトを意図的に壊した版(ビット順反転・コマンド違い・ACK開放の欠落や遅れ等)を
#       作って、このテストが壊れ方を検出できるかを確認する(検出できなければ試験の目が粗いということ)。
# 実機でしか分からないこと: TM1637のACK実際のタイミング余裕、5V/3.3Vでの動作、明るさ・チラつき。
#
# 使い方:  python memory_bringup_offdevice_test.py            (本体の検査)
#          python memory_bringup_offdevice_test.py --mutants  (変異テスト)

import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "memory_bringup_test.py")
MARKER = 'print("=== Memory module bring-up test start'


class Bus:
    """CLK/DIOの2線バスと、TM1637受信側の模擬。時間は仮想クロック(us)。"""

    def __init__(self, slave_acks=True):
        self.t = 0
        self.slave_acks = slave_acks
        self.clk = 1
        self.pico_dio_out = 1          # Pico側のDIO出力ラッチ
        self.pico_dio_mode = "OUT"     # "OUT" / "IN"(+PULL_UP)
        self.slave_low = False         # TM1637がDIOをLowに引いているか(ACK中)
        self.state = "IDLE"
        self.bitcount = 0
        self.cur = 0
        self.frame = None
        self.frames = []               # 各START〜STOPのバイト列
        self.ack_slots = 0             # ACKスロット(9クロック目)の回数
        self.pico_released_in_ack = 0  # そのうちPicoがDIOを開放していた回数
        self.contention_us = 0         # ACK中にPicoがHighを駆動し続けた累積時間(衝突の継続時間)
        self.contention_max_us = 0     #   そのうち1回の最大
        self._cont_start = None
        self.min_clk_us = 10**9
        self._last_clk_edge = None
        self.errors = []
        self._prev_line = 1

    # DIOの実際のレベル(ワイヤードAND: Pico出力・TM1637のACK・プルアップ)
    def dio_line(self):
        pico = self.pico_dio_out if self.pico_dio_mode in ("OUT", "OPEN_DRAIN") else 1
        if self.pico_dio_mode == "OPEN_DRAIN":
            pico = 1 if self.pico_dio_out else 0
        return 0 if (self.slave_low or pico == 0) else 1

    # ---- Pico側からの操作 ----
    def set_clk(self, v):
        if v == self.clk:
            return
        old_line = self.dio_line()
        if self._last_clk_edge is not None:
            self.min_clk_us = min(self.min_clk_us, self.t - self._last_clk_edge)
        self._last_clk_edge = self.t
        self.clk = v
        self._on_clk_edge(v)
        self._prev_line = self.dio_line()

    def _end_contention(self):
        if self._cont_start is not None:
            d = self.t - self._cont_start
            self.contention_us += d
            self.contention_max_us = max(self.contention_max_us, d)
            self._cont_start = None

    def set_dio(self, v):
        before = self.dio_line()
        self.pico_dio_out = v
        if v == 0:
            self._end_contention()
        self._after_dio_change(before)

    def set_dio_mode(self, mode):
        before = self.dio_line()
        self.pico_dio_mode = mode
        if mode == "IN":
            self._end_contention()
        self._after_dio_change(before)

    def _after_dio_change(self, before):
        after = self.dio_line()
        if after != before and self.clk == 1:       # CLK=Highの間のDIO変化 = START/STOP
            if before == 1 and after == 0:
                self.state, self.bitcount, self.cur, self.frame = "RX", 0, 0, []
            elif before == 0 and after == 1 and self.state in ("RX", "ACK"):
                # STOP条件は「CLK↑(DIO=Low)→DIO↑」なので、直前のバイト完了後に部分ビットが最大1個(Low)入るのは正常。
                # 2ビット以上、または1ビット目がHighなら、バイトの途中でSTOPが来た(異常)。
                if self.bitcount >= 2 or (self.bitcount == 1 and (self.cur & 1)):
                    self.errors.append("STOP in the middle of a byte (bits=%d)" % self.bitcount)
                self.frames.append(self.frame)
                self.state, self.frame = "IDLE", None
        elif after != before and self.clk == 0 and self.state == "ACK" and self.pico_dio_mode != "IN":
            pass

    def _on_clk_edge(self, v):
        if self.state not in ("RX", "ACK"):
            return
        if v == 1:                                  # 立ち上がり
            if self.state == "RX":
                bit = self.dio_line()
                self.cur |= bit << self.bitcount    # LSBファースト
                self.bitcount += 1
            else:                                   # 9番目のクロックのHigh区間 = Picoが読む
                self.ack_slots += 1
                if self.pico_dio_mode == "IN":
                    self.pico_released_in_ack += 1
        else:                                       # 立ち下がり
            if self.state == "RX" and self.bitcount == 8:
                self.state = "ACK"                  # 8番目の立ち下がり: TM1637がACKを出す
                if self.slave_acks:
                    self.slave_low = True
                    if self.pico_dio_mode == "OUT" and self.pico_dio_out == 1:   # push-pullでHigh駆動中のみ衝突(オープンドレインのHighは解放)
                        self._cont_start = self.t   # Pico=High駆動のままACKが来た: 解放されるまでの時間を測る
            elif self.state == "ACK":               # 9番目の立ち下がり: ACK解除、バイト完了
                self._end_contention()
                self.slave_low = False
                self.frame.append(self.cur)
                self.state, self.bitcount, self.cur = "RX", 0, 0


def load_script(bus, source=None):
    """偽のmachine/timeを差し込み、スクリプトの「定義部分」だけをexecして名前空間を返す。"""
    class Pin:
        OUT, IN, PULL_UP, OPEN_DRAIN = "OUT", "IN", "PULL_UP", "OPEN_DRAIN"

        def __init__(self, n, mode=None, pull=None):
            self.n, self.mode = n, mode
            if n == 3:
                bus.set_dio_mode(mode if mode in ("OUT", "IN", "OPEN_DRAIN") else "OUT")
            self.v = 1

        def init(self, mode=None, pull=None):
            self.mode = mode
            if self.n == 3:
                bus.set_dio_mode(mode)

        def value(self, v=None):
            if self.n == 2:
                if v is None:
                    return bus.clk
                bus.set_clk(v)
                return None
            if self.n == 3:
                if v is None:
                    return bus.dio_line()
                bus.set_dio(v)
                return None
            if v is None:
                return 1
            self.v = v
            return None

    machine = types.ModuleType("machine")
    machine.Pin = Pin
    tm = types.ModuleType("time")
    tm.sleep_us = lambda u: setattr(bus, "t", bus.t + u)
    tm.sleep = lambda s: setattr(bus, "t", bus.t + int(s * 1e6))
    sys.modules["machine"], sys.modules["time"] = machine, tm
    src = source if source is not None else open(SCRIPT, encoding="utf-8").read()
    head = src[: src.index(MARKER)]
    ns = {"__name__": "memory_bringup_definitions"}
    exec(compile(head, "memory_bringup_test.py", "exec"), ns)
    return ns


def run_checks(source=None, verbose=True):
    """戻り値: 失敗した検査項目のリスト(空なら合格)。"""
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)
        if verbose:
            print(("  PASS  " if cond else "  FAIL  ") + msg)

    # ---- シナリオ1: TM1637あり(ACKを返す) ----
    bus = Bus(slave_acks=True)
    ns = load_script(bus, source)
    ns["set_brightness"](7)
    bus.frames.clear()
    for g in range(6):
        ns["tm1637_write_grid"](g, 0xA0 | g)
    exp = []
    for g in range(6):
        exp += [[0x44], [0xC0 | g, 0xA0 | g], [0x88 | 7]]
    check(bus.frames == exp, "command sequence: [0x44] -> [0xC0|g, data] -> [0x88|brightness] for all 6 grids (LSB-first, START/STOP framing)")
    check(not bus.errors, "no protocol errors (STOP inside a byte etc.): %s" % bus.errors[:1])
    nbytes = sum(len(f) for f in exp)
    check(ns["ack_ok"] == nbytes + 1 and ns["ack_ng"] == 0,
          "ACK counted once per byte: ack_ok=%d (expected %d, incl. the initial set_brightness), ack_ng=%d" % (ns["ack_ok"], nbytes + 1, ns["ack_ng"]))
    check(bus.ack_slots == bus.pico_released_in_ack and bus.ack_slots > 0,
          "Pico releases DIO (input) during every ACK slot: %d/%d" % (bus.pico_released_in_ack, bus.ack_slots))
    check(bus.contention_max_us <= 2, "Pico releases DIO within 2 us of the ACK edge (longest overlap of Pico=High / TM1637=Low: %d us)" % bus.contention_max_us)
    check(bus.min_clk_us >= 2, "CLK edges are at least 2 us apart (min %d us)" % bus.min_clk_us)
    check(bus.pico_dio_mode in ("OUT", "OPEN_DRAIN") and bus.state == "IDLE", "DIO is returned to its drive mode and the bus is idle after the last STOP (mode=%s, state=%s)" % (bus.pico_dio_mode, bus.state))

    # brightness command encodes the level
    bus.frames.clear()
    ns["set_brightness"](2)
    check(bus.frames == [[0x88 | 2]], "set_brightness(2) sends 0x8A")

    # digit glyph table sanity (bit0=A ... bit6=G, bit7=DP)
    d = ns["DIGIT"]
    seg = lambda s: sum(1 << "ABCDEFG".index(c) for c in s)
    ok_glyph = (d[1] == seg("BC") and d[2] == seg("ABDEG") and d[3] == seg("ABCDG") and d[4] == seg("BCFG")
                and d[8] == seg("ABCDEFG") and d[0] == seg("ABCDEF"))
    check(ok_glyph, "DIGIT[] glyphs for 0,1,2,3,4,8 match the segment letters (bit0=A .. bit6=G)")

    # ---- シナリオ2: TM1637なし(ACKなし) ----
    bus2 = Bus(slave_acks=False)
    ns2 = load_script(bus2, source)
    for g in range(6):
        ns2["tm1637_write_grid"](g, 0x00)
    check(ns2["ack_ok"] == 0 and ns2["ack_ng"] > 0, "no TM1637 -> every byte is counted as NG: ack_ok=%d ack_ng=%d" % (ns2["ack_ok"], ns2["ack_ng"]))
    check(bus2.contention_us == 0, "no contention when nobody acknowledges")
    return fails


def make_mutants(src):
    ms = []

    def add(name, old, new, count=1):
        assert src.count(old) >= 1, (name, old)
        ms.append((name, src.replace(old, new, count)))

    add("bit order MSB-first", "DIO.value((b >> i) & 1)", "DIO.value((b >> (7 - i)) & 1)")
    add("data command 0x44 -> 0x40", "_write_byte(0x44)", "_write_byte(0x40)")
    add("address command off by one", "_write_byte(0xC0 | grid_index)", "_write_byte(0xC0 | (grid_index + 1))")
    add("brightness command loses the display-ON bit", "_write_byte(0x88 | level)", "_write_byte(0x80 | level)")
    add("DIO never released for ACK", "    DIO.init(Pin.IN, Pin.PULL_UP)", "    pass")
    add("DIO released too late (contention)", "    DIO.init(Pin.IN, Pin.PULL_UP)       # Pico側はDIOを解放", "    time.sleep_us(6)\n    DIO.init(Pin.IN, Pin.PULL_UP)       # Pico側はDIOを解放")
    add("DIO not returned to output", "    DIO.init(PIN_DRIVE)\n", "    pass\n")
    add("ACK inverted (counts NG as OK)", "    if DIO.value() == 0:\n        ack_ok += 1", "    if DIO.value() == 1:\n        ack_ok += 1")
    add("STOP condition missing final DIO rise", "    time.sleep_us(2)\n    DIO.value(1)\n\n\ndef _write_byte", "    time.sleep_us(2)\n\n\ndef _write_byte")
    add("ACK counted twice per byte", "        ack_ok += 1", "        ack_ok += 2")
    return ms


def main():
    if not os.path.exists(SCRIPT):
        print("script not found:", SCRIPT)
        return 2
    src = open(SCRIPT, encoding="utf-8").read()
    if "--mutants" not in sys.argv:
        print("== off-device checks on memory_bringup_test.py (OPEN_DRAIN = False: push-pull, as designed) ==")
        fails = run_checks(src)
        print("\n== same checks with OPEN_DRAIN = True (diagnostic option; assumes external pull-ups on CLK/DIO) ==")
        assert "OPEN_DRAIN = False" in src
        fails_od = run_checks(src.replace("OPEN_DRAIN = False", "OPEN_DRAIN = True", 1))
        n = len(fails) + len(fails_od)
        print("\nRESULT:", "ALL PASS (both drive modes)" if n == 0 else "%d FAILED" % n)
        return 0 if n == 0 else 1
    print("== baseline ==")
    base = run_checks(src, verbose=False)
    print("baseline failures:", len(base), base)
    if base:
        return 1
    print("\n== mutants (each must be detected = at least one check FAILs, or the load itself breaks) ==")
    undetected = []
    for name, m in make_mutants(src):
        try:
            fails = run_checks(m, verbose=False)
        except Exception as e:       # 壊れ方が例外として出ても「検出された」とみなす
            fails = ["exception: %s" % type(e).__name__]
        status = "DETECTED" if fails else "** UNDETECTED **"
        print("  %-48s %s  %s" % (name, status, (fails[0][:70] if fails else "")))
        if not fails:
            undetected.append(name)
    print("\nRESULT: %d/%d mutants detected" % (len(make_mutants(src)) - len(undetected), len(make_mutants(src))))
    return 0 if not undetected else 1


if __name__ == "__main__":
    sys.exit(main())
