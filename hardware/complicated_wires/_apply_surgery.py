# -*- coding: utf-8 -*-
"""complicated_wires.kicad_sch(現物)に対する外科的パッチ。
ユーザーの手動配置(GND端子台の移動など)は一切変更せず、以下だけを行う:
  1) 旧NeoPixelチェーン(D1-D12, R13)を削除
  2) EXTRA1-4検知回路(R15-22)・接続状態インジケータLED(LED2-11, R23-32)を削除
  3) 上記に付随するワイヤー・ラベル・電源シンボル・no_connectを削除
  4) S1/S2/S5/S6のpin2(EXTRA_T配線)を削除し、no_connectに戻す
  5) U1のGP10-13,14-22,26(EXTRA/LED用スタブ)を削除し、no_connectに戻す
  6) E1-E4の作図注記(polyline+text)と、古い説明テキストを削除
  7) 新しい20個NeoPixelチェーン(D1-D20, R13)を、既存内容から十分離れた空き領域に追加
実行前に --dry-run で件数を確認できる。
"""
import json
import re
import sys

from _sch_surgery import (
    G, find_balanced, iter_top_blocks, parse_lib_pin_tables, parse_symbols,
    symbol_pin_abs, parse_wires, parse_labels, parse_no_connects, near, u, fmt,
)

PATH = "complicated_wires.kicad_sch"


def load():
    return open(PATH, encoding="utf-8").read()


