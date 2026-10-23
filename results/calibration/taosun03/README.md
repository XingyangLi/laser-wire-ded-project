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

The radiograph is a rounded dome about 1.5–2 mm tall, higher on the trailing side, with a small notch where the melt pins on the wire. The gas in that pool is small closed bubbles, about 0.05–0.3 mm, not a large open wake. A gas sheet under the trailing bead is a non-wetted film: the plate angle sits near 50–60° and the molten plate line is receding, which is the same artifact TaoSun-01 saw on cal11. The score is out of 10:

| points | check |
| --- | --- |
| 2 | trailing crest 1.45–2.30 mm |
| 1 | trailing crest at least 0.35 mm above the leading crest |
| 2 | wire line pinned at that neck |
| 1 | molten plate line mostly pinned or advancing (not a receding film) |
| 2 | substrate under the bead melted on the center plane, with no gas sheet |
| 2 | one or more closed bubbles of 0.05–0.3 mm that stay in the pool |

Bubble points are withheld while the plate line is receding. A one-cell mobile pore and an open wake do not score. A locked lack-of-fusion pore at the foot does not score. The center-plane cut is `sidePlane` at y = 20 µm, drawn in `<tag>_side_alpha_T.png` and in the lower-left panel of `<tag>_vs_radiograph.png`. The full table is `ranking.csv`.

The 110°/150° screens in the table below still have a receding plate line and a solid substrate under the bead. They top out at 5, and none of them has a scored bubble. cal48 (Marangoni on) is the one center-plane slice with a gas sheet under the bead. The wetted and fused runs are in "Plate wetting and substrate melting".

| tag | t | score | trail / lead | plate line | substrate | what it shows |
| --- | --- | --- | --- | --- | --- | --- |
| cal62 | 0.80 s | 5 | 2.22 / 0.84 mm | 26/26 receding, 54° | solid | 700 W at 2 mm/s, run to 0.90 s. Lead fell to 0.84 mm. Plate still unwetted. Stopped. Center plane: `cal62_side_alpha_T.png`. |
| cal58 | 0.85 s | 5 | 2.06 / 1.30 mm | 29/29 receding, 51° | solid | 80+80+500 W to 0.95 s. Lead rose from 0.99 mm. Foot lack-of-fusion. Stopped. |
| cal76 | 0.70 s | 5 | 1.91 / 0.84 mm | 31/31 receding, 48° | solid | 30°/100° on 50+50+650 W. Lead fell. Plate still unwetted. Stopped. |
| cal90 | 0.40 s | 5 | 1.61 / 0.99 mm | 24/24 receding, 38° | solid | Force factor 10. Angle fell to 38° and the line is still entirely receding. Stopped. |
| cal66 | 0.90 s | 5 | 2.22 / 1.15 mm | 23/23 receding, 48° | solid | 30°/100° on 700 W. Lead rose from 0.99 mm. Stopped. |
| cal89 | 0.45 s | 5 | 1.91 / 0.99 mm | 25/25 receding, 59° | solid | Scan 3.5 mm/s. Plate still unwetted. Stopped. |
| cal88 | 0.45 s | 4 | 1.61 / 0.69 mm | 21/22 receding, 60° | solid | 50+50+700 W. Lead low and the wire line follows it to 0.69 mm. Stopped. |
| cal86 | 0.45 s | 5 | 1.76 / 1.30 mm | 22/22 receding, 51° | solid | Wire gap 0.02 mm on 700 W. Fully pinned. Plate still unwetted. Stopped. |
| cal72 | 0.70 s | 5 | 1.91 / 0.84 mm | 31/31 receding, 62° | solid | 50+50+650 W at 2 mm/s, to 0.75 s. Lead rose from 0.54 mm. Foot lack-of-fusion. Stopped. |
| cal87 | 0.50 s | 5 | 2.06 / 1.15 mm | 19/19 receding, 61° | solid | 80+80+700 W. Plate still unwetted. Stopped. |
| cal85 | 0.50 s | 5 | 1.91 / 1.30 mm | 23/23 receding, 50° | solid | Rear spot 600 W. Lead rose. Stopped. |
| cal91 | 0.50 s | 5 | 1.61 / 0.69 mm | receding, penetration 0 | solid | 40+40+650 W. Low lead, wire line held, plate unwetted. Stopped. |
| cal92 | 0.50 s | 5 | 2.06 / 0.69 mm | receding | solid | 60+60+700 W. Tall trail, low lead, plate unwetted. Stopped. |

