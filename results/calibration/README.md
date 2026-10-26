# Wire-cavity calibration (oxygen off)

Goal: a 3D melt pool that looks like the side-view radiograph. A 1 mm vertical wire melts into a dome on the plate, taller on the trailing side, with a notch where the three-phase line sits on the wire near the top of the dome, and small closed bubbles in the melt. Process parameters are free. Oxygen stays off through cal15. From cal16, Sahoo–Belton `sigma(T, a_O)` can be on while the plate and wire windows stay as written (`--oxygen-sigma-only`).

The reference run (`results/reference`) aimed the beams outward. With shadowing on, each ray deposits on the first metal it meets, and those rays met the wire at the top of the domain (front-beam axis at z = 3.44 mm). The plate pool was wide and shallow and the wire contact line sat at z ≈ 3.3 mm.

Negative inclination reverses that. The beam moves inward as it descends, so the first hit is the foot or the flank instead of the top. `scripts/preview_beam_hits.py` prints that hit before a run.

Side views put the trailing side (+x) on the left. Scores are against the radiograph, not against the previous iteration.

From cal13 on, the open-cavity volume is not the score. The bead has to wet a molten plate with no gas film under it, keep the trailing-tall dome, and shed closed bubbles of about 0.05–0.3 mm at the wire.

## cal01 — plate spots outside the wire

Command: `results/calibration/launch_cal01.sh`. Coarse mesh, 150 µm, 30305 cells, 24 ranks. Wall clock 470 s for 0.10 s.

| item | value |
| --- | --- |
| azimuths | 40°, −40°, 180° |
| inclinations | −8°, −8°, −8° (inward) |
| powers | 500 + 500 + 800 W |
| 1/e² radius | 0.40 mm |
| aims | front plate hit r ≈ 0.94 mm, rear plate hit x = +0.99 mm |
| feed | gap 0.10 mm, feed starts at 0.05 s, 30 mm/s, scan 6 mm/s |

At 0.10 s the plate holds a pool 3.0 mm long, 2.5 mm wide and 0.56 mm deep. Tmax is 3102 K, just at the 316L boiling point, and the depth stays 0.56 mm, so this is not a keyhole. The wire is still solid. On the centerline the liquid only reaches z = 0.23 mm, and the trailing crest (0.08 mm) is lower than the leading crest (0.23 mm). The wire contact line is at z = 0.08–0.23 mm (4 cells, 3 pinned). That is the foot, not the top of the domain. The open cavity is 0.62 mm³ on the half domain, centered at y = 0.97 mm, so it is a side gap rather than a wake under a neck. Fed cross-section is ~0.01 mm² against the steady 3.93 mm²: 50 ms of wire cannot build the dome.

Verdict: the top-of-wire hit is gone, and a wire line exists at the foot. The spots still miss the wire, so the wire does not melt and there is no dome, no high neck and no wake cavity. Figures: `cal01_side_alpha_T.png`, `cal01_iso_alpha.png`.

## cal02 — rear beam into the wire flank

Command: `results/calibration/launch_cal02.sh`. Same coarse mesh, 24 ranks. Wall clock 937 s for 0.16 s.

| item | value |
| --- | --- |
| azimuths | 30°, −30°, 180° |
| inclinations | −28°, −28°, −32° |
| powers | 400 + 400 + 700 W |
| 1/e² radius | 0.40 mm |
| aims | front clips the foot (z ≈ 0.11 mm); rear axis meets the flank at z ≈ 0.75 mm |
| feed | gap 0.10 mm, feed starts at 0.02 s, 30 mm/s, scan 6 mm/s |

At 0.16 s the liquid on the centerline reaches z = 1.15 mm and the wire contact line sits at z = 0.84–1.30 mm (11 cells, pinned and receding). That line is on the flank, near the top of the melt, not at the ceiling. Metal outside the wire is taller on the trailing side (0.69 mm) than on the leading side (0.38 mm). The plate itself is not melted (pool depth 0). Tmax is 2760 K. The open cavity is 2.8 mm³ on the half domain, 1.2 mm deep and 1.7 mm downstream, centred at (x, y, z) = (0.64, 0.98, 0.84) mm, so the gas is beside the wire in the wake. The y = 0 slice and the y-projection still show a solid wire, because that gas does not cross the center plane. Travel is only 0.8 mm, and the downstream section is 0.06 mm² against 3.93 mm², so this is still startup.

