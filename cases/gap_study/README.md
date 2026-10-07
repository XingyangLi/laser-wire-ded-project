# Wire-substrate gap case study (gap_study_1mm, gap_study_2mm, gap_study_3mm)

**Question.** How does the initial vertical standoff between the wire tip and the plate (1, 2, 3 mm)
change the transfer mode at the start of the build: does the tip bridge into the pool, form a ball
that hangs / drips (droplet transfer), or arrive solid on a still-solid plate (stubbing)?
Earlier runs with the tip ~1-1.5 mm up and the focus near the plate *balled up* (molten ball hanging
on the tip, no bridge: `val3mm_fe_ni_focus03_balled`), which is why the baseline
`val3mm_fe_ni_v2` starts with the tip on the plate and a defocused beam.

## Setup (all three identical to `val3mm_fe_ni_v2` except the gap, the stubbing model and output)

| | value |
|---|---|
| process | 600 W (3 beams x 200 W, 25 deg, focus 1.5 mm *below* the plate on the wire axis, w0 0.5 mm, zR 1.2 mm -> 0.85 mm ray radius), 160 mm/min (2.67 mm/s), 3 mm track, end 1.1249 s |
| wire | Fe/Ni 5-strand ring (Fe,Ni,Fe,Ni,Fe x 0.3 mm, 80 um gaps, envelope 0.946 mm), vertical (coaxial), fed from t = 0 at **18.18 mm/s** along its axis (metal basis of WFS 10.1 mm/s on 0.9 mm) |
| substrate | Invar 36, rigid substrate x100, stub floor, A_sub 0.35 / A_wire 0.25 |
| `--wire-gap` | **1, 2, 3 mm** = vertical distance from the plate top (z = 0) to the lowest point of the flat-cut wire tip at t = 0 |
| `--stubbing` | ON (new rigid-wire stubbing model, see `docs/MODEL_NOTES.md`) |
| `--write-interval` | 0.01 s (v2: 0.02 s) |
| mesh | 120 um core / 60 um in the wire box; gas layer raised so that the tip + 1.5 mm of wire are inside |

| case | gas layer (uniform 120 um up to) | cells (checkMesh) | unmelted tip would touch the plate at | beam axis to wire axis at the tip (to wire surface, rel. intensity) |
|---|---|---|---|---|
| gap_study_1mm | 2.5 mm (1.6 mm) - same mesh as v2 | 169,650 | ~56 ms | 1.17 mm (0.68 w, 0.39) |
| gap_study_2mm | 3.5 mm (2.6 mm) | 222,300 | ~111 ms | 1.63 mm (1.18 w, 0.06) |
| gap_study_3mm | 4.5 mm (3.6 mm) | 269,100 | ~166 ms | 2.10 mm (1.68 w, 0.004) |
| baseline v2 | 2.5 mm (1.6 mm) | 169,650 | on the plate (gap 0) | 0.70 mm (at the plate) |

(The generator prints a slightly lower estimate, e.g. 165,822 for 1 mm; the numbers above are from
`checkMesh` after meshing. The wire tip was checked in the meshed fields: lowest wire cell centre at
1.05 / 2.07 / 3.06 mm, i.e. half a cell above the requested gap.)

Beam geometry: the wire axis *is* the axis of the coaxial 3-beam cone. The solver traces parallel
rays of radius 0.85 mm (the 1/e^2 radius where the defocused beam meets the plate) along each beam
direction, so each beam axis is (z + 1.5 mm) tan 25 deg from the wire axis at height z. A tip 3 mm up
is practically outside the beams (it is heated only once it has been fed down), a tip 1 mm up is in
the beam flank. The wire is fed continuously, so every gap closes unless the tip melts back faster
than 18 mm/s.

## What is measured (and where)

Solver output per case (`~/laser_wire_ded_stranded/gap_study_<n>mm/postProcessing/`):

* `wireTransfer/wireTransfer.dat` (new, every 20 time steps):
  `tipZ` (lowest solid never-molten wire cell = **wire tip height vs time**), `hangMinZ` (lowest
  metal above a gas gap = ball bottom), `gapMin` (gas gap wire/ball -> pool/plate), `bridged`,
  `nBridgedCols`, `bridgedArea` (wire connected to the substrate metal = **wire-pool contact**),
  `ballVolume`, `ballDiamEq`, `ballWidthX/Y`, `ballHeight`, `ballBottomZ/TopZ` (hanging liquid metal =
  **ball size**), and the stubbing record `stubbed`, `stallFactor`, `nContactCells`, `contactArea`,
  `nStubEvents`, `contactTime`, `firstStubTime`, `stalledLength`, `stalledVolume` (**stub events and
  stalled feed**), `fedLength`, `fedVolume`.
