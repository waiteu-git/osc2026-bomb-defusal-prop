# hardware/shared_lib  (proposal 2026-09-30)

Shared KiCad library for parts used by more than one module. Register per project (project tables, path relative to the module folder):

    (lib (name "OSC_Shared") (type "KiCad") (uri "${KIPRJMOD}/../shared_lib/OSC_Shared.kicad_sym") (options "") (descr "OSC2026 shared symbols"))
    (lib (name "OSC_Shared") (type "KiCad") (uri "${KIPRJMOD}/../shared_lib/OSC_Shared.pretty") (options "") (descr "OSC2026 shared footprints"))

| item | what |
|---|---|
| `OSC_Shared:Pico_TH40` (symbol) | Pico 2 with only the 40 header pins (RPi_Pico:Pico minus SWCLK/GND/SWDIO 41-43) |
| `OSC_Shared:RPi_Pico_TH_Headers` (footprint) | THT 40 pads only, module floats ~2.5mm (3D +2.5mm), courtyard = header strips, no castellation SMD pads / NPTH pegs |

Why: the Pico 2 H sits on 2.54mm header pins about 2.5mm above the board, so only the 40 through-hole pins touch the board.
`RPi_Pico:RPi_Pico_SMD_TH` treats castellation pads and the SWD ground as connected and has a full-size courtyard.
`apply_pico_th40.py <module.kicad_sch> [--write]` swaps a schematic over (dry run by default; aborts if the layout differs from the timer's).
The timer board still uses its own copy (`Timer_Local:*`); migrate it when convenient.

## Who uses it (2026-09-30, hub decision: unify only the boards being built)

| module | status |
|---|---|
| timer | keeps its own copy `Timer_Local:Pico_TH40` / `Timer_Local:RPi_Pico_TH_Headers`; **content must stay identical to OSC_Shared** (change both when either changes). Migrate later, low priority, only when the user says so |
| four_button | uses OSC_Shared from the start (Simon session) |
| button | **uses OSC_Shared** (schematic `OSC_Shared:Pico_TH40`, PCB `OSC_Shared:RPi_Pico_TH_Headers`; committed in af3041d) |
| complicated_wires | to migrate when its session resumes (has a PCB; the Pico is on the back, check the placement) |
| host, maze, memory, morse_code, password, whos_on_first, wire_sequence, wires, shared_param_widget | frozen: not migrated |

Pico 2 H (Akizuki 130982) has a JST SH 3-pin debug connector on the top side of the module: keep its height/position in mind for 3D and case checks.

## Pico 3D model correction (2026-10-01)
`KiCad-RP-Pico/RP-Pico Libraries/Pico.wrl` renders in KiCad 10.0.3 at 1/2.54 of the real size and off to one corner of the footprint when used with `scale 1 / offset 0` (also true of the upstream `RPi_Pico_SMD_TH`; reproduced with `kicad-cli pcb render`). 3D view only, no effect on fabrication.
Fix = `scale 2.54` (all axes) and model offset X/Y = (16.17, 39.27) mm; Z keeps the float height (2.5 for the floating TH footprint, 0 for a seated SMD one). The values come from rendering a single footprint and are stored in this library.
`python hardware/shared_lib/fix_pico_3d_model.py <file.kicad_pcb|file.kicad_mod> ...` applies it (idempotent, `--check` only reports, refuses to write while KiCad holds the file's lock). Run it on a board after regenerating it from a script that embeds an uncorrected footprint.
Status (2026-10-01): `OSC_Shared` (this library), `button.kicad_pcb` and `four_button.kicad_pcb` carry the corrected values. The timer board and `Timer_Local` were corrected the same day but restored to commit 28acde1 at the user's request, so they carry the old values again (re-apply with the script when asked). `complicated_wires.kicad_pcb` is not corrected yet (it uses the seated SMD footprint, so its Z stays 0).

Known quirks: the default Footprint property of `Pico_TH40` in `OSC_Shared.kicad_sym` still reads `Timer_Local:RPi_Pico_TH_Headers`; placed symbols override it with `OSC_Shared:RPi_Pico_TH_Headers`, and it is left unchanged so that the schematics' embedded symbol copies keep matching. Both boards need the KiCad-RP-Pico package (`${KICAD10_3RD_PARTY}`) only for the Pico 3D model; ERC/DRC do not depend on it.

## Migrating a schematic
1. Register OSC_Shared in the project's `sym-lib-table` and `fp-lib-table` (lines above).
2. `python hardware/shared_lib/apply_pico_th40.py <module.kicad_sch>` (dry run), then add `--write`.
3. KiCad: close and reopen the project; "Update PCB from Schematic" (with "Update footprints from library"); check ERC + `kicad-cli pcb drc --schematic-parity`.
A `lib_symbol_mismatch` ERC warning right after the swap is cosmetic: Tools > Update Symbols from Library.