cal94–cal98 finish on the same 110°/150° plate. The center-plane substrate stays near 1210–1290 K and the molten line is receding. They are not continued. Center-plane cuts: `cal94_side_alpha_T.png` through `cal98_side_alpha_T.png`.
| cal43 | 0.96 s | 5 | 2.06 / 0.99 mm | 34/34 receding, 47° | solid | 50+50+650 W at 1.05 s. Dome held. Plate still unwetted. Stopped. |
| cal36 | 1.00 s | 5 | 2.22 / 1.15 mm | 35/36 receding | solid | 700 W. Open wake, no locked bubble. Stopped. |
| cal66 | 0.70 s | 5 | 2.06 / 0.99 mm | 34/34 receding, 52° | solid | 30°/100° notch on 700 W. Continued to 0.90 s. |
| cal72 | 0.50 s | 5 | 1.91 / 0.54 mm | 26/27 receding | solid | Lowest lead. Continued to 0.75 s. |
| cal58 | 0.70 s | 5 | 1.91 / 0.99 mm | 37/37 receding, 54° | solid | 80+80+500 W. Continued to 0.95 s. |
| cal81 | 0.65 s | 5 | 1.76 / 0.84 mm | 15/15 receding, 61° | solid | Foot lack-of-fusion, 0.26 mm. Not a pool bubble. Stopped. |
| cal78 | 0.60 s | 4 | 1.91 / 1.15 mm | 26/26 receding, 54° | solid | 15°/50° window lost the pin (2/7). Not continued. |
| cal48 | 0.28 s | 3 | 1.30 / 1.15 mm | 23/23 receding | solid, gas sheet | Marangoni case. Gas layer on the center plane. |

Earlier paragraphs below were written while an open wake still scored. The geometry in them is unchanged. The number that ranks a run now is the table above and `ranking.csv`.

cal36 and cal35 both reach a trailing crest of 1.76 mm, which is one cell layer on this mesh, and both pin the wire line on that crest. They get there by different levers, and neither has a closed bubble. The plate line on both is receding and the substrate under the bead is solid.

cal43 drops the front spots to 50 W and puts 650 W in the rear spot, at scan 3 mm/s and feed 18 mm/s. At 0.32 s the trailing crest is 1.61 mm and the leading crest is 0.99 mm, the lowest leading crest of the finished set. The wire line is pinned on 9 of 11 cells from 0.84 mm to 1.76 mm. The cavity is open and off the center plane. Three pinch-offs did not stay. It is continued to 0.80 s. Comparison: `cal43_vs_radiograph.png`.

Aiming that kind of rear-heavy beam at the foot instead (cal46, aim z = 0.30 mm, 80+80+520 W) also keeps the leading crest at 0.99 mm, but the wire line reaches down to 0.69 mm, so the neck is not held. A 0.02 mm wire gap (cal52) and a steeper rear inclination (cal55, −48°) stay on the 1.45 mm crest. Those three are not continued.

More wire at the cal08 heat does not by itself make the trailing bulb. Feed 32 mm/s (cal53) raises the trail to 1.61 mm and the lead to 1.30 mm, with the line fully pinned and eight pinch-offs that do not stay. Feed 28 mm/s (cal42) leaves equal 1.30 mm crests. Scan 1.5 mm/s with the feed cut to 14 mm/s (cal44) puts the crest on the leading side, 1.30 mm against 0.99 mm, and locks a 0.34 mm lack-of-fusion pore in the plate at z ≈ −0.08 mm. The slow scan that did raise a trailing crest is cal35, which kept the feed near 18 mm/s and moved power rearward. cal42, cal44 and cal53 are not continued. The feed is crossed back onto the rear-heavy recipes instead: cal68 is 100+100+700 W at feed 32 mm/s, cal69 is 50+50+650 W at feed 28 mm/s, and cal70 is 50+50+650 W with the 60°/140° window.

cal36 puts 700 W in the rear spot and 100 W in each front spot, at scan 3 mm/s and feed 20 mm/s, with the plain 30°/90° wire window. At 0.36 s the leading crest is only 1.15 mm, so the trail stands 0.61 mm above it. The wire line is pinned on 8 of 9 cells and its top is the crest. The cavity is open and centred at y = 1.04 mm. Four pinch-offs were single mobile cells; none was locked, and there is no closure. One of those cells sat near the center plane (y ≈ 0.07 mm) and then vanished. The molten plate line is entirely receding at a mean angle of 64°. Travel is 1.1 mm. The continuation is below. Comparison at 0.36 s: `cal36_vs_radiograph.png`, since replaced by the 0.80 s figure.

cal35 is the taller-section screen: scan 2 mm/s, feed 18 mm/s, powers 120+120+560 W, same 30°/90° window. At 0.45 s the leading crest is 1.30 mm, so the trail stands 0.46 mm above it. All 8 wire cells are pinned, from 1.30 mm to 1.91 mm, so the top of the line is one cell above the crest. The cavity is open, centred at y = 1.08 mm. Eleven pinch-offs were recorded and none was locked. The plate line is entirely receding at a mean angle of 57°. Travel is only 0.9 mm against a pool about 2.7 mm long. It is continued to 1.00 s. Comparison: `cal35_vs_radiograph.png`.

Of the three trailing windows at 0.30 s, 60°/140° (cal34) kept the trailing crest highest. By 0.70 s that ranking changes. 45°/120° (cal32) reaches a 1.91 mm trail, the tallest finished crest, but the leading crest rises to 1.45 mm. 60°/140° (cal34) reaches 1.76 mm on the trail and keeps the lead at 1.15 mm, with the wire line up to 1.91 mm and 9 of 13 cells pinned. 75°/160° (cal33) loses the trail. The trailing crest there is 0.84 mm and the leading crest is 1.30 mm, and only 3 of 9 wire cells are pinned. Those cavities are open and centred near y = 1 mm. Pinch-offs were single mobile cells and none was locked. On every finished screen the molten plate line is entirely receding, including cal37's 150°/170° window (mean angle 47°).

