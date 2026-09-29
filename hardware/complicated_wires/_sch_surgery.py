# -*- coding: utf-8 -*-
"""complicated_wires.kicad_sch を「現状のまま」外科的に編集するためのツール。
ユーザーがKiCadのGUIで手動移動した位置を壊さないよう、生成スクリプトでの
全体再生成(regenerate)は使わず、このツールで対象ブロックだけを特定して
削除・追加する。座標は常に「ファイルの現在の内容」から再計算する。
"""
import re
import sys
import math
import uuid as uuidlib

sys.stdout.reconfigure(encoding="utf-8")

G = 1.27
DIRS = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}


def u():
    return str(uuidlib.uuid4())


def fmt(g):
    return "%.2f" % (g * G)


PIN_RE = re.compile(
    r'\(pin\s+(\w+)\s+(\w+)\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)\s*\(length\s+[-\d.]+\)\s*'
    r'\(name\s+"([^"]*)".*?\(number\s+"([^"]*)"', re.S)


def to_g(v):
    x = float(v) / G
    return int(round(x)) if abs(x - round(x)) < 1e-6 else x


def find_balanced(text, start):
    """text[start] == '(' を仮定し、対応する ')' の直後の位置を返す"""
    depth, j = 0, start
    while True:
        ch = text[j]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1


def iter_top_blocks(text, tag, indent="\t"):
    """indent+'(tag' で始まるブロックを順に (start, end, block_text) で返す"""
    key = indent + "(" + tag
    i = 0
    out = []
    while True:
        i = text.find(key, i)
        if i < 0:
            break
        end = find_balanced(text, i + len(indent))
        out.append((i, end, text[i:end]))
        i = end
    return out


def parse_lib_pin_tables(text):
    """(lib_symbols ... ) セクションから、埋め込み済みの各シンボル定義のピン表を作る。
    戻り値: {lib_id(=シンボル名): {pin_number: (lx, ly, angle, name, ptype)}}"""
    m = re.search(r"\t\(lib_symbols\n(.*?)\n\t\)\n", text, re.S)
    if not m:
        raise SystemExit("lib_symbols section not found")
    body = m.group(1)
    tables = {}
    for sm in re.finditer(r'\t\t\(symbol "([^"]+)"', body):
        name = sm.group(1)
        blk_start = sm.start()
        blk_end = find_balanced(body, sm.start() + 2)
        blk = body[blk_start:blk_end]
        tbl = {}
        for pm in PIN_RE.finditer(blk):
            tbl[pm.group(7)] = (to_g(pm.group(3)), to_g(pm.group(4)), int(pm.group(5)), pm.group(6), pm.group(1))
        tables[name] = tbl
    return tables


def parse_symbols(text):
    """(symbol (lib_id "...") (at x y rot) ... (property "Reference" "REF" ...) ...) を全部拾う。
    戻り値: list of dict(ref, lib_id, x, y, rot, start, end)"""
    out = []
    for start, end, blk in iter_top_blocks(text, "symbol"):
        lm = re.search(r'\(lib_id "([^"]+)"\)', blk)
        am = re.search(r'\(at ([\-\d.]+) ([\-\d.]+) (\d+)\)', blk)
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        mm = re.search(r'\(mirror (x|y)\)', blk)
        if not (lm and am and rm):
            continue
        out.append({
            "ref": rm.group(1), "lib_id": lm.group(1),
            "x": float(am.group(1)) / G, "y": float(am.group(2)) / G, "rot": int(am.group(3)),
            "mirror": mm.group(1) if mm else None,
            "start": start, "end": end, "text": blk,
        })
    return out


def symbol_pin_abs(sym, pin_tables):
    """symの各ピンの絶対座標(格子単位)を返す: {pin_number: (ax, ay)}。mirror x/yに対応。"""
    tbl = pin_tables.get(sym["lib_id"].split(":")[-1]) or pin_tables.get(sym["lib_id"])
    if tbl is None:
        # lib_idがそのままsymbol名の場合がある(埋め込みは "Connector_Generic:Conn_01x02" のような名前で保存)
        key = sym["lib_id"]
        tbl = pin_tables.get(key)
    if tbl is None:
        raise SystemExit("no pin table for lib_id=%s (ref=%s)" % (sym["lib_id"], sym["ref"]))
    out = {}
    rot = sym["rot"]
    th = math.radians(rot)
    c, s = int(round(math.cos(th))), int(round(math.sin(th)))
    mirror = sym.get("mirror")
    for num, (lx, ly, pa, pname, ptype) in tbl.items():
        if mirror == "y":
            lx = -lx
        elif mirror == "x":
            ly = -ly
        rx, ry = lx * c - ly * s, lx * s + ly * c
        ax, ay = sym["x"] + rx, sym["y"] - ry
        out[num] = (ax, ay)
    return out


def parse_wires(text):
    out = []
    for start, end, blk in iter_top_blocks(text, "wire"):
        m = re.search(r'\(pts\s*\(xy ([\-\d.]+) ([\-\d.]+)\)\s*\(xy ([\-\d.]+) ([\-\d.]+)\)', blk)
        if not m:
            continue
        p1 = (float(m.group(1)) / G, float(m.group(2)) / G)
        p2 = (float(m.group(3)) / G, float(m.group(4)) / G)
        out.append({"p1": p1, "p2": p2, "start": start, "end": end, "text": blk})
    return out


def parse_labels(text):
    out = []
    for start, end, blk in iter_top_blocks(text, "label"):
        nm = re.search(r'\(label "([^"]*)"', blk)
        am = re.search(r'\(at ([\-\d.]+) ([\-\d.]+)', blk)
        if not (nm and am):
            continue
        out.append({"name": nm.group(1), "x": float(am.group(1)) / G, "y": float(am.group(2)) / G,
                     "start": start, "end": end, "text": blk})
    return out


def parse_no_connects(text):
    out = []
    for start, end, blk in iter_top_blocks(text, "no_connect"):
        am = re.search(r'\(at ([\-\d.]+) ([\-\d.]+)\)', blk)
        if not am:
            continue
        out.append({"x": float(am.group(1)) / G, "y": float(am.group(2)) / G,
                     "start": start, "end": end, "text": blk})
    return out


def near(a, b, tol=0.05):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "complicated_wires.kicad_sch"
    text = open(path, encoding="utf-8").read()
    pin_tables = parse_lib_pin_tables(text)
    syms = parse_symbols(text)
    print("symbols:", len(syms), " lib pin tables:", len(pin_tables))
    refs = sorted((s["ref"] for s in syms), key=lambda r: (len(r), r))
    print(refs)
