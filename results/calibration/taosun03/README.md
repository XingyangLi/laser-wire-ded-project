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
| cal36 | 0.36 s | 8 | 1.76 / 1.15 mm | 1.15–1.76 mm, 8/9 pinned | open, 3.25 mm³, centre y = 1.04 mm | Tall trailing crest, lower leading side. Continued to 0.80 s. |
| cal35 | 0.45 s | 8 | 1.76 / 1.30 mm | 1.30–1.91 mm, 8/8 pinned | open, 3.18 mm³, centre y = 1.08 mm | Same crest height, line fully pinned above it. Continued to 1.00 s. |
| cal34 | 0.30 s | 7 | 1.45 / 1.15 mm | 1.15–1.61 mm, 6/11 pinned | open, 3.19 mm³, centre y = 1.06 mm | Best window. Continued to 0.70 s. |
| cal47 | 0.25 s | 7 | 1.45 / 1.15 mm | 1.15–1.61 mm, 12/13 pinned | open, 3.70 mm³, centre y = 0.98 mm | Milder plate window, same crests as cal34. Not continued. |
| cal51 | 0.28 s | 7 | 1.45 / 1.15 mm | 0.99–1.61 mm, 9/11 pinned | open, 3.31 mm³, centre y = 1.01 mm | 0.18 mm spots. Same crests. Not continued. |
| cal56 | 0.25 s | 7 | 1.45 / 1.15 mm | 1.15–1.61 mm, 9/11 pinned | open, 3.56 mm³, centre y = 0.97 mm | Force factor 2. Same crests. Not continued. |
| cal40 | 0.28 s | 7 | 1.45 / 1.30 mm | 1.15–1.61 mm, 9/11 pinned | open, 3.50 mm³, centre y = 0.99 mm | Sticky 20°/90° trail. Less asymmetry. Not continued. |
| cal38 | 0.28 s | 7 | 1.45 / 1.15 mm | 1.15–1.61 mm, 9/10 pinned | open, 3.43 mm³, centre y = 0.99 mm | 30°/100° window matches cal34. Not continued. |
| cal49 | 0.28 s | 7 | 1.45 / 1.15 mm | 1.15–1.61 mm, 13/16 pinned | open, 3.53 mm³, centre y = 1.01 mm | Tight 15°/50° window, no sector. Not continued. |
| cal32 | 0.30 s | 6 | 1.30 / 1.15 mm | 1.15–1.45 mm, 5/9 pinned | open, 3.07 mm³, centre y = 1.02 mm | Narrower window. Continued to 0.70 s. |
| cal48 | 0.28 s | 6 | 1.30 / 1.15 mm | 1.15–1.45 mm, 10/10 pinned | open, 3.07 mm³, centre y = 1.01 mm | Marangoni on cools the pool. Not continued. |
| cal39 | 0.28 s | 6 | 1.30 / 1.15 mm | 1.15–1.45 mm, 8/13 pinned | open, 3.17 mm³, centre y = 1.02 mm | Wide 90°/170° window. Foot pore, not a neck. Not continued. |
| cal37 | 0.25 s | 5 | 1.30 / 1.30 mm | 0.99–1.45 mm, 12/12 pinned | open, 3.39 mm³, centre y = 0.97 mm | Steep plate window did not hold. Not continued. |
| cal41 | 0.28 s | 4 | 1.30 / 1.30 mm | 1.30–1.45 mm, 1/7 pinned | open, 3.40 mm³, centre y = 0.97 mm | Wide 100°/165° window. Line mostly mobile. Not continued. |
| cal50 | 0.28 s | 4 | 1.15 / 1.15 mm | 1.15–1.45 mm, 6/9 pinned | open, 3.36 mm³, centre y = 0.99 mm | 60°/140° only within 45° of +x. Crests equal. Not continued. |
| cal57 | 0.28 s | 4 | 1.15 / 1.30 mm | 1.15–1.45 mm, 7/10 pinned | open, 3.28 mm³, centre y = 0.98 mm | Uniform 45°/110° window. Leading crest higher. Not continued. |
| cal45 | 0.28 s | 3 | 1.30 / 1.30 mm | 1.15–1.76 mm, 7/9 pinned | open, 3.88 mm³, centre y = 0.99 mm | Rear aim at z = 0.95 mm lifts the line above a flat crest. Not continued. |
| cal33 | 0.30 s | 2 | 0.84 / 1.30 mm | 1.30–1.45 mm, 3/9 pinned | open, 3.28 mm³, centre y = 0.98 mm | Wide window dropped the trailing crest. Not continued. |

cal36 and cal35 both reach a trailing crest of 1.76 mm, which is one cell layer on this mesh, and both pin the wire line on that crest. They get there by different levers, and neither has a closed cavity.

cal36 puts 700 W in the rear spot and 100 W in each front spot, at scan 3 mm/s and feed 20 mm/s, with the plain 30°/90° wire window. At 0.36 s the leading crest is only 1.15 mm, so the trail stands 0.61 mm above it. The wire line is pinned on 8 of 9 cells and its top is the crest. The cavity is open and centred at y = 1.04 mm. Four pinch-offs were single mobile cells; none was locked, and there is no closure. One of those cells sat near the center plane (y ≈ 0.07 mm) and then vanished. The molten plate line is entirely receding at a mean angle of 64°. Travel is 1.1 mm. It is continued to 0.80 s. Comparison: `cal36_vs_radiograph.png`.