cal45 aims the rear spot at z = 0.95 mm instead of 0.55 mm. At 0.28 s the centerline crests are equal at 1.30 mm, while the wire line sits at 1.15–1.76 mm, above that crest. The higher hit melts the flank and does not build the trailing bulb. It is not continued. Comparison: `cal45_vs_radiograph.png`.

cal47 lowers the plate window to 90°/140° with force factor 8. At 0.25 s the crests match cal34, 1.45 mm trailing and 1.15 mm leading, and 12 of 13 wire cells are pinned. The plate line is still receding (35 of 37 molten cells, mean angle 58°). One lack-of-fusion pore is locked, 0.23 mm, two cells, at (x, y, z) ≈ (0.65, 0.66, 0.23) mm. That is a pocket at the foot, not gas under the neck. The run is not continued; cal34 already carries this crest shape further. Comparison: `cal47_vs_radiograph.png`.

cal48 turns Marangoni back on, on the cal08 beams. At 0.28 s the trailing crest is 1.30 mm, the leading crest 1.15 mm, and the wire line is fully pinned at 1.15–1.45 mm. The hottest liquid on the centerline is 2584 K, cooler than the Marangoni-off screens. No pore is locked and there is no closure. It is not continued. Comparison: `cal48_vs_radiograph.png`.

cal39 is the wide trailing window, 90°/170°. At 0.28 s the trailing crest is 1.30 mm and the leading crest is 1.15 mm, with 5 of 13 wire cells receding. A lack-of-fusion pore is locked at the plate, 0.46 mm, 15 cells, centred near (0.60, 0.51, −0.05) mm. That is not gas under the neck. The wider window does not beat 60°/140°, and the run is not continued. Comparison: `cal39_vs_radiograph.png`.

cal51 (0.18 mm spots) and cal56 (force factor 2) both finish on the same crest pair as cal34, 1.45 mm trailing and 1.15 mm leading, with the wire line on the neck. The tighter spot does not steepen the foot: all 28 molten plate cells are receding and the mean angle is 50°. The weaker force leaves the same receding plate line, mean angle 58°. Neither has a locked pore at the end, and neither reaches the 1.76 mm crest of cal35 and cal36. They are not continued. Comparisons: `cal51_vs_radiograph.png`, `cal56_vs_radiograph.png`.

Across the trailing-window sweep the 60°/140° window (cal34) is the one that keeps a 1.45 mm trail and a 1.15 mm lead. A stickier 20°/90° window (cal40) holds the same trail height but the leading crest rises to 1.30 mm. Wider than 60°/140° does worse: 75°/160° drops the trail to 0.84 mm, 90°/170° leaves a plate pore, and 100°/165° (cal41) pins only 1 of 7 wire cells with equal 1.30 mm crests. cal40 and cal41 are not continued.

A 30°/100° window (cal38) and a tight 15°/50° window with no sector (cal49) reproduce cal34's 1.45 / 1.15 mm crests, with the line mostly pinned. Cutting the 60°/140° sector from 90° down to 45° (cal50) removes that trailing advantage: the crests are equal at 1.15 mm, and a 0.26 mm lack-of-fusion pore is locked on the leading side at z = 0.23 mm. A uniform 45°/110° window (cal57) makes the leading crest the higher one, 1.30 mm against 1.15 mm. None of these four is continued.

cal43, cal36, cal35, cal34, cal32 and cal38 are the continued runs. The screens that matched a lower score are not. cal66 puts cal38's 30°/100° window on cal36's 700 W rear spot. cal67 keeps that 700 W and lowers the rear aim from 0.55 mm to 0.35 mm. Two further crosses use the free cores: cal64 keeps cal36's 700 W rear spot and widens that spot to 0.40 mm, and cal65 puts that 700 W together with the 60°/140° window and a 2 mm/s scan. The refined 60°/140° mesh is cal10 on TaoSun-01 and is not started here. cal63 is the best coarse screen, cal36, at `--wire-refine 2` (about 38 µm in x and y, z left coarse), one rank, to 0.25 s. Powers stay 100+100+700 W and there is no trailing sector.

cal59 keeps the 60°/140° window with cal35's taller section (scan 2 mm/s, feed 18 mm/s, 120+120+560 W) to 0.60 s. cal61 keeps that window with cal36's powers (100+100+700 W, scan 3 mm/s) to 0.40 s. cal62 is cal36's powers at scan 2 mm/s and feed 20 mm/s, to 0.60 s, to see whether the tall crest lengthens into a bulb. cal31 stays the refined cal08 mesh. Solvers stay at `nice -n 10` and the rank total stays at or under 32.

By 0.59 s the cal36 continuation has the wire line fully pinned from 0.99 mm to 2.22 mm. cal35 at 0.58 s is fully pinned from 1.45 mm to 2.06 mm. Both wakes are still open, and neither continuation has a closure event. The half-domain centroid stays near y = 1 mm, which is what a cavity sitting on the symmetry plane reports. The official scores above stay on the posted slices until each continuation is post-processed.