Verdict: the wire is melting and the contact line is in the right band, with the trailing side higher. The dome is a shoulder, not a bead of wire-diameter height, and the cavity is not the centerline notch in the radiograph. Same beams continued to 0.48 s to let the fed volume pile up. Figures: `cal02_side_alpha_T.png`, `cal02_projection.png`, `cal02_iso_alpha.png`.

## cal02 continued to 0.48 s

`continue_cal02.sh`, about 26 min of wall time on top of the 937 s above. The contact height stopped climbing: z = 0.99–1.76 mm at both 0.36 s and 0.48 s. The solidified section at x = 2.93 mm is h = 0.80 mm, w = 2.49 mm, area 1.62 mm² (steady target 3.93 mm²). Off the wire, the trailing crest is 1.15 mm and the leading crest is 0.69 mm. Pool length 3.9 mm, width 3.4 mm, depth 0, Tmax 2785 K. The open cavity is still 2.8 mm³ and 1.7 mm deep, centred beside the wire (y ≈ 1.0 mm), so the y-projection does not show a notch. Figures: `cal02b_side_alpha_T.png`, `cal02b_projection.png`, `cal02b_iso_alpha.png`.

Verdict: right scale, trailing side higher, wire line stable. The line still sits above the crest (1.76 mm vs 1.15 mm), the pool is spreading wider than the bead is tall, and the cavity is not on the center plane. Not a radiograph match.

## cal03 — narrower spots, lower flank hit

Command: `launch_cal03.sh`. Coarse mesh, 24 ranks, 920 s for 0.20 s.

| item | value |
| --- | --- |
| azimuths | 22°, −22°, 180° |
| inclinations | −16°, −16°, −30° |
| powers | 350 + 350 + 520 W |
| 1/e² radius | 0.32 mm |
| aims | front plate hit r ≈ 0.82 mm (misses the wire); rear axis meets the wire at z ≈ 0.56 mm |
| feed | gap 0.10 mm, feed starts at 0.02 s, 30 mm/s, scan 6 mm/s |

At 0.20 s the pool is 2.8 mm long and 1.9 mm wide (cal02 had spread to 3.4 mm by 0.48 s). Tmax 2830 K. The wire line is entirely pinned at z = 0.84–0.99 mm, which is the top of the liquid on the centerline. The trailing crest is 0.69 mm and the leading crest is 0.84 mm; the track is too short for the trailing pile-up seen later in cal02. Open cavity 2.1 mm³, depth 0.92 mm, still centred off the center plane. Figures: `cal03_side_alpha_T.png`, `cal03_projection.png`.

The screen has the contact on the crown and a narrower pool, so the same case was continued to 0.70 s (`continue_cal03.sh`, another 2294 s). `launch_cal03.sh` now carries end time 0.70 s so one command repeats the full run.

## Result — cal03 at 0.70 s

Oxygen off. Coarse 150 µm half-domain, 24 ranks. Total wall time about 54 min (920 s to 0.20 s, then 2294 s to 0.70 s).

At 0.70 s the solidified section is h = 1.08 mm, w = 2.2 mm, area 2.43 mm² (the wire-feed steady area is 3.93 mm²). Off the wire the trailing crest is 1.61 mm and the leading crest is 1.15 mm. The wire line is fully pinned at z = 1.15–1.91 mm, which brackets the crest: the bottom of the line meets the bead and the top sits about 0.3 mm above the trailing crest. On the centerline, gas beside the wire occupies z ≈ 1.45–1.91 mm over x ≈ 0.7–2.5 mm, which is the notch above the bead. The cavity report is open, 3.0 mm³, depth 1.84 mm, centred at (x, z) = (0.45, 1.30) mm and y ≈ 1.2 mm, so most of that volume is beside the center plane rather than a closed bubble under the bead. Pool 4.2 mm by 2.5 mm, depth 0, penetration of the section 0.24 mm, Tmax 2714 K. No enclosed pores.