cal35 is the taller-section screen: scan 2 mm/s, feed 18 mm/s, powers 120+120+560 W, same 30°/90° window. At 0.45 s the leading crest is 1.30 mm, so the trail stands 0.46 mm above it. All 8 wire cells are pinned, from 1.30 mm to 1.91 mm, so the top of the line is one cell above the crest. The cavity is open, centred at y = 1.08 mm. Eleven pinch-offs were recorded and none was locked. The plate line is entirely receding at a mean angle of 57°. Travel is only 0.9 mm against a pool about 2.7 mm long. It is continued to 1.00 s. Comparison: `cal35_vs_radiograph.png`.

Of the three trailing windows, 60°/140° (cal34) is the one that keeps the trailing crest highest. 45°/120° (cal32) keeps a smaller advantage, 0.15 mm, and the line is back on the flank: around 0.20 s its bottom had fallen to 0.23 mm. 75°/160° (cal33) loses the trail. The trailing crest there is 0.84 mm and the leading crest is 1.30 mm, and only 3 of 9 wire cells are pinned. Those cavities are open and centred near y = 1 mm. Pinch-offs were single mobile cells and none was locked. On every finished screen the molten plate line is entirely receding, including cal37's 150°/170° window (mean angle 47°).

cal45 aims the rear spot at z = 0.95 mm instead of 0.55 mm. At 0.28 s the centerline crests are equal at 1.30 mm, while the wire line sits at 1.15–1.76 mm, above that crest. The higher hit melts the flank and does not build the trailing bulb. It is not continued. Comparison: `cal45_vs_radiograph.png`.

cal47 lowers the plate window to 90°/140° with force factor 8. At 0.25 s the crests match cal34, 1.45 mm trailing and 1.15 mm leading, and 12 of 13 wire cells are pinned. The plate line is still receding (35 of 37 molten cells, mean angle 58°). One lack-of-fusion pore is locked, 0.23 mm, two cells, at (x, y, z) ≈ (0.65, 0.66, 0.23) mm. That is a pocket at the foot, not gas under the neck. The run is not continued; cal34 already carries this crest shape further. Comparison: `cal47_vs_radiograph.png`.

cal48 turns Marangoni back on, on the cal08 beams. At 0.28 s the trailing crest is 1.30 mm, the leading crest 1.15 mm, and the wire line is fully pinned at 1.15–1.45 mm. The hottest liquid on the centerline is 2584 K, cooler than the Marangoni-off screens. No pore is locked and there is no closure. It is not continued. Comparison: `cal48_vs_radiograph.png`.

cal39 is the wide trailing window, 90°/170°. At 0.28 s the trailing crest is 1.30 mm and the leading crest is 1.15 mm, with 5 of 13 wire cells receding. A lack-of-fusion pore is locked at the plate, 0.46 mm, 15 cells, centred near (0.60, 0.51, −0.05) mm. That is not gas under the neck. The wider window does not beat 60°/140°, and the run is not continued. Comparison: `cal39_vs_radiograph.png`.

cal51 (0.18 mm spots) and cal56 (force factor 2) both finish on the same crest pair as cal34, 1.45 mm trailing and 1.15 mm leading, with the wire line on the neck. The tighter spot does not steepen the foot: all 28 molten plate cells are receding and the mean angle is 50°. The weaker force leaves the same receding plate line, mean angle 58°. Neither has a locked pore at the end, and neither reaches the 1.76 mm crest of cal35 and cal36. They are not continued. Comparisons: `cal51_vs_radiograph.png`, `cal56_vs_radiograph.png`.

Across the trailing-window sweep the 60°/140° window (cal34) is the one that keeps a 1.45 mm trail and a 1.15 mm lead. A stickier 20°/90° window (cal40) holds the same trail height but the leading crest rises to 1.30 mm. Wider than 60°/140° does worse: 75°/160° drops the trail to 0.84 mm, 90°/170° leaves a plate pore, and 100°/165° (cal41) pins only 1 of 7 wire cells with equal 1.30 mm crests. cal40 and cal41 are not continued.

A 30°/100° window (cal38) and a tight 15°/50° window with no sector (cal49) reproduce cal34's 1.45 / 1.15 mm crests, with the line mostly pinned. Cutting the 60°/140° sector from 90° down to 45° (cal50) removes that trailing advantage: the crests are equal at 1.15 mm, and a 0.26 mm lack-of-fusion pore is locked on the leading side at z = 0.23 mm. A uniform 45°/110° window (cal57) makes the leading crest the higher one, 1.30 mm against 1.15 mm. None of these four is continued.

cal36, cal35, cal34 and cal32 are the continued runs. The screens that matched a lower score are not. Two further crosses use the free cores: cal64 keeps cal36's 700 W rear spot and widens that spot to 0.40 mm, and cal65 puts that 700 W together with the 60°/140° window and a 2 mm/s scan. The refined 60°/140° mesh is cal10 on TaoSun-01 and is not started here. cal63 is the best coarse screen, cal36, at `--wire-refine 2` (about 38 µm in x and y, z left coarse), one rank, to 0.25 s. Powers stay 100+100+700 W and there is no trailing sector.

cal59 keeps the 60°/140° window with cal35's taller section (scan 2 mm/s, feed 18 mm/s, 120+120+560 W) to 0.60 s. cal61 keeps that window with cal36's powers (100+100+700 W, scan 3 mm/s) to 0.40 s. cal62 is cal36's powers at scan 2 mm/s and feed 20 mm/s, to 0.60 s, to see whether the tall crest lengthens into a bulb. cal31 stays the refined cal08 mesh. Solvers stay at `nice -n 10` and the rank total stays at or under 32.