cal71 repeats the 100+100+700 W case on a full-width mesh to 0.30 s, so the wake centroid is not folded onto y ≥ 0. cal72 puts the 50+50+650 W split on cal35's section (scan 2 mm/s, feed 18 mm/s) to 0.50 s. cal73 keeps the 750 W of cal43 and moves it to 25+25+700 W. cal74 tightens the 700 W spot to 0.18 mm. cal75 raises that spot's aim to z = 0.70 mm. cal76 puts the 30°/100° window on the 50+50+650 W split. cal77 shallows the rear beam to −28°. cal78 uses the 15°/50° wire window on the 700 W spot. Each is one rank.

cal58 cuts the front spots to 80 W and the rear spot to 500 W, at scan 2 mm/s and feed 16 mm/s. At 0.34 s the trailing crest is 1.61 mm and the leading crest is 1.15 mm. All 10 wire cells are pinned from 0.99 mm to 1.61 mm. The cavity is open. Two pinch-offs did not stay. All 23 molten plate cells are receding, at a mean angle of 50°. It reaches score 8 with less rear power than cal36 or cal43, and it is continued to 0.70 s. Comparison: `cal58_vs_radiograph.png`.

cal54 keeps the cal08 beams and changes only the speeds, to scan 2.5 mm/s and feed 22 mm/s. At 0.36 s the trailing crest is 1.61 mm and the leading crest is 1.30 mm, so the advantage is 0.31 mm. All 11 wire cells are pinned from 1.30 mm to 1.76 mm. A single-cell gas pore, 0.15 mm, showed up near the center plane just before the end and was gone in the final sample. The run is not continued. Comparison: `cal54_vs_radiograph.png`.

The cal58 heat is crossed on the freed cores. cal79 adds the 60°/140° window. cal80 raises the feed from 16 mm/s to 22 mm/s. cal81 drops the front spots to 40 W and puts 560 W in the rear spot, still at scan 2 mm/s and feed 16 mm/s.

At 0.70 s, cal32 (45°/120°) has a trailing crest of 1.91 mm and a leading crest of 1.45 mm. Eleven of 13 wire cells are pinned from 1.15 mm to 1.91 mm. All 35 molten plate cells are receding. The cavity is still open, 2.61 mm³. A single-cell gas pore appeared during the run and did not stay. The lead rose with the trail, so this continuation stops here. Comparison: `cal32_vs_radiograph.png`.

cal34 at the same time keeps the leading crest at 1.15 mm while the trail reaches 1.76 mm. The wire line runs from 1.15 mm to 1.91 mm, with 9 of 13 cells pinned and 3 receding. All 22 molten plate cells are receding, mean angle 53°. The cavity is open, 2.61 mm³. It is continued to 1.00 s. Comparison: `cal34_vs_radiograph.png`.

cal61 puts that 60°/140° window on the 100+100+700 W beams. At 0.40 s the crests are 1.61 mm and 1.15 mm, but only 4 of 10 wire cells are pinned and 6 are receding. A 3-cell mobile gas pore, 0.22 mm, near the center plane at 0.40 s was gone in the final sample. The hotter rear spot does not hold this window, and the run is not continued. Comparison: `cal61_vs_radiograph.png`.

The 45°/120° window is what grew the 1.91 mm trail, so it is crossed onto the rear-heavy splits that kept the lead down. cal82 is 50+50+650 W with that window. cal83 is 100+100+700 W with that window.

At 0.80 s, cal36 is the closest shape so far. The trailing crest is 2.22 mm and the leading crest has fallen to 0.84 mm. All 10 wire cells are pinned from 0.99 mm to 2.22 mm. All 21 molten plate cells are receding, mean angle 44°. The cavity is still open, 2.72 mm³, centred at y = 1.17 mm on the half mesh. Fifty-six pinch-offs were recorded. A single-cell gas pore near the center plane at the last sample did not stay. The crest is at the top of the radiograph's height, so the run is continued only to 1.00 s to see whether one of those pinch-offs locks. Comparison: `cal36_vs_radiograph.png`.

cal84 is the same 100+100+700 W at scan 5 mm/s and feed 22 mm/s, to 0.32 s. The faster pass is a test of whether the tail can freeze around a pinch-off that the 3 mm/s pool keeps open.

cal66 puts the 30°/100° window on the 100+100+700 W beams. At 0.40 s the trail is 1.61 mm, the lead is 0.99 mm, and all 12 wire cells are pinned from 0.99 mm to 1.76 mm. All 26 molten plate cells are receding, mean angle 59°. The 60°/140° window on this same power (cal61) pinned only 4 of 10 cells, so 30°/100° is the window that holds. The cavity is open. It is continued to 0.70 s. Comparison: `cal66_vs_radiograph.png`.

cal74 tightens that rear spot to 0.18 mm. At 0.36 s the crests are the same pair, 1.61 mm and 0.99 mm, and all 10 wire cells are pinned. The trail is a cell below cal36 at the same time, so the tighter spot is not continued. Comparison: `cal74_vs_radiograph.png`.