def main(dry_run=True):
    text = load()
    pin_tables = parse_lib_pin_tables(text)
    syms = parse_symbols(text)
    wires = parse_wires(text)
    labels = parse_labels(text)
    nocs = parse_no_connects(text)
    by_ref = {s["ref"]: s for s in syms}

    removals = []   # list of (start, end, description)

    # ---- 1)+2) 削除対象シンボル ----
    TARGET = set(["D%d" % i for i in range(1, 13)] + ["R13"] + ["R%d" % i for i in range(15, 23)] +
                 ["LED%d" % i for i in range(2, 12)] + ["R%d" % i for i in range(23, 33)])
    target_syms = [s for s in syms if s["ref"] in TARGET]
    assert len(target_syms) == len(TARGET), (len(target_syms), len(TARGET))
    attach_points = []
    for s in target_syms:
        removals.append((s["start"], s["end"], "symbol %s" % s["ref"]))
        for pn, p in symbol_pin_abs(s, pin_tables).items():
            attach_points.append(p)

    def touches_target(pt):
        return any(near(pt, a) for a in attach_points)

    far_ends = []
    for w in wires:
        h1, h2 = touches_target(w["p1"]), touches_target(w["p2"])
        if h1 or h2:
            removals.append((w["start"], w["end"], "wire %s-%s" % (w["p1"], w["p2"])))
            if h1 and not h2:
                far_ends.append(w["p2"])
            elif h2 and not h1:
                far_ends.append(w["p1"])

    for lb in labels:
        if any(near((lb["x"], lb["y"]), f) for f in far_ends):
            removals.append((lb["start"], lb["end"], "label %s" % lb["name"]))

    # far_ends上の#PWR/#FLGシンボル(target自身の電源フラグ)も削除
    power_syms = [s for s in syms if s["ref"].startswith("#") and s["ref"] not in TARGET]
    for s in power_syms:
        if any(near((s["x"], s["y"]), f) for f in far_ends):
            removals.append((s["start"], s["end"], "power symbol %s" % s["ref"]))

    for nc in nocs:
        if touches_target((nc["x"], nc["y"])):
            removals.append((nc["start"], nc["end"], "no_connect at target pin"))

    # ---- 4) S1/S2/S5/S6 pin2 の EXTRA{i}_T 配線を削除 ----
    EXTRA_T_LABELS = {"EXTRA1_T", "EXTRA2_T", "EXTRA3_T", "EXTRA4_T"}
    extra_far = []
    for lb in labels:
        if lb["name"] in EXTRA_T_LABELS:
            removals.append((lb["start"], lb["end"], "label %s" % lb["name"]))
            extra_far.append((lb["x"], lb["y"]))
    for w in wires:
        if any(near(w["p1"], f) or near(w["p2"], f) for f in extra_far):
            removals.append((w["start"], w["end"], "wire for EXTRA_T stub"))

    # no_connectを追加する場所(S1.2/S2.2/S5.2/S6.2の現在位置)
    add_nc_at = []
    for ref in ("S1", "S2", "S5", "S6"):
        s = by_ref[ref]
        pins = symbol_pin_abs(s, pin_tables)
        add_nc_at.append(pins["2"])

    # ---- 5) U1のGP10-13,14-22,26スタブを削除 ----
    U1_STUB_LABELS = {"EXTRA1", "EXTRA2", "EXTRA3", "EXTRA4",
                       "WIRE1_LED", "WIRE2_LED", "WIRE3_LED", "WIRE4_LED", "WIRE5_LED", "WIRE6_LED",
                       "EXTRA1_LED", "EXTRA2_LED", "EXTRA3_LED", "EXTRA4_LED"}
    u1 = by_ref["U1"]
    u1_pins = symbol_pin_abs(u1, pin_tables)
    U1_STUB_PINS = ["14", "15", "16", "17", "19", "20", "21", "22", "24", "25", "26", "27", "29", "31"]
    u1_far = []
    for lb in labels:
        if lb["name"] in U1_STUB_LABELS:
            removals.append((lb["start"], lb["end"], "label %s (U1 stub)" % lb["name"]))
            u1_far.append((lb["x"], lb["y"]))
    for w in wires:
        if any(near(w["p1"], f) or near(w["p2"], f) for f in u1_far):
            removals.append((w["start"], w["end"], "wire for U1 stub"))
    for pn in U1_STUB_PINS:
        add_nc_at.append(u1_pins[pn])

    # ---- 6) E1-E4作図注記+古い説明文の削除 ----
    for start, end, blk in iter_top_blocks(text, "text"):
        m = re.search(r'\(text "([^"]*)"', blk)
        if not m:
            continue
        s = m.group(1)
        if re.fullmatch(r"E[1-4]", s) or "検知回路+専用LED" in s:
            removals.append((start, end, "text %r" % s))
    for start, end, blk in iter_top_blocks(text, "polyline"):
        am = re.search(r'\(xy ([\-\d.]+) ([\-\d.]+)\) \(xy ([\-\d.]+) ([\-\d.]+)\)', blk)
        if not am:
            continue
        x1 = float(am.group(1)) / G
        # E1-E4の縦線はx = TB_X+12+2*(6+i) = 28+12+2*(6..9) = 52,54,56,58 (格子単位)
        if 51.5 <= x1 <= 58.5:
            removals.append((start, end, "polyline x=%.1f (E-line)" % x1))

    # ---- 重複除去 & 適用 ----
    dedup = {}
    for s, e, d in removals:
        dedup.setdefault((s, e), d)
    removals = sorted(((s, e, d) for (s, e), d in dedup.items()), key=lambda r: r[0])
    total_removed_chars = sum(e - s for s, e, _ in removals)
    print("removal spans:", len(removals), " chars:", total_removed_chars)
    kinds = {}
    for _, _, d in removals:
        kind = d.split()[0]
        kinds[kind] = kinds.get(kind, 0) + 1
    print("by kind:", kinds)
    print("no_connect to add:", len(add_nc_at))

    if dry_run:
        return

    # 重なりチェック(隣接/包含があればassert)
    for i in range(len(removals) - 1):
        assert removals[i][1] <= removals[i + 1][0], ("overlap", removals[i], removals[i + 1])

    new_text = text
    for start, end, _ in sorted(removals, key=lambda r: -r[0]):
        new_text = new_text[:start] + new_text[end:]

    # no_connectを追加(信号側末尾、最後のno_connectブロックの直後に挿入)
    nc_blocks = []
    for p in add_nc_at:
        nc_blocks.append("\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid \"%s\")\n\t)" % (fmt(p[0]), fmt(p[1]), u()))
    # 挿入位置: 現存する最後の no_connect ブロックの直後(型ごとにまとまっている前提、_sch_surgery.iter_top_blocksで再確認)
    remaining_nocs = parse_no_connects(new_text)
    insert_at = remaining_nocs[-1]["end"] if remaining_nocs else new_text.find("\t(lib_symbols")
    new_text = new_text[:insert_at] + "\n" + "\n".join(nc_blocks) + new_text[insert_at:]

    # 新20個NeoPixelチェーンを追加
    block = json.load(open("_new_neopixel_block.json", encoding="utf-8"))
    for kind, key in [("wires", "wire"), ("labels", "label"), ("nocs", "no_connect"), ("syms", "symbol")]:
        existing = {"wire": parse_wires, "label": parse_labels, "no_connect": parse_no_connects, "symbol": parse_symbols}[key](new_text)
        insert_at = existing[-1]["end"] if existing else new_text.find("\t(lib_symbols")
        new_text = new_text[:insert_at] + "\n" + "\n".join(block[kind]) + new_text[insert_at:]

    open(PATH, "w", encoding="utf-8").write(new_text)
    print("wrote", PATH, "new size", len(new_text))


if __name__ == "__main__":
    main(dry_run=("--apply" not in sys.argv))