* `meltPool/meltPool.dat`: pool size, bead height / width / area at the probe behind the pool,
  **penetration**, dilution, metal volume.
* `meltPool/components.dat`: **unmelted Fe / Ni** (deposit and solid track).

`scripts/pc/compare_gap_study.py` (run automatically at the end of the queue, any time by hand)
turns these into `C:\Users\dukyo\laser_wire_ded\viz\gap_study_compare\`:
`gap_study_compare.png` (tip height, gap / bridging, ball volume and diameter, stall factor and
stalled feed, bead height/width, penetration, final centreline and cross-section profiles, baseline
v2 included) and `gap_study_table.md/.csv/summary.json` with: time the tip reaches 0.15 mm, **time to
first wire-pool contact**, first stub time, stub events, stub contact time, stalled feed (mm3 and
fraction of the feed), **max ball volume / diameter before contact**, max ball width / height,
**droplet transfer events** (hanging liquid volume falls by >40 % while not bridged), bridged
fraction, mean bead height / width and its scatter, **bead continuity** (fraction of late bead-probe
samples with h > 50 um), max penetration, metal added, unmelted Fe / Ni.

Pictures per case (same renders as v2): `C:\Users\dukyo\laser_wire_ded\viz\gap_study_<n>mm\`
(`build_long_section.png`, cross sections, `unmelted_timeseries.png`, `standard\` frames,
`track_profile.png/.csv`, `below_plate.txt`).

## How to run / check (Windows)

* **Gap_Study_Status.bat** (project folder): queue state, benchmark decision, each case's progress,
  ETA in CT and the latest `WireTransfer:` line.
* **Gap_Study_Start_Queue.bat**: (re)starts the queue hidden with keep-awake (safe to double-click
  again after a reboot: it continues every case from its latest time and never starts twice).
* **Open_in_ParaView.bat gap_study_2mm** (or double-click and type the case name).

The queue (`scripts/pc/gap_study_queue.sh`, installed as
`~/laser_wire_ded_stranded/gap_study_queue/gap_study_queue.sh`) waits until `val3mm_fe_ni_v2`
has finished *and* rendered (`ALL DONE`), runs a 2 x 5 min benchmark (1 x 8 ranks vs 3 x 5 ranks
concurrently on the same case) and keeps concurrent runs only if they give > 10 % more total
throughput; otherwise the three cases run one after the other on 8 ranks (renders overlap with the
next run). Then it writes the comparison.

Regenerate the setups: `python3 scripts/pc/gap_study_generate.py` (options from the v2
`case_params.json`, then `--wire-gap`, `--stubbing`, `--write-interval 0.01`).
`python3 scripts/pc/gap_study_generate.py --verify-baseline` regenerates v2 and diffs it against
`cases/val3mm_fe_ni_v2` (only `maxDeltaT` differs, from the newer `--capillary-dt-factor` option; it
is not the binding limit).

## Smoke test of the stubbing model

`scripts/pc/smoke_stubbing.sh` (coarse 16k-cell copy, 0.3 mm gap, 1 W so nothing melts, 35 ms,
serial): A = `--stubbing`, B = `--wire-transfer-stats` (diagnostics only), C = no stubbing dictionary.
The solid tip landed on the solid plate at t = 21.0 ms in all three. A: `Stubbing: solid wire on solid
support ... -> feed stalls`, stall factor 0.71 -> 4e-4 within 4 ms -> 7e-13, fed volume frozen at
0.130 mm3, stalled volume 0.0857 mm3 by 35 ms. B: same contact detected, feed kept going (fed volume
0.216 mm3; difference to A = A's stalled volume). B and C: identical meltPool / components output,
i.e. with stubbing off nothing changes. No errors in any run.

## Caveats

* The stubbing model treats the never-molten wire as a rigid rod: on solid-solid contact the whole
  feed stops (no buckling / elastic energy); the feed that could not enter is reported as stalled
  feed, it is *not* added later. Contact cells slide with the moving plate (no friction model).
* After a stall the helical strand pattern entering at the top is offset by the stalled length
  (the inlet pattern is a function of time); this is a small mismatch far above the tip.
* Ball / bridge / gap diagnostics are column based (vertical wire): "hanging" = metal above a gas gap
  in its vertical cell column within 1.5 mm of the wire axis; droplet events and the transfer-mode
  label are heuristics, check them against the pictures.
* The 3 mm track is shorter than the pool (~3.4 mm), so bead numbers are from the bead probe and the
  recording planes, not a steady-state bead.