cal78 uses the 15°/50° wire window, with no sector, on the 700 W spot. At 0.36 s the lead is already 0.84 mm, matching cal36 at 0.80 s, and the trail is 1.61 mm. Only 6 of 12 wire cells are pinned; the other 6 are advancing. It is continued to 0.60 s to see whether that line finishes pinning while the trail grows. Comparison: `cal78_vs_radiograph.png`.

Slowing cal36's 100+100+700 W beams to 2 mm/s (cal62) reaches a 2.06 mm trail at 0.60 s with all 12 wire cells pinned, from 1.30 mm to 2.22 mm. The leading crest is still 1.30 mm. It is continued to 0.90 s to see whether that lead falls the way cal36's did. Giving the 30°/100° window more time (cal38) or putting 60°/140° on the tall section (cal59) also reaches 1.91 mm, and in both the lead rises, to 1.30 mm and 1.45 mm. A 0.40 mm rear spot (cal64) does the same. Those three are not continued. Comparisons: `cal62_vs_radiograph.png`, `cal38_vs_radiograph.png`, `cal59_vs_radiograph.png`, `cal64_vs_radiograph.png`.

Lowering the rear aim to 0.35 mm (cal67) keeps a fully pinned line and a 0.99 mm lead, with the trail at 1.61 mm. Raising it to 0.70 mm (cal75) lets the lead back up to 1.15 mm. A shallower rear beam, −28° (cal77), and the 60°/140° window on 50+50+650 W (cal70) leave the trail at 1.45 mm. Extra feed on the 650 W split (cal69) reaches 1.76 / 0.99 mm, but only 5 of 8 wire cells are pinned and 3 are receding. A lack-of-fusion cell showed up at the foot and was gone in the final sample. None of these four is continued.

The free cores go to levers around the 700 W recipe. cal85 drops the rear spot to 600 W. cal86 closes the wire gap to 0.02 mm. cal87 cuts the front spots to 80 W and keeps 700 W behind. cal88 cuts them to 50 W. cal89 scans at 3.5 mm/s, between cal36 and the 5 mm/s freeze test. cal90 raises the contact-force factor from 6 to 10.

At 0.80 s the 50+50+650 W run (cal43) matches cal36's leading crest, 0.84 mm, with the trail at 1.91 mm and all 10 wire cells pinned from 0.99 mm to 2.06 mm. It is continued to 1.05 s. Comparison: `cal43_vs_radiograph.png`.

At 0.70 s the milder 80+80+500 W run (cal58) has a 1.91 mm trail and a 0.99 mm lead, with all 9 wire cells pinned from 0.99 mm to 2.06 mm. It is continued to 0.95 s. Comparison: `cal58_vs_radiograph.png`.

Cutting the front spots to 40 W at that slow scan (cal81, rear 560 W) drops the lead to 0.69 mm at 0.45 s. By 0.65 s the lead is back to 0.84 mm, all 7 wire cells are pinned from 0.99 mm to 1.91 mm, and the trail is still 1.76 mm. The foot pore grew from one cell to three, 0.26 mm, centred near (−0.73, 0.37, 0.43) mm, and it is locked. The run stops. Comparison: `cal81_vs_radiograph.png`.

The 30°/100° window on 50+50+650 W (cal76) reaches 1.76 / 0.99 mm at 0.40 s with 12 of 14 wire cells pinned. It is continued to 0.70 s. The same window on 80+80+500 W (cal79) does not beat the plain cal58 crests. Comparison: `cal76_vs_radiograph.png`.

Feed 32 mm/s on the 700 W spot (cal68) pins every wire cell but the line runs down to 0.54 mm, and a lack-of-fusion cell locks at z = 0.38 mm. Front spots of 25 W (cal73) drop the lead to 0.69 mm and the line follows it down. Both are not continued. Comparisons: `cal68_vs_radiograph.png`, `cal73_vs_radiograph.png`.

cal91 keeps 40 W fronts and raises the rear spot to 650 W at scan 3 mm/s, to see if the foot pore in cal81 was the slow scan. cal92 puts 60 W in each front spot with 700 W behind. cal94 is cal81's slow scan with the front spots raised from 40 W to 60 W.

By 1.00 s the 700 W case (cal36) still has a 2.22 mm trail, but the leading crest has come back from 0.84 mm at 0.80 s to 1.15 mm. Twelve of 13 wire cells are pinned, from 1.15 mm to 2.37 mm. Ninety-two pinch-offs were recorded and none stayed. The run stops here. The 0.80 s comparison, with the lower lead, is `cal36_0p80_vs_radiograph.png`. The 1.00 s comparison is `cal36_vs_radiograph.png`.

The slow-scan tall section (cal35) at 1.00 s is fully pinned from 1.45 mm to 2.22 mm, with the trail at 2.06 mm and the lead up to 1.45 mm. The 60°/140° window (cal34) at 1.00 s has the lead up to 1.45 mm as well, from 1.15 mm at 0.70 s. Neither is continued further. Putting that window on the 700 W spot at 2 mm/s (cal65) leaves the trail at 1.45 mm. The 45°/120° window on 700 W (cal83) does the same. The 5 mm/s pass (cal84) keeps a 1.76 / 0.99 mm pair and does not freeze a pore.

