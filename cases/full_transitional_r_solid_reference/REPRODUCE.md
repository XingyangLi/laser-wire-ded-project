# Transitional-R, solid 0.9 mm Invar 36 wire on SS304: protected baseline

This folder is a backup of the Transitional-R result that the user wants to keep. Do not overwrite it.

## What is here
- `viz/`: the renders and numbers exactly as produced on Dukyong_PC on 2026-10-02 (finished about 4:10 PM CT).
  Copied unchanged from `C:\Users\dukyo\laser_wire_ded\viz\full_transitional_r`.
- `case_params.json`: every model parameter of the run.
- `case_settings_reconstructed/`: the full OpenFOAM case setup (mesh, physics, boundary and solver settings), without results.
- `source_code_used/`: the exact code bundle the PC used (`lwded_src.tgz`, 2026-10-02 11:34). Its
  `generate_case.py` is byte-identical to the current one (sha256 865184be...).

## Case data
The raw OpenFOAM result folders (`~/laser_wire_ded/full_transitional_r` in WSL) no longer exist. At 6:45 PM CT on
Oct 2, `~/laser_wire_ded` was replaced by an unrelated case, so the time directories and logs are gone.
So `case_settings_reconstructed/` and `case_params.json` were regenerated on 2026-10-03 with the same code and
the same command. The settings are identical to the original run, but the results come only from `viz/`.

## Exact command (from run_production.sh of 2026-10-02)
```bash
cd ~/laser_wire_ded
(cd solver && ./Allwmake)
python3 generate_case.py --laser-config transitional_r --case full_transitional_r --resolution medium --np 4
cd full_transitional_r && ./Allrun 4
~/vizenv/bin/python ../visualize.py --case . --out viz
```
`--np` only sets the MPI split; the PC run used 4 ranks (it ran alongside Normal and Lack-of-Fusion).

## Key settings (all are defaults of --laser-config transitional_r)
- 600 W total in 3 Gaussian beams of 200 W each (1/e^2 radius 0.5 mm, 25 deg from vertical, focus 0.5 mm above the plate on the wire axis).
  The beam arrangement is '-' (one spot in front of the wire, two behind; azimuths 0/120/-120 deg).
- Travel 5.8 mm/s, wire feed 29 mm/s, solid wire 0.9 mm, vertical (coaxial), 0.05 mm initial tip gap, feeding starts at 20 ms.
- Invar 36 wire on SS304, absorptivity 0.42 for both.
- Half domain (symmetry plane y = 0): x -3.5..+6.5 mm, y 0..3 mm, z -2..+2.5 mm. 100 um core mesh with 87 x 26 x 35 = 79,170 cells.
- End time 0.862 s.

## Result (viz/summary.json)
At the end, the bead is 1.40 mm high and 5.68 mm wide, with 0.45 mm penetration. Dilution is 0.26 geometric and 0.31 by composition.
The melt pool is 2.6 x 1.7 mm and peaks at about 2363 K. The last-20% averages are 1.43 mm high, 0.25 geometric and 0.34 compositional dilution.
