# val3mm_fe_ni_v2: defocused 3 mm Fe+Ni check with the anti-sinking fix

Same as `val3mm_fe_ni_defocus` (600 W, 2.67 mm/s, WFS 18.2 mm/s metal basis, focus -1.5 mm, zR 1.2 mm,
A_sub 0.35, A_wire 0.25, alphaHit 0.25, strand-k 0.4, unmeltedK 0.3, liquidusUnmixedThreshold 0.85,
gap 80 um, tip on plate, dx 120/60 um, 3 mm track, end 1.125 s, 8 ranks) plus:

| option | value | why |
|---|---|---|
| `--rigid-substrate 100` (meltProperties `rigidSubstrate`) | Kmushy x100 where z < 0 and fl < 0.05 | in the defocus run the cold wire tip was pushed into the SOLID plate during the first 0.3 s (fl = 0 there; 0.75 mm3 of never-melted wire down to z = -0.51 mm by 0.2 s). The prescribed feed indents the plate through the pressure coupling because plate and wire had the same Darcy stiffness. |
| `--stub-floor` (components `stubFloorZ -6e-5`) | stubbing support >= top substrate cell centre | never-molten solid strands within one cell of the original plate surface are dragged with the substrate even when the plate under the tip is molten |
| `--feed-scale 1.0` | unchanged | the defocus run's metal inventory grew 7.18 mm3 in 1.125 s = 6.38 mm3/s vs 6.43 mm3/s fed (99%). The fed metal IS delivered; the low bead (0.85 mm) comes from the 3 mm track being shorter than the 3.7 mm pool (no steady bead yet), ~1 mm3 of wire metal pushed below the plate, and metal held ahead of the wire. A 1.8x feed would give a 4.3 mm2 steady bead vs ~2.4 mm2 measured in the X-ray. |

Ni: not changed. The unmelted Ni of the defocus run sat in the same below-plate strands (pushed into the
cold plate), so it should mostly disappear with the anti-sinking fix.
## Smoke test (PC, 2026-10-06 11:11-11:30 CT, same case with end 0.04 s, stopped at 0.03 s)

Wire material below the original plate surface (z < 0), `check_below_plate.py`:

| t [s] | val3mm_fe_ni_defocus (no fix) | val3mm_fe_ni_v2 (fix) |
|---|---|---|
| 0.01 | (not written) | 0.0002 mm3 |
| 0.02 | 0.019 mm3, cells with cW>0.3 down to z = -0.057 mm | 0.0006 mm3, no cell with cW>0.3 below z = 0 |
| 0.03 | (~0.045 mm3, interpolated) | 0.0011 mm3, none below z = 0 |
| 0.04 | 0.076 mm3, down to -0.171 mm | (smoke stopped) |

Metal inventory identical (121.018 mm3 at 0.02 s in both), so the feed is still fully delivered.
Speed unchanged (p_rgh GAMG still at its 10-cycle cap in the early steps as before; ~9-12 h wall per
sim-s on the PC at the start).