The lowest lead with a tall trail is cal72: 50+50+650 W, scan 2 mm/s, feed 18 mm/s. At 0.50 s the trail is 1.91 mm and the lead is 0.54 mm. Ten of 12 wire cells are pinned, from 0.84 mm to 2.06 mm. The cavity is open. It is continued to 0.75 s. Comparison: `cal72_vs_radiograph.png`. cal95 is that split at scan 2.5 mm/s. cal96 keeps the 2 mm/s scan and lowers the feed to 16 mm/s. cal97 drops the rear spot to 600 W. cal98 raises the front spots to 70 W.

At 0.70 s the 30°/100° window on 100+100+700 W (cal66) has a 2.06 mm trail and a 0.99 mm lead, with all 10 wire cells pinned from 0.99 mm to 2.06 mm. The lead did not climb the way cal36's did after 0.80 s. It is continued to 0.90 s. Comparison: `cal66_vs_radiograph.png`. The 45°/120° window on 50+50+650 W (cal82) also drops the lead to 0.54 mm, and the wire line follows it down to 0.69 mm with only 3 of 8 cells pinned. It is not continued.

On the full-width mesh (cal71, 70 528 cells, the same 100+100+700 W) the wake centroid is at y = −0.004 mm and the volume is 6.08 mm³, about twice the half-domain cavity. At 0.30 s the trail is only 1.30 mm and the lead is 1.15 mm, with 15 of 20 wire cells pinned. The cavity is open. It is continued to 0.55 s. That open volume is not the target. Comparison: `cal71_vs_radiograph.png`.

At 0.90 s the slow 700 W run (cal62) has a 2.22 mm trail and a 0.84 mm lead, with the wire line pinned from 0.84 mm to 2.37 mm. The plate line is 26/26 receding at 54° and the substrate under the bead is solid, so the open wake is not a bubble. The run stops. Center-plane cut: `cal62_side_alpha_T.png`.

At 1.05 s, cal43 still has the dome (trail 2.06 mm, lead 0.99 mm, wire line fully pinned) and the plate line is 34/34 receding at 47°. The substrate under the bead on the center plane is solid. The 0.96 s center-plane cut is `cal43_side_alpha_T.png`. The run stops. cal78 at 0.60 s lost the wire pin (2 of 7 cells) and the lead rose to 1.15 mm. It is not continued. Comparison: `cal78_vs_radiograph.png`.

## Plate wetting and substrate melting

The plate window on cal08 is 110°/150°. The molten line sits near 50°, so every cell is receding and the Young force lifts metal off the plate. That is the film TaoSun-01 called out on cal11. These screens keep the 30°/100° wire trail that holds the notch, and they lower the plate window. They do not repeat cal11 (refined 60°/140°) or cal12 (cal36 power on a refined mesh). cal63 is already that refined 700 W case here and is left running. Each new run is one rank at `nice -n 10`.

| tag | plate window | melting change | beams |
| --- | --- | --- | --- |
| cal99 | 10°/40° | none | 100+100+700 W, scan 3 mm/s, to 0.40 s |
| cal100 | 20°/55° | none | same |
| cal101 | 5°/25° | none | same |
| cal102 | 30°/80° | none (57° sits inside the window, so the line can pin) | same |
| cal103 | 10°/40° | substrate absorptivity 0.55 | same |
| cal104 | 10°/40° | preheat 900 K | same |
| cal105 | 10°/40° | absorptivity 0.55, preheat 800 K, fronts 180 W | rear spot still 700 W |
| cal106 | 15°/45° | absorptivity 0.60, preheat 700 K, scan 2 mm/s | 80+80+650 W, to 0.45 s |
| cal107 | 20°/55° | absorptivity 0.55 | 100+100+700 W, to 0.40 s |
| cal108 | 20°/55° | absorptivity 0.55, preheat 900 K | same |
| cal109 | 20°/55° | absorptivity 0.60, preheat 800 K, fronts 180 W | rear spot 700 W |
| cal110 | 20°/55° | absorptivity 0.55, preheat 900 K | trail pin 15°/50° over 60° of +x, to 0.60 s |
| cal111 | 20°/55° | same as cal110 | trail pin 20°/45° over 45° of +x, to 0.60 s |
| cal112 | 20°/55° | absorptivity 0.60, preheat 800 K, fronts 180 W | trail pin 15°/50° over 60° of +x, to 0.60 s |
| cal113 | 20°/55° | same heat as cal111 | wire floor 10°/70° over 60° of +x, to 0.65 s |
| cal114 | 10°/40° | substrate absorptivity 0.65, no preheat | cal103 notch (trail 30°/100°), to 0.70 s, then 1.00 s |
| cal115 | 10°/40° | same as cal114 | wire floor 15°/80°, to 0.55 s |

A run that wets the plate and melts the substrate is continued to at least 0.60 s. The wire angle on these heated plates sits near 17–33°. A 30°/100° trail puts the low end of that outside the window, so those cells recede. cal110–cal112 put a pinning window on the trailing face only. An open wake on these screens is not the target. No run has a closed bubble of 0.05–0.3 mm. Pinch-offs stay one-cell and mobile.