This is the reference. It has the dome, the trailing pile-up, and a pinned line at the neck. It does not have a closed cavity under the bead, and the track has not yet taken up the full wire cross-section. Comparison: `cal03b_vs_radiograph.png`. Fields: `cal03b_side_alpha_T.png`, `cal03b_projection.png`, `cal03b_iso_alpha.png`.

Repeat that cal03 run with `./results/calibration/launch_cal03.sh`. It is not a radiograph match: the bead is a fillet, the section is short of the fed area, and there is no gas pocket under the contact line.

## cal04 — steep plate angle, slower scan

Command: `launch_cal04.sh`. Coarse mesh, 33611 cells, 24 ranks. Wall clock 1812 s for 0.36 s.

Plate window 70°/125°, wire window 20°/150°. Scan 4 mm/s (steady area 5.89 mm²), powers 420 + 420 + 680 W. Rear axis meets the wire at z ≈ 0.85 mm.

At 0.36 s the apparent plate angle is 50° and 41 of 44 molten plate-line cells are receding, so the 70° floor is not being held. The pool is 3.3 mm by 3.1 mm. Crests are 1.15 mm trailing and 1.30 mm leading. The wire line is pinned at z = 1.30–1.61 mm. The section at the pool tail is 0.21 mm²; travel is only 1.4 mm, shorter than the pool, so this is not quasi-steady. Tmax 2760 K. Open cavity 2.4 mm³. Figures: `cal04_side_alpha_T.png`, `cal04_projection.png`, `cal04_iso_alpha.png`.

Verdict: still a wide shallow bead. The Young force at factor 1 does not pull the angle up to 70° while Marangoni is on.

## cal05 — Marangoni off, stronger Young force

Command: `launch_cal05.sh`. Same beams, scan and 70°/125° window as cal04, plus `--no-marangoni` and `--contact-force-factor 4`. Wall clock 1697 s for 0.30 s.

The apparent plate angle is still 49°, with 36 of 37 molten plate-line cells receding. The pool is 3.2 mm by 2.8 mm. Crests are about 1.1–1.3 mm. The wire line is pinned at z = 1.15–1.61 mm. Tmax 2935 K. Open cavity 2.6 mm³, still off the center plane. The section at the pool tail is 0.03 mm² because travel (1.0 mm) is shorter than the pool. Figures: `cal05_side_alpha_T.png`, `cal05_projection.png`, `cal05_iso_alpha.png`.

Verdict: scaling the Young force and switching Marangoni off does not change the macroscopic foot. On this mesh the reported angle stays near 50° while the pool edge follows the heated footprint. The next run shrinks that footprint onto the wire.

## cal06 — tight spots, stopped early

`launch_cal06.sh` was stopped at t = 0.10 s. The pool was only 1.0 mm wide and Tmax was 2785 K, but the rear beam (axis hit z ≈ 1.2 mm) had already put the wire line at z = 2.14 mm and the plate section was ~0.03 mm². The liquid was a band on the wire, not a bead on the plate.

## cal07 — heat at the foot, stopped at 0.40 s

Command: `launch_cal07.sh`. Coarse mesh, 24 ranks. Wall clock 2157 s for 0.40 s.

Rear axis meets the wire at z ≈ 0.39 mm and the inner ray at z ≈ 0.87 mm; the outer ray hits the plate at x ≈ 0.56 mm. Front spots land at r ≈ 0.6 mm. Powers 300 + 300 + 400 W, spots 0.30 mm. Scan 3 mm/s, feed 22 mm/s (steady area 5.8 mm²). Marangoni off, force factor 4, plate window 70°/125°.

