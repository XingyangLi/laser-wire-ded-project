# taosun03 calibration (cal3x)

Oxygen stays off. These runs complement cal01–cal10 on TaoSun-01. They do not repeat cal10 (cal08 beams, trailing window 60°/140°, `--wire-refine 2`, 12 ranks).

## Machine limit

TaoSun-03 is an AMD Ryzen Threadripper PRO 5995WX: 64 physical cores, 128 hardware threads, 440 GB RAM. The WSL ext4 disk is the 1.5 TB volume on `Y:\Xingyang` (`/dev/sdd`, about 1.4 TB free). Case files stay on that ext4 filesystem, not on `C:`.

Half of the CPU is already taken by another simulation. This work uses at most **half of the physical cores**:

| limit | value |
| --- | --- |
| MPI ranks, all jobs added together | 32 |
| `wmake` / `make -j` (`WM_NCOMPPROCS`) | 32 |
| OpenMP threads per rank | 1 |
| solver priority | `nice -n 10` |

RAM and the GPU are not capped. Launch scripts take slots through `results/calibration/taosun03/lib.sh` and refuse a rank count above 32. Nothing was already running over that limit, so nothing was restarted.

OpenFOAM.com v2406 is installed (`openfoam2406-dev` 2406.260127-2). `laserWireDEDFoam` is built with `WM_NCOMPPROCS=32`. The solver is one translation unit, so that build is a single `g++`.

Smoke (`./scripts/run_wire_cavity.sh --smoke --np 2`, `nice -n 10`) passed. The 8 ms planted-wake case finished in about 1 s of solver clock time. At the end the wire line had 5 cells, all pinned, and the cavity report was open. `quantify_pores.py --expect-wire-smoke` passed.

## What cal01–cal09 already showed

cal08 is the best shape so far: flank-heated 160+160+420 W spots, scan 4 mm/s, feed 20 mm/s, plate window 110°/150°, wire window 30°/90°, Marangoni off, force factor 6. At 1.50 s the track holds the fed section (3.78 of 3.93 mm²), the trailing crest is 1.61 mm against 0.84 mm on the leading side, and the wire line is pinned at 0.99–1.61 mm. The deposit is a flat plateau rather than the radiograph's round bulb, and the wake cavity sits off the center plane on the 150 µm mesh. Raising the plate angle (cal04, cal05, cal07, cal08) did not move the apparent foot off about 50°; the heated footprint sets it. cal09 is the same beams at `--wire-refine 2` and was stopped at 0.25 s.

## Runs from this machine

Screens are coarse (150 µm), one rank each, all six together. A 10-rank trial on this mesh spent about 90% of each step in MPI (about 1.8 s/step, 1.5×10⁻⁵ simulated seconds per wall second). One rank does about 0.24 s/step (1.1×10⁻⁴ s/s), so 0.30 s of coarse time is about 45 minutes. Six ranks stay inside the 32-core cap. Long runs come after the screens, on one rank unless a refined-mesh timing says otherwise.

| tag | question | mesh | angles (plate, wire front, wire trail) | other change from cal08 | end |
| --- | --- | --- | --- | --- | --- |
| cal32 | trailing window, narrow | coarse | 110/150, 25/70, **45/120** | sector blend 30° | 0.30 s |
| cal33 | trailing window, wide | coarse | 110/150, 25/70, **75/160** | sector blend 30° | 0.30 s |
| cal34 | trailing window, cal10 angles, matched screen | coarse | 110/150, 25/70, **60/140** | same sector as cal10; not the refined cal10 run | 0.30 s |
| cal35 | taller bulb | coarse | 110/150, 30/90, none | scan 2 mm/s, feed 18 mm/s (section 7.1 mm²), powers 120+120+560 W | 0.45 s |
| cal36 | more power into the wire | coarse | 110/150, 30/90, none | scan 3 mm/s, feed 20 mm/s (section 5.2 mm²), powers 100+100+700 W | 0.36 s |
| cal37 | steeper plate foot | coarse | **150/170**, 30/90, none | force factor 10 | 0.25 s |
| cal31 | does the neck resolve | `--wire-refine 2` (57 014 cells, 38 µm in x,y) | cal08, no sector | one rank. A probe gave 7.4×10⁻⁶ s/s, so 0.40 s is about 15 h. Four ranks were no faster | 0.40 s |

60°/140° on the refined mesh is cal10 on TaoSun-01 and is not run here.

## Filling the 32 cores

One rank is faster than 10 on the coarse mesh, so the cores are filled with more runs rather than more ranks on one run. cal38–cal41 extend the trailing-angle sweep (20/90, 30/100, 90/170, 100/165). cal42–cal47 change the dome: more feed, rear-heavy power, a slower scan, a higher flank hit, a foot hit, and a milder plate window. cal48 turns Marangoni back on. cal49 pins the wire with a tight 15°/50° window. Each is one rank at `nice -n 10`.