At about 0.06 s, cal99–cal106 already have no receding molten plate cells. cal100 (20°/55°) has 22 of 23 pinned, at 43°. The 110°/150° runs next to them are still entirely receding, including cal90, whose force factor of 10 only moved the angle down to 38°.

At the 0.10 s center-plane cut the plate surface is still solid on the angle-only runs (about 1230–1440 K). It is above the 316L solidus where the substrate absorptivity or the preheat was raised: cal103 at 1752 K, cal104 at 1858 K, cal105 at 1819 K, cal106 at 1764 K. The bead is not tall yet, so that is a hot plate surface, not a fused dome.

Finished slices, center plane at y = 20 µm. "Plate" is pinned / advancing / receding. Gap fraction is 0 on every row. cal63 (refined 700 W, stopped at 0.25 s) and cal71 (full width, 0.55 s) stay on 110°/150° with the whole plate line receding and a solid substrate, so they are not continued.

| tag | t | score | trail / lead | plate | melt | wire line |
| --- | --- | --- | --- | --- | --- | --- |
| cal111 | 0.60 s | 6 | 2.06 / 0.99 mm | 39/13/0, 49° | 12/12, 2142 K | 4/10 pinned, 6 receding, z 1.30–1.45 mm, mean 20°. The 20° trail floor is the angle itself, so the line sits 0.6 mm below the crest. |
| cal108 | 0.40 s | 6 | 1.91 / 0.84 mm | 40/4/0, 43° | 5/5, 2071 K | 4/8 pinned, 4 receding, mean 27°, under the 30° floor. Continued to 0.65 s. |
| cal100 | 0.40 s | 6 | 1.45 / 0.99 mm | 13/11/0, 54° | 0/9, 1380 K | Wetted dome, solid plate. Not continued. |
| cal101 | 0.40 s | 6 | 1.45 / 0.84 mm | 4/25/0, 46° | 0/11, 1364 K | Same. The 5°/25° window advances the line. Not continued. |
| cal102 | 0.40 s | 6 | 1.61 / 1.15 mm | 26/0/4, 52° | 0/10, 1361 K | Mostly pinned, four cells still receding. Solid plate. Not continued. |
| cal99 | 0.40 s | 5 | 1.45 / 1.15 mm | 9/17/0, 48° | 0/10, 1358 K | Wetted, solid. Not continued. |
| cal109 | 0.40 s | 4 | 0.69 / 0.23 mm | 28/3/0, 43° | 5/5, 2197 K | All 9 wire cells recede at 17°. Crest stays low. Continued to 0.65 s. |
| cal110 | 0.60 s | 3 | 0.69 / 1.15 mm | 47/7/0, 45° | 10/10, 2204 K | 9/11 pinned at 27° inside 15°/50°, but the trail crest never grows. |
| cal112 | 0.60 s | 3 | 0.84 / 0.54 mm | 43/27/2, 54° | 13/13, 2017 K | 9/13 pinned. Hotter fronts, short dome. |
| cal103 | 0.40 s | 3 | 0.69 / 1.15 mm | 8/24/0, 46° | 4/7, 1881 K | Fused and wetted, lead taller than the trail. Continued to 0.65 s. |
| cal104 | 0.40 s | 3 | 0.69 / 1.30 mm | 5/25/0, 51° | 4/7, 1719 K | Same. Continued to 0.65 s. |
| cal105 | 0.40 s | 3 | 0.69 / 0.69 mm | 12/30/0, 47° | 7/7, 2001 K | Fully fused columns, short crests. Continued to 0.65 s. |
| cal106 | 0.45 s | 3 | 0.54 / 1.15 mm | 23/17/0, 46° | 3/3, 1941 K | Slow scan, lead taller. Continued to 0.65 s. |
| cal107 | 0.40 s | 3 | 0.69 / 1.15 mm | 32/11/1, 48° | 6/7, 2097 K | Plate pinned, crest still low. Continued to 0.65 s. |

cal111 is the fused dome: trail 2.06 mm, lead 0.99 mm, every trail column melted, no receding plate cell, no gas sheet. The wire line does not make the notch. Its mean angle is 20°, which is the receding edge of the 20°/45° trail window, so 6 of 10 cells recede and the line stays at 1.30–1.45 mm. cal110 pins that line (9 of 11, window 15°/50°) and the trailing crest collapses to 0.69 mm. Center-plane cuts: `cal111_side_alpha_T.png`, `cal108_side_alpha_T.png`, `cal110_side_alpha_T.png`. The 0.40 s cuts of the runs that continue are `cal103_0p40_side_alpha_T.png` through `cal105_0p40_side_alpha_T.png`, `cal107_0p40_side_alpha_T.png`, `cal108_0p40_side_alpha_T.png`, `cal109_0p40_side_alpha_T.png`, and `cal106_0p45_side_alpha_T.png`.

cal113 keeps cal111's heat and plate window and lowers the wire floor to 10°, with the advancing limit at 70°, on a 60° trailing sector. That puts the 20° cells inside the window instead of on the receding edge. It runs to 0.65 s.

At 0.65 s the two runs that were continued from a wetted, partly fused bead are the new top of the table. Neither has a closed bubble. The plate line on both has no receding cell, and the center plane has no gas sheet.