At 0.40 s the centerline metal (cold wire removed) peaks at 1.45 mm on both sides of the wire, at |x| ≈ 0.6 mm, then falls to 0.5 mm by |x| ≈ 2 mm. That is a mound with a skirt, the same height on the leading and trailing sides, not a round trailing cap that meets the plate steeply. The pool is 3.0 mm by 2.2 mm and still widening (1.0 mm at 0.08 s, 1.6 mm at 0.16 s, 2.2 mm at 0.36 s). Plate angle 53°, with 26 of 32 molten plate-line cells receding, so the 70° floor is still not held. The wire line is fully pinned at z = 1.30–1.61 mm. Tmax 2914 K.

Travel since the feed started is 1.05 mm, shorter than the pool, so the probe area (0.04 mm²) is not a track section. The mirrored metal volume rose by 6.1 mm³, which matches the 6.0 mm³ of wire fed in 0.35 s: the wire is entering the pool, and it has not yet been laid down as a bead. The open-cavity report is 2.66 mm³ centred at y = 1.11 mm, beside the wire. One mobile gas cell sits near the center plane at (x, y, z) ≈ (0.90, 0.07, 0.99) mm; that is a single 150 µm cell, not a notch under the contact line. Figures: `cal07_side_alpha_T.png`, `cal07_projection.png`, `cal07_iso_alpha.png`.

Verdict: tallest compact mound so far, and the fed wire is in the pool. The skirt is still spreading and the two sides are equal. Continuing these beams would widen the fillet. Not a radiograph match.

## cal08 — flank heat, 4 mm/s, full wire section

Command: `launch_cal08.sh`. Coarse mesh, 35264 cells, 24 ranks. Wall clock 2.3 h for 1.50 s.

The rear spot stays on the trailing flank (axis hit z ≈ 0.88 mm, 1/e² ray z ≈ 1.22 mm, outer ray z ≈ 0.55 mm). Front spots only kiss the plate at r ≈ 0.56–0.82 mm. Powers 160 + 160 + 420 W, spots 0.26 mm. Scan 4 mm/s, feed 20 mm/s, steady area 3.93 mm². Plate window 110°/150°, force factor 6, wire window 30°/90°, Marangoni off.

At 1.50 s the probed section is 3.78 mm² against the 3.93 mm² the wire feed should build, so the fed wire is in the track. The pool is 2.85 mm long and 1.61 mm wide, depth 0, Tmax 2901 K. On the centerline the trailing crest is 1.61 mm and the leading crest is 0.84 mm. Behind the wire the track holds about 1.3–1.5 mm out to x ≈ 4 mm, taller than the 1 mm wire, not the low ramp of cal03. The wire line is fully pinned at z = 0.99–1.61 mm, level with that crest. The plate angle is still 53°, and all 22 molten plate-line cells are receding, so the 110° floor is not what holds the foot. The compact beam does.

The open-cavity report is 2.37 mm³ centred at y = 1.15 mm, beside the wire. The y-projection does not show a gas pocket on the center plane. The run recorded 35 pinch-offs and no closure. One lack-of-fusion pore is locked, 0.23 mm, two cells, at (x, y, z) ≈ (1.70, 0.81, 0.54) mm. That is not the notch under the contact line. Comparison: `cal08_vs_radiograph.png`.

Verdict: the track finally takes the wire, and it is tall and trailing-heavy. It is flatter along the travel direction than the radiograph's round bulb, and the junction cavity is not resolved on the 150 µm mesh.

## cal09 — 37 µm at the wire, stopped early

`launch_cal09.sh` was stopped at t = 0.38 s (SIGTERM). Wall clock about 7.1 h. Same beams as cal08, `--wire-refine 2` (about 38 µm in x and y). The last field write is 0.25 s.

At 0.31 s the pool was 2.0 mm by 1.6 mm, Tmax about 2860 K, and the probed area was still 0.2 mm². The wire line sat at z = 0.84–1.45 mm and was only partly pinned. On the 0.25 s centerline the metal outside the wire reached 0.84 mm on the trailing side and 0.69 mm on the leading side, with the foot back at x ≈ 1.3 mm. That is a small steep mound, not yet cal08's tall track, and the mirrored metal volume had risen only about 2 mm³. The open cavity was a few mm³ and still off the center plane. Figure: `cal09_t025_side_alpha_T.png`.

