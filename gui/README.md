# Laser Wire DED — local run GUI

Simple tkinter control panel for setting laser / wire / mesh parameters and
launching OpenFOAM cases through WSL (same stack as the existing scripts).

## Open on your PC (Windows)

1. Double-click:

   `C:\Users\dukyo\laser_wire_ded_project\gui\launch_gui.bat`

   or in PowerShell:

   ```powershell
   cd C:\Users\dukyo\laser_wire_ded_project\gui
   .\launch_gui.ps1
   ```

2. Needs **Python 3.11** from python.org (already at
   `C:\Users\dukyo\AppData\Local\Programs\Python\Python311\`) and **WSL
   Ubuntu-24.04** with OpenFOAM v2406 (as used by the stranded runs).

## What the buttons do

| Button | Effect |
|--------|--------|
| **Validate (--print)** | Syncs the repo-root `*.py` into the WSL workdir and runs `generate_case.py --print` (no case written). |
| **Generate case** | Writes the OpenFOAM case under the WSL workdir (default `~/laser_wire_ded_stranded/<case>`). Does **not** start the solver. |
| **Mesh only** | Detached job: generate + mesh (`MESH_ONLY=1 ./Allrun`). Uses `launch_wsl_job.ps1` (keeps PC awake). |
| **Run solver** | Detached `mpirun … laserWireDEDFoam` (continues if the case already has processors). |
| **Generate+Mesh+Solve** | Full pipeline + visualize at the end. |
| **Status** | Status file, process list, sim time / ETA, log tail. |
| **Visualize** | Detached `visualize.py` or `visualize_multicomp.py` → `C:\Users\dukyo\laser_wire_ded_project\viz\<case>\`. |
| **Open viz folder** | Opens that folder in Explorer. |

Long jobs are started through `C:\Users\dukyo\laser_wire_ded_project\scripts\pc\launch_wsl_job.ps1`
(hidden PowerShell window) so WSL is not idle-killed.

## Presets

- **Transitional-R solid** — paper `transitional_r`, solid 0.9 mm wire.
- **Transitional-R 7-strand (contact)** — stranded 7, focus 0 mm, feed from t=0.
- **Fe+Ni 5-strand on Invar** — ring of 5×0.3 mm strands `Fe,Ni,Fe,Ni,Fe`, Invar substrate, contact feed.
- **Normal / LoF** — paper solid-wire conditions.
- **Custom single-beam** — vertical Gaussian, 2 kW / 10 mm/s / 25 mm/s WFS, 316L.

Blank numeric fields mean “let `generate_case.py` use its default / paper value”.

## Parameters exposed

Matches `generate_case.py`: laser config, power, scan speed, WFS, spot/focus/beam
geometry, wire type (solid/stranded), strands, layout, strand diameter/gap/lay,
strand materials (multi-comp), feed start/angle/gap, track length / end time,
resolution / dx / NP / dim / domain-y, materials, liquidus, wire-refine, max WFS,
and the two multi-comp behaviour flags.

## Safety

- Case names matching `full_transitional_r*` or `results_keep` are **blocked**.
- WSL workdir must not be `~/laser_wire_ded` or `~/laser_wire_ded_scan`.
- Default workdir is `~/laser_wire_ded_stranded` (existing solver build).
- The GUI never auto-starts a production run; solver buttons ask for confirmation.

## Files

```
gui/
  app.py              # main window
  launch_gui.bat      # Windows double-click launcher
  launch_gui.ps1
  README.md
  (generators are read from the repo root: ../generate_case.py etc.)
  jobs/               # generated bash scripts + .out logs
```

This GUI is part of the laser_wire_ded_project repo; see ../README.md.