| tag | t | score | trail / lead | plate | melt | wire line |
| --- | --- | --- | --- | --- | --- | --- |
| cal113 | 0.65 s | 8 | 1.61 / 0.99 mm | 0 of 50 receding, 42° | 11/11 | 10/15 pinned, z 1.45–1.76 mm, mean 18°. Dome, notch, and full fusion. No bubble. Continued to 0.90 s. |
| cal103 | 0.65 s | 7 | 1.76 / 1.15 mm | 0 of 38 receding | 4/13 | 9/9 pinned, z 1.30–1.91 mm, mean 39°. At 0.90 s the trail is 1.91 / 1.15 mm but only 3 of 8 wire cells stay pinned (mean 15°) and 6 of 21 columns are melted. Score 6. Stopped. |
| cal108 | 0.65 s | 7 | 1.91 / 0.99 mm | 1 of 46 receding | 11/11 | 3/10 pinned, mean 24°. At 0.90 s the trail falls to 0.84 mm and the lead is 0.99 mm. Score 3. The 0.65 s cut is `cal108_0p65_side_alpha_T.png`. Stopped. |
| cal109 | 0.65 s | 4 | 0.69 / 0.23 mm | 0 of 51 receding | 13/13 | Crest never grows. Not continued. |
| cal104 | 0.65 s | 3 | 1.15 / 1.30 mm | 0 of 34 receding | 6/12 | Trail rose from 0.69 mm and is still under the lead. Not continued. |
| cal105 | 0.65 s | 3 | 0.69 / 1.15 mm | 0 of 47 receding | 10/10 | Wire line up to 2.06 mm over a short trail. Not continued. |
| cal106 | 0.65 s | 3 | 0.69 / 1.30 mm | 0 of 54 receding | 10/10 | Lead stays taller. Not continued. |
| cal107 | 0.65 s | 2 | 0.84 / 1.15 mm | 1 of 49 receding | 5/14 | Crest stays low. Not continued. |
| cal31 | 0.40 s | 4 | 1.76 / 0.84 mm | 40 of 45 receding, 58° | 0/9 | Refined cal08. Plate still receding, substrate solid. Stopped. |

Center-plane cuts: `cal103_side_alpha_T.png`, `cal108_side_alpha_T.png`. The 0.65 s copies kept before the next continuation are `cal103_0p65_side_alpha_T.png` and `cal108_0p65_side_alpha_T.png`.

cal103's 39° wire angle is why 30°/100° pins every cell at 0.65 s. By 0.90 s that angle has fallen to 15° and the pin is gone, while the trail has grown to 1.91 mm. cal108's preheated pool sits at 24° at 0.65 s, so the same 30° floor recedes, and by 0.90 s the trailing crest has fallen to 0.84 mm. Neither holds a bubble. The open wake on these slices is still about 2–3 mm³.

cal113 is that preheated pool with the wire floor lowered to 10° and the ceiling at 70°, on a 60° trailing sector. At 0.65 s it is the first run to take the dome, the notch, and a fully melted plate together: trail 1.61 mm, lead 0.99 mm, 11 of 11 columns melted, no receding plate cell, no gas sheet, 10 of 15 wire cells pinned from 1.45 to 1.76 mm. Score 8. The cavity report is still open, 2.77 mm³, and the only gas pores sit below the plate (z ≈ −0.6 mm), so nothing in the pool scores. Center-plane cut: `cal113_side_alpha_T.png`. It is continued to 0.90 s. The 0.65 s copy is `cal113_0p65_side_alpha_T.png`.

cal114 is cal103's pinned notch with substrate absorptivity raised from 0.55 to 0.65, and no preheat. At 0.70 s it matches cal113's score of 8 from the other direction: trail 1.91 mm, lead 1.15 mm, 9 of 15 columns melted, no receding plate cell, 6 of 10 wire cells pinned from 1.45 to 1.76 mm (mean 29°, four cells still under the 30° floor). No closed bubble. The open wake is still there. It is continued to 1.00 s. Center-plane cut: `cal114_side_alpha_T.png`.

cal113 at 0.90 s loses the crest the same way cal108 did. The trail is 0.84 mm and the lead is 0.99 mm, with the plate still wetted and 18 of 18 columns melted. Score 3. The score-8 slice remains the 0.65 s cut. The preheated pool is not continued further.

cal115 keeps cal114's plate, power, and absorptivity, and lowers the wire floor from 30° to 15° so the 29° cells pin. It runs to 0.55 s.

At 1.00 s cal114's crest has fallen. The trail is 1.15 mm and the lead is 0.99 mm, 12 of 22 columns are melted, and 8 of 13 wire cells recede at 24°. Score 3. The plate line is still not receding, and there is still no pool bubble. The score-8 cut is the 0.70 s one, `cal114_0p70_side_alpha_T.png`. The run stops.

cal115 at 0.55 s lowers that wire floor to 15°. Eight of ten wire cells pin, but the line stays at 1.30–1.45 mm while the trail grows to 2.37 mm, above the 2.30 mm cap, and the lead is 1.30 mm. All six trail columns on that slice are melted and the plate line is not receding. Score 5. No closed bubble. Nothing is left running.