Stopped so the trailing face of the wire can be given its own contact window. Not a radiograph match.

From 1:20 PM CT on 22 Oct 2026 the workstation is shared. Calibration runs use at most 12 MPI ranks and `nice -n 10`. On the refined mesh that rate was about 2.5×10⁻⁵ simulated seconds per wall second, faster than cal09's 24 ranks, and 0.40 s took 4.1 h.

## cal10 — trailing wire window

Command: `launch_cal10.sh`. Same beams and speeds as cal08. Front of the wire 25°/70°, trailing half 60°/140° within 90° of +x, cosine blend 30°, head frame. Plate window 110°/150°, force factor 6, Marangoni off. Mesh `--wire-refine 2` (about 38 µm, 57014 cells). 12 ranks, `nice -n 10`. Wall clock 4.1 h for 0.40 s.

The coarse screen (`launch_cal10_screen.sh`) ran on 24 ranks until `stopAt writeNow` at t = 0.123 s, then on 12 ranks to 0.15 s. At 0.15 s the wire line was at z = 0.99–1.30 mm and no wire cell was advancing, so the refined run was started. Figure: `cal10_screen_side_alpha_T.png`.

At 0.40 s the centerline metal outside the wire peaks at 1.76 mm just behind the wire and the leading crest is 0.84 mm. The trail falls to 0.69 mm by x ≈ 1.7 mm. The pool is 2.55 mm by 1.91 mm, depth 0, Tmax 2881 K. Travel since the feed started is 1.4 mm, shorter than the pool, so the probe area is not a track section. The mirrored metal volume rose by 4.4 mm³; the wire feed over 0.35 s is 5.5 mm³.

The wire line is at z = 0.84–1.91 mm, 6 of 13 cells pinned, one advancing and six receding, mean angle 41°. On the centerline the columns just behind the wire are solid from the plate up to 1.76 mm. The open-cavity report is 3.56 mm³ centred at (0.58, 1.03, 1.14) mm, beside the wire, and the closed volume is zero. The run recorded 169 pinch-offs and no closure. One lack-of-fusion pore is locked, one cell, 0.18 mm, at (x, y, z) ≈ (−0.33, 0.95, 0.23) mm. The plate angle is 64°, with 41 of 42 molten plate-line cells receding.

Verdict: the centerline behind the wire is solid metal. The gas the solver counts is still off the center plane, and no pinch-off stayed closed. The bead is tall on the trailing side and the line reaches that crest, and the mound is short. Comparison: `cal10_vs_radiograph.png`. Not a radiograph match.

## cal11 — continue cal10 to 1.0 s

`continue_cal11.sh` restarted `cases/wire_cavity_cal10` from 0.40 s to 1.0 s. Same beams, same 60°/140° trailing window, same 38 µm mesh. 12 ranks, `nice -n 10`. The continuation took 5.5 h. Travel from the feed start is 3.8 mm, longer than the 2.79 mm pool.

At 1.0 s the centerline trailing crest is 1.61 mm and the leading crest is 0.84 mm. Behind the wire the track holds about 1.0–1.3 mm out to x ≈ 3.5 mm. The probed section is 2.23 mm² against the 3.93 mm² feed area. The mirrored metal volume rose by 9.0 mm³; the wire fed in 0.95 s is 14.9 mm³. The wire line is at z = 0.84–1.76 mm, 9 of 28 cells pinned, none advancing. The plate angle is 56°, and all 77 molten plate-line cells are receding.

On the center plane at 0.8 s and 0.9 s a gas region sits behind the wire under the trailing metal, from about 0.4 mm to 1.6 mm up (`cal11_sideview.png`). By 1.0 s that column is metal again. What remains on the centerline is a few cells along the plate. The open-cavity report is 3.02 mm³ centred at (0.44, 1.10, 1.17) mm, beside the wire, closed volume zero. Pinch-offs 216, closures 0. One locked entrapment cell, 0.07 mm, sits in the plate. Comparison: `cal11_vs_radiograph.png`.