cal31 stayed on one rank. A geometric 4-rank split of the refined mesh was no faster. Scotch was slower, and it cuts vertical columns: the solver counted 3715 column pieces against 2011 real columns, and it requires each column on one rank (`simple`, nz = 1). Late step times on the same 57k-cell mesh, cold start, `nice -n 10`:

| ranks | decomposition | seconds per step |
| --- | --- | --- |
| 1 | none | 0.44 |
| 4 | simple, nz = 1 | 0.41 |
| 4 | scotch | 0.51 |
| 8 | scotch | 1.76 |

None of those is a 1.5× gain, so cal31 was not restarted.

cal50–cal58 are further one-rank screens: a 45° trailing sector (not cal10's 90° refined run), 0.18 mm spots, a 0.02 mm wire gap, feed 32 mm/s, scan 2.5 mm/s, a steeper rear beam, a weaker Young force, a uniform 45°/110° wire window, and front spots cut to 80 W. With cal31–cal49 that is 28 ranks.

Continuations are chosen after the score, not by the flank-height watcher. That watcher was stopped so a weak screen does not keep a core. `score_screens.py` writes `ranking.csv`.

## Scores against the radiograph

The radiograph is a rounded dome about 1.5–2 mm tall, higher on the trailing side, with the three-phase line pinned on the wire at that neck and a gas cavity in the wake. The score is out of 10: trailing height (2), trailing crest above the leading crest (2), wire line pinned at the neck (3), wake behind the wire (2), a closure (1). A point for the wake still stands when the cavity is off the center plane; the note says so. Figures are `results/calibration/taosun03/<tag>_vs_radiograph.png`.

| tag | t | score | trail / lead | wire line | cavity | what it shows |
| --- | --- | --- | --- | --- | --- | --- |
| cal34 | 0.30 s | 7 | 1.45 / 1.15 mm | 1.15–1.61 mm, 6/11 pinned | open, 3.19 mm³, centre y = 1.06 mm | Best window. Continued to 0.70 s. |
| cal32 | 0.30 s | 6 | 1.30 / 1.15 mm | 1.15–1.45 mm, 5/9 pinned | open, 3.07 mm³, centre y = 1.02 mm | Narrower window, line back on the flank. Continued to 0.70 s. |
| cal37 | 0.25 s | 5 | 1.30 / 1.30 mm | 0.99–1.45 mm, 12/12 pinned | open, 3.39 mm³, centre y = 0.97 mm | Steep plate window did not hold. Not continued. |
| cal33 | 0.30 s | 2 | 0.84 / 1.30 mm | 1.30–1.45 mm, 3/9 pinned | open, 3.28 mm³, centre y = 0.98 mm | Wide window dropped the trailing crest. Not continued. |

Of the three trailing windows, 60°/140° (cal34) is the one that keeps the trailing crest highest. 45°/120° (cal32) keeps a smaller advantage, 0.15 mm, and the line is back on the flank: around 0.20 s its bottom had fallen to 0.23 mm. 75°/160° (cal33) loses the trail. The trailing crest there is 0.84 mm and the leading crest is 1.30 mm, and only 3 of 9 wire cells are pinned. All three cavities are open and centred near y = 1 mm, so the gas is beside the wire rather than in a centerline notch. Pinch-offs were single mobile cells (three on cal32, one on cal33, two on cal34) and none was locked at 0.30 s. There is no closure. On every finished screen the molten plate line is entirely receding, at a mean angle of about 47–62°, including cal37's 150°/170° window.

cal34 is continued to 0.70 s and cal32 to 0.70 s, one rank each. cal33 and cal37 are not. The refined 60°/140° mesh is cal10 on TaoSun-01 and is not started here.

cal37 uses the cal08 beams with a plate window of 150°/170° and force factor 10. At 0.25 s the centerline crests are equal. The wire line sits one cell above that crest and is fully pinned. Lack-of-fusion cells of about 0.15–0.26 mm flicker on and off; none is locked at the end. Travel is 1.0 mm, shorter than the pool. Comparison figures: `cal34_vs_radiograph.png` (best so far), `cal32_vs_radiograph.png`, `cal33_vs_radiograph.png`, `cal37_vs_radiograph.png`.

Two coarse crosses keep the 60°/140° window and change the lever that cal35 and cal36 are already running without that window. cal59 is scan 2 mm/s, feed 18 mm/s, powers 120+120+560 W, to 0.60 s. cal61 is scan 3 mm/s, feed 20 mm/s, powers 100+100+700 W, to 0.40 s. cal31 stays the refined cal08 mesh, still early in its 0.40 s. Solvers stay at `nice -n 10` and the rank total stays at or under 32.
