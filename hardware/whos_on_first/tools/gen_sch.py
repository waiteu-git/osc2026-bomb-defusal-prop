#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate hardware/whos_on_first/whos_on_first.kicad_sch (part 1: lib_symbols).

Reuses the lib_symbols block from keypad.kicad_sch verbatim (avoids retyping
the huge RPi_Pico:Pico symbol; also already contains Connector_Generic:Conn_01x04,
used for both J1 and, since 2026-09-27(2), J2 as well - see below), plus two
symbols extracted verbatim from KiCad's own installed libraries.

2026-09-27(2) TFT -> OLED change (hub decision, "再現の方針"): the display was
switched from the 8-pin SPI TFT to a 4-pin I2C OLED (SSD1315), so the
hand-extracted Conn_01x08 (TFT connector) symbol is REMOVED from this script -
J2 now reuses the same Connector_Generic:Conn_01x04 that J1 already pulls in
from keypad.kicad_sch's lib_symbols, so no new connector symbol needs to be
extracted at all.

Formula (confirmed against keypad.kicad_sch): absolute pin position =
(placement_x + local_x, placement_y - local_y), regardless of pin angle.
Every wire has exactly 2 points. All coords are multiples of 1.27mm.
"""
import re
import uuid

KEYPAD_PATH = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\keypad\keypad.kicad_sch"
OUT_PATH = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\whos_on_first\whos_on_first.kicad_sch"
PROJECT = "whos_on_first"

def u():
    return str(uuid.uuid4())

def fmt(n):
    s = f"{n:.4f}".rstrip("0").rstrip(".")
    if s == "-0":
        s = "0"
    return s

# ---------------------------------------------------------------------------
# 1. Extract lib_symbols block from keypad.kicad_sch (paren-matched). This
#    already includes RPi_Pico:Pico, Connector_Generic:Conn_01x04, Device:R,
#    Device:LED, Switch:SW_Push, power:GND/+5V/+3.3V - everything except the
#    two extras below.
# ---------------------------------------------------------------------------
with open(KEYPAD_PATH, "r", encoding="utf-8") as f:
    src = f.read()

start = src.index("\t(lib_symbols")
depth = 0
i = start
while True:
    c = src[i]
    if c == "(":
        depth += 1
    elif c == ")":
        depth -= 1
        if depth == 0:
            end = i + 1
            break
    i += 1
lib_symbols_block = src[start:end]

# ---------------------------------------------------------------------------
# 2. Two extra symbols, extracted verbatim from KiCad's installed libraries
#    (NOT hand-derived) so ERC never reports lib_symbol_mismatch and so KiCad
#    never silently re-syncs pin positions later and breaks our wiring.
# ---------------------------------------------------------------------------
def extract_symbol(lib_path, name, new_outer):
    """Copy a symbol verbatim from an installed KiCad .kicad_sym, prefixing
    only the OUTER symbol name with 'Library:' (sub-units stay unprefixed)."""
    with open(lib_path, "r", encoding="utf-8") as f:
        t = f.read()
    i0 = t.index('(symbol "%s"' % name)
    d = 0
    j = i0
    while True:
        c = t[j]
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                break
        j += 1
    blk = t[i0:j + 1].replace('(symbol "%s"' % name, '(symbol "%s"' % new_outer, 1)
    return blk if blk.endswith("\n") else blk + "\n"

SYM_DIR = "C:/Program Files/KiCad/10.0/share/kicad/symbols/"
CP_BLOCK = extract_symbol(SYM_DIR + "Device.kicad_sym", "C_Polarized", "Device:C_Polarized")
PWRFLAG_BLOCK = extract_symbol(SYM_DIR + "power.kicad_sym", "PWR_FLAG", "power:PWR_FLAG")

EXTRA = CP_BLOCK + PWRFLAG_BLOCK

# Insert the new symbols just before the closing "\t)\n" of lib_symbols block.
assert lib_symbols_block.endswith("\t)\n") or lib_symbols_block.endswith("\t)")
insert_at = lib_symbols_block.rstrip("\n")
assert insert_at.endswith("\t)")
lib_symbols_block_new = insert_at[:-2] + EXTRA + "\t)\n"

print("Original lib_symbols_block len:", len(lib_symbols_block))
print("New lib_symbols_block len:", len(lib_symbols_block_new))
with open("lib_symbols_check.txt", "w", encoding="utf-8") as f:
    f.write(lib_symbols_block_new)