The tall white region under the bead on `cal11_sideview.png` is a non-wetted film. The plate angle is 56° and every molten plate-line cell is receding, because the 110° receding floor sits above that angle and the Young force pulls the metal off the plate. That is not the radiograph's cavity. The target is a wetted plate and small closed bubbles, about 0.05–0.3 mm, pinched off at the wire.

## cal12 — stopped immediately

`launch_cal12.sh` had started with the same 110°/150° plate window. It was killed at t = 0.006 s, before any field write. Continuing it would have regrown the gas film.

## cal13 — wet the plate

`launch_cal13.sh` keeps the cal10 beams, speeds, and 60°/140° trailing wire window. The plate window is 10°/40°. Refined mesh, 57014 cells, 12 ranks, `nice -n 10`. Wall clock 5.8 h for 0.60 s.

The plate line is wetting: 22 pinned, 17 advancing, 1 receding, mean angle 53°. The center plane inside the wire is metal (alpha ≥ 0.96) from the plate up to the top of the domain. A first rendering painted that column white because contouring leaves a value of exactly 1 unfilled; `cal13_sideview.png` was redrawn so that metal stays dark. Under the trailing bead a gas film one cell thick (z ≈ 0.23 mm) sits near world x = 1.0 mm at 0.40 s and near world x = 1.8 mm at 0.60 s. The metal under it is solid, 1100–1360 K, liquid fraction 0, continuous with the plate. It is not a bubble inside liquid. The trailing crest is 1.45 mm and the leading crest is 0.84 mm. The junction still holds an open gas notch beside the wire, from about 1.15 mm to 1.9 mm, not a closed bubble. The open-cavity report is 2.66 mm³ centred at (0.48, 1.09, 1.08) mm. Pinch-offs 48, closures 0. One locked lack-of-fusion patch, 0.31 mm, sits on the plate at z = 0.11 mm.

The plate itself never melts. The top plate cell stays near 1274 K from 0.3 s to 0.6 s, under the 1658 K solidus, and the pool depth is 0. The liquid starts about 0.4 mm above the plate. Conduction into the 300 K plate is real and smooth; there is not enough of it. Side view: `cal13_sideview.png`.

## cal14 — hot plate, cold wire

`launch_cal14.sh` is cal13 with the substrate initialised at 1100 K, including the substrate inlet. The wire stub, the wire inlet, the gas inlet and the radiation ambient stay at 300 K. Same beams, same 10°/40° plate window, same trailing wire sector. Refined mesh, 12 ranks, `nice -n 10`. Wall clock 6.3 h for 0.60 s.

The plate under the bead melts. At 0.60 s the center-plane plate is above the 1658 K solidus from about x = −1.1 mm to x = 1.7 mm, with a peak of 1873 K, and the pool depth is 0.4 mm. The plate line has no receding cells (21 advancing, 6 pinned, mean angle 55°). There is no gas film under the bead. The trailing crest is 1.76 mm and the leading crest is 0.84 mm.

No closed bubble persists. The porosity count is 0 at 0.60 s. A mobile one-cell pore, 0.06 mm, sat at z = 1.30 mm just behind the wire at 0.578 s and was gone by the end. Pinch-offs 68, closures 0. The largest closed volume in the run was 0.0006 mm³. The open-cavity report is still 2.84 mm³ beside the wire and is not the score. Side view: `cal14_sideview.png`.

## cal15 — steeper trailing wire window, faster scan

`launch_cal15.sh` keeps the 1100 K plate and the 10°/40° plate window. The trailing wire window is 110°/160° with a 10° blend, and the scan is 5 mm/s. Refined mesh, 12 ranks, `nice -n 10`. Wall clock 7.0 h for 0.70 s.

