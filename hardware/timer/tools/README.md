# hardware/timer/tools

**One-shot tools from 2026-09-30. The PCB is now edited by hand in KiCad; do not run `build_timer_pcb.py` again**
(it rebuilds every footprint and would erase routing and manual edits). Kept for provenance.

| file | purpose |
|---|---|
| `build_timer_pcb.py` + `timer_placement.py` | built `timer.kicad_pcb` from the real library footprints (pcbnew API, netlist from `kicad-cli sch export netlist`) |
| `make_pico_variant.py` | generates `Timer_Local.pretty/RPi_Pico_TH_Headers.kicad_mod` from the community `RPi_Pico_SMD_TH` |
| `make_local_footprints.py` | generates the MF-RX030 / MF-R185 / MountingHole_2.6mm footprints |
| `patch_battery_fpfields.py`, `patch_pico_fp.py` | protected patches of `timer.kicad_sch` (Footprint fields, battery input J6/F6/Q1/R5, Pico footprint) - already applied |
| `retired/gen_timer_pcb_2pico_retired.py` | the previous script-generated PCB (placeholder footprints) |

`timer.kicad_sch` is hand-edited: change it only by targeted patch, never regenerate.
