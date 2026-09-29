import layout80 as L
COLS, ROWS = 81, 41   # 1 col = 1 mm, 1 row = 2 mm
cv = [[" "]*COLS for _ in range(ROWS)]
def put(x, y, s):
    r = int(round(y/2.0)); c = int(round(x))
    r = max(0, min(ROWS-1, r))
    for i, ch in enumerate(s):
        if 0 <= c+i < COLS: cv[r][c+i] = ch
def rect(x0, y0, x1, y1, h="-", v="|", corner="+"):
    c0, c1 = int(round(x0)), int(round(x1)); r0, r1 = int(round(y0/2)), int(round(y1/2))
    for c in range(c0, c1+1):
        cv[r0][c] = h; cv[r1][c] = h
    for r in range(r0, r1+1):
        cv[r][c0] = v; cv[r][c1] = v
    for (r, c) in ((r0,c0),(r0,c1),(r1,c0),(r1,c1)): cv[r][c] = corner
def fill(x0, y0, x1, y1, ch):
    for r in range(int(round(y0/2)), int(round(y1/2))+1):
        for c in range(int(round(x0)), int(round(x1))+1):
            cv[r][c] = ch

# corner keep-outs (15x15), hatched
for k, (x0,y0,x1,y1) in L.KEEPS.items():
    fill(x0, y0, x1, y1, "/")
    put(x0+ (x1-x0)/2-4, (y0+y1)/2 - 0, "hole")
# panel border
rect(0, 0, 80, 80, "=", "|", "#")
# OLED PCB (behind panel) dotted
rect(*L.E["OLED_PCB(behind)"], h=".", v=":", corner=".")
# OLED window (only shows the display word - button words are fixed printed caps now)
w = L.E["OLED_window"]; rect(*w, h="-", v="|", corner="+")
put(31, 25.5, "DISPLAY WORD")
# caps (word printed on the cap itself, not on-screen)
for n, x, r in L.names:
    yc = L.row_centres[r]
    label = "[  %s  ]" % n
    put(x-5, yc, label)
# LEDs
for i, x in enumerate((32.0, 40.0, 48.0), start=1):
    put(x-1, 9.0, "(%d)" % i)
put(73, 20.0, "(G)")
# JST
put(34, 74.0, "[ JST XH 4P ]")
# title labels (placed below the window - the OLED PCB is small, so unlike the
# old TFT layout there is no room above the window; below it there is ~11mm)
put(28, 36.0, "OLED PCB 27x24.7 (rear)")
lines = ["".join(row).rstrip() for row in cv]
print("\n".join(lines))

with open("ascii80.txt", "w", encoding="utf-8") as f:
    f.write(chr(10).join(lines) + chr(10))