The plate stays molten (center-plane peak 1921 K, pool depth 0.56 mm) and the plate line has no receding cells. The trailing crest is 1.61 mm and the leading crest is 0.69 mm. The early notch, gas from about 0.4 mm to 1.9 mm at 0.10 s, has closed back to two cells at the wire top by 0.30 s and stays there. The Young force was already at its cap on cal14, so the higher receding angle did not deepen it. No bubble persists: porosity is 0 at 0.70 s. A mobile 0.09 mm, 3-cell pore at z = 1.30 mm was present at 0.697 s and gone at the end. Pinch-offs 46, closures 0. Side view: `cal15_sideview.png`.

## cal16 — oxygen surface tension on the cal14 bead

`launch_cal16.sh` returns to the cal14 speeds and the 60°/140° trailing window. Dissolved oxygen is 500 ppm, so `sigma(T, a_O)` replaces the linear law. The oxygen contact-angle table is removed after generation, leaving the 10°/40° plate window and the wire sector as written. Marangoni stays off. The neck is cooler than the pool surface, so adsorption lowers sigma there more than on the hot cap. Refined mesh, 12 ranks, `nice -n 10`, end 0.60 s.

The solver was killed at t = 0.438 s on 24 Oct 2026 (wall clock 3.6 h, log `cases/wire_cavity_cal16/log.laserWireDEDFoam`). Nothing was running on 26 Oct, and there is no cal17 directory. The last written field is 0.40 s.

At 0.40 s the plate is still molten (center-plane peak 1895 K) and the plate line has no receding cells (6 pinned, 20 advancing, mean 60°). The trailing crest is 1.61 mm and the leading crest is 0.84 mm. The wire line reaches 1.76 mm, but 24 of 36 cells are receding: the wire angle sits near 29°, under the 60° floor, same as cal14. `OxygenSigma` at the kill reports 500 ppm, sigma from 0.88 to 1.17 N/m. The open-cavity report is 2.95 mm³ beside the wire and is not the score. Side view: `cal16_sideview.png`.

No closed bubble is present at a finished end. The longest liquid-shelled pore still in the pool is 51 ms: 0.15 mm, 15 cells, shell fraction 1, z = 1.15–1.30 mm, from 0.382 s to 0.433 s, alive when the process stopped. Pinch-offs 29, closures 0. The largest closed volume in the cavity report is 0.0003 mm³.

## Scores at the restart

Same 10-point radiograph score as the other workstation: 2 if the trailing crest is 1.45–2.30 mm, 1 if it stands at least 0.35 mm above the lead, 2 if the wire line is pinned on that neck, 1 if the molten plate line is not receding, 2 if the substrate under the bead is melted and there is no gas sheet, 2 if a closed bubble of 0.05–0.3 mm is still in the pool at the end. A pore that has already vanished does not score. The gas at z ≈ 1.8 mm on the center plane is the notch against the wire, not a bubble and not a film under the bead.

| tag | t | score | trail / lead | plate | bubble in the pool |
| --- | --- | --- | --- | --- | --- |
| cal14 | 0.60 s | 6 | 1.76 / 0.84 mm | 0 receding, 1873 K | 0.17 mm, 22 cells, liquid shell, 112 ms, gone by 0.60 s |
| cal15 | 0.70 s | 6 | 1.61 / 0.69 mm | 0 receding, 1921 K | 0.11 mm, 34 ms, gone before the end |
| cal16 | 0.40 s | 6 | 1.61 / 0.84 mm | 0 receding, 1895 K | 0.15 mm, 15 cells, 51 ms, still present at the kill |

The wire-pin points stay at 0 on all three: the line reaches the crest and then recedes. None of these runs has a closed 0.05–0.3 mm bubble at its last sample.

`continue_cal16.sh` restarts the 0.40 s field to 0.70 s on the same 12 ranks. The binary is the one that wrote 0.40 s, so the 500 ppm bead is finished before the rear-beam dip is turned on. `launch_cal17.sh` is the next recipe if that pore does not stay: 100 ppm with `--oxygen-sigma-only`, and a trailing window of 15°/45° over 45° of +x, on the same 1100 K plate. The 60° floor cannot pin a 22–29° wire angle. 100 ppm is the level that held a score-8 dome on the other workstation; 500 ppm is the level that dropped their trail, and it has not dropped this refined bead by 0.40 s.
