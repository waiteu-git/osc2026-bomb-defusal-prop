# placement table for build_timer_pcb.py (mm, board 80 x 80, origin top-left, y down)
# side 'F' = front, 'B' = back (mirrored, THT parts sit behind the front-side Picos/digits)
M = lambda side, dx=0, dy=0: (side, "match", dx, dy)
A = lambda side, x, y, rot=0: (side, "at", x, y, rot)
PLACE.update({
    # front: display, strike LEDs, the two Pico 2 (pin-header mounted)
    "DS1": M("F"), "DS2": M("F"), "DS3": M("F"), "DS4": M("F"),
    "D1": M("F"), "D2": M("F"), "D3": M("F"), "D4": M("F"),
    "U1": A("F", 40.0, 46.5, 270), "U3": A("F", 40.0, 68.4, 270),   # USB connector on the right
    # back: LED resistors (top band), module connectors and fuses
    "R1": M("B"), "R2": M("B"),
    "J1": M("B", 0, -1), "J2": M("B", 0, -1), "J3": M("B", 0, -1), "J4": M("B", 0, -1), "J5": M("B", 0, -1),
    "J8": M("B", 0, 0.5), "J7": M("B", 0, 0.5),
    "F1": M("B"), "F2": M("B"), "F3": M("B"), "F4": M("B"), "F5": M("B"),
    # back: TM1637 + decoupling
    "U2": M("B", 3.0, 0),
    "C3": A("B", 47.5, 71.0), "C1": A("B", 56.0, 71.0), "C2": A("B", 62.5, 71.0),
    # back: I2C pull-ups and the new battery input chain (J6 -> F6 -> Q1)
    "R3": A("B", 35.3, 50.5), "R4": A("B", 41.3, 50.5),
    "F6": A("B", 50.0, 50.5), "Q1": A("B", 58.5, 50.5), "R5": A("B", 63.2, 50.5), "J6": A("B", 72.75, 50.5),
})
SILK = [("+", 71.0, 54.6, 1.5), ("-", 74.5, 54.6, 1.5), ("5V IN ONLY", 72.5, 57.0, 1.0)]   # back side, mirrored
REFPOS = {"J7": (30.3, 50.5)}     # reference designators placed by hand (x, y); all others are auto-placed clear of pads
