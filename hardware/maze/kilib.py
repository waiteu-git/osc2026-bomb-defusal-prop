"""Helpers to pull symbol definitions out of KiCad .kicad_sym / .kicad_sch text and read their pins."""
import re

KICAD_SYM_DIR = r"C:\Program Files\KiCad\10.0\share\kicad\symbols"
KEYPAD_SCH = r"C:\Users\ysou5\OneDrive - 東京理科大学\ドキュメント\osc\hardware\keypad\keypad.kicad_sch"


def balanced(text, start):
    """return end index (exclusive) of the s-expression that starts at text[start] == '('."""
    depth = 0
    i = start
    in_str = False
    n = len(text)
    while i < n:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i + 1
        i += 1
    raise ValueError("unbalanced")


def find_symbol_block(text, name, top_level_only=True):
    pat = re.compile(r'\(symbol "' + re.escape(name) + r'"')
    m = pat.search(text)
    if not m:
        raise KeyError(name)
    return text[m.start():balanced(text, m.start())]


def from_std_lib(lib, name):
    """symbol block from KiCad standard library, renamed 'Lib:Name' for embedding in lib_symbols."""
    path = KICAD_SYM_DIR + "\\" + lib + ".kicad_sym"
    text = open(path, encoding="utf-8").read()
    blk = find_symbol_block(text, name)
    assert "(extends" not in blk[:400], name + " uses extends"
    return blk.replace('(symbol "' + name + '"', '(symbol "' + lib + ":" + name + '"', 1)


def from_keypad(libid):
    text = open(KEYPAD_SCH, encoding="utf-8").read()
    a = text.index("(lib_symbols")
    end = balanced(text, a)
    return find_symbol_block(text[a:end], libid)


def read_pins(block):
    """pins of a (fully qualified or bare) symbol block: list of dict(number,name,x,y,angle,length,etype)."""
    pins = []
    for m in re.finditer(r"\(pin (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s*\(length ([-\d.]+)\)", block):
        etype, style, x, y, a, ln = m.groups()
        end = balanced(block, m.start())
        body = block[m.start():end]
        nm = re.search(r'\(name "([^"]*)"', body).group(1)
        num = re.search(r'\(number "([^"]*)"', body).group(1)
        hide = "(hide yes)" in body
        pins.append(dict(number=num, name=nm, x=float(x), y=float(y), angle=float(a), length=float(ln),
                         etype=etype, style=style, hidden=hide))
    return pins


if __name__ == "__main__":
    import sys
    for lib, nm in [("Connector_Generic", "Conn_01x02"), ("Device", "C"), ("Device", "C_Polarized"),
                    ("LED", "WS2812B"), ("power", "PWR_FLAG")]:
        b = from_std_lib(lib, nm)
        print(lib, nm, len(b))
        for p in read_pins(b):
            print("   ", p)
    for nm in ["RPi_Pico:Pico", "Device:R", "Device:LED", "Switch:SW_Push", "Connector_Generic:Conn_01x04",
               "power:GND", "power:+5V", "power:+3.3V"]:
        b = from_keypad(nm)
        print(nm, len(b))
        for p in read_pins(b):
            print("   ", p)
