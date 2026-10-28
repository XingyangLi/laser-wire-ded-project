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

The solver was killed at t = 0.438 s on 24 Oct 2026 (wall clock 3.6 h, log `cases/wire_cavity_cal16/log.laserWireDEDFoam`). Nothing was running on the morning of 26 Oct. The last written field is 0.40 s.

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

A restart of that 0.40 s field ran until t = 0.461 s on 26 Oct 2026 (about 31 min on this continuation) and was then stopped. The next field write would have been 0.50 s, so the last saved field is still 0.40 s. The pore had come back (0.07 mm at 0.402 s, growing, liquid shell) and the center plane was still the filled cal14 neck. That continuation was holding all 12 ranks. Closed bubbles are no longer the target.

## Why the center plane is solid

The half mesh is a symmetry plane at y = 0 (`symmetry` is a `symmetryPlane`, every face point has y = 0). The front beams are a ±30° pair and the rear beam is on y = 0, so the heating is symmetric. Rays of a beam with y < 0 are folded with `y -> |y|` and each ray carries half the beam power, which rebuilds the missing half. The reported cavity centroid near y = 1.1 mm is not that fold, and it is not the centre of mass of a cavity that includes the symmetry plane.

On cal14 the wire-touching cavity (`cavityMarker`) was reconstructed at 0.2 s and 0.6 s. At 0.2 s, 0.19 mm³ of it lies in y < 0.2 mm and reaches down to z = 0.08 mm: the center plane does have a gas column behind the wire. At 0.6 s that column is gone below z = 1.30 mm. Only 0.08 mm³ remains on y < 0.2 mm, and it sits at z = 1.30–1.76 mm, the crown. Ninety-one percent of the marker volume is at y > 0.4 mm, and the gas that still reaches the plate is at y = 1.2–1.6 mm. The rear spot is 0.26 mm wide and aimed at (x, y, z) = (0.24, 0, 0.55) mm, so it heats the center-plane flank and closes the neck. The sides of the wire stay outside that spot, and the open volume lives there. A full-width copy would put the same groove at ±y. Its centroid would fall on y = 0 without putting gas on the center plane. That is what the other workstation's full-width centroid was measuring. Comparison of the center plane with the radiograph: `cal14_center_vs_radiograph.png`. At 0.2 s the gas behind the wire spans about z = 0.54–1.61 mm. At 0.6 s it is a cap at z = 1.45–1.61 mm.

## Thin gas slit on the trailing face

The radiograph feature to reproduce is a thin gas slit on the trailing face of the wire, on the center plane, under the notch and beside the fused dome. It is about 0.05 mm wide and about 0.4 mm deep (z about 1.2 mm down to 0.75 mm on the 1 mm wire), open where the melt meets the wire, and tapered to a point. Depth and width are expected to move with oxygen and with wire feed. The plate stays the cal14 plate: 1100 K, window 10°/40°, the same three beams, scan 4 mm/s. The runs stay 3D.

The mesh is the 150 µm track with three nested refinement passes in x, y and z on the trailing face only (`--neck-refine 3`, box x 0.32–0.90 mm, y 0–0.22 mm, z 0.55–1.45 mm). Each pass is two cells larger than the next, so every interface is a 2:1 jump. OpenFOAM v2406 names that third axis `normal` in `refineMeshDict`. The neck spacing is 19 µm. A mesh-only check of the 100 ppm case has 61402 cells, shortest edge 19 µm, maximum non-orthogonality 26° and maximum aspect ratio 4.7 (`checkMesh`: Mesh OK). The capillary step uses that spacing (`maxDeltaT` about 2.4×10⁻⁶ s). There is no full-height `--wire-refine`: stacking it on the neck passes would take the gap cells well below 19 µm and the time step with them. `dx_min` is the product of the wire-box levels and the neck levels when both are set.

The wire window and the trailing-sector window follow oxygen. `--oxygen-wire-angles` writes a 7-column table and `oxygenWireAnglesOnly`, so the solver applies the wire and trailing columns and leaves the plate at 10°/40°. The table is a stand-in for an oxide film, not a sessile-drop fit. The front of the wire stays wetting-to-intermediate. The trailing face is wetting at low ppm and non-wetting from 100 ppm up, so a wetted groove (apparent angle near 50°) sits inside the low-ppm window and below the high-ppm receding floor. Knots (ppm, wire receding/advancing, trailing receding/advancing): 0 → 25/70 and 25/70; 50 → 32/80 and 40/85; 100 → 42/100 and 90/125; 300 → 58/125 and 110/145; 1000 → 70/140 and 120/150. The trailing sector is 40° about +x with a 15° blend, so the oxide window is the center-back of the wire and not the side groove at y ≈ 1 mm.

Sahoo–Belton `sigma(T, a_O)` is on, and Marangoni is on, so `dσ/dT` can change sign as oxygen adsorption overtakes the clean-metal slope. Recoil is on. The wire inlet stays at 300 K: the slit sits on solid unmelted wire, and preheating that face would melt it. Dissolved-gas transport is not solved: the slit is an open meniscus, and the oxygen entry is the uniform melt activity `a_O = ppm × 10⁻⁴` already used by the surface-tension model.

`launch_slit_sweep.sh` is the full-track version of that neck: feed 24 mm/s at 50, 100 and 300 ppm (cal26, cal29, cal32), 4 ranks each, end 0.20 s. It was started and then stopped on 26 Oct 2026. After about an hour the three runs were still at t ≈ 0.014 s (about 4×10⁻⁶ simulated seconds per wall second), because they grow the bead from a cold wire on the 19 µm step. That is too slow to learn whether a slit can exist.

`launch_slit_smoke.sh` is the screen that replaces it. The domain is a few millimetres around the neck (x −2.2 to 3.2 mm, y 0 to 1.6 mm, z −0.8 to 2.3 mm) with the same 19 µm nested neck and the same cal14 beams. A hot bead and a molten plate cap are painted in, and a gas gap 0.06 mm wide is cut on the trailing face from z = 0.75 mm up through the free surface. Feed starts at t = 0. The run is 51 ms, written every 10 ms, 3 ranks, `nice -n 10`. Plate window 10°/40°.

| tag | ppm | feed | wire | what is being asked |
| --- | --- | --- | --- | --- |
| cal34 | 50 | 20 mm/s | 300 K | weak oxide, cal14 feed |
| cal35 | 300 | 20 mm/s | 300 K | strong oxide |
| cal36 | 300 | 28 mm/s | 300 K | strong oxide, faster feed |
| cal37 | 100 | 24 mm/s | 900 K | mid oxide, wire preheat |

The square gap is prescribed. A smoke that still has an open gap near 0.05 mm wide and ~0.4 mm deep after a few milliseconds is a slit the model can hold. The other workstation's cal113 / cal117 / cal140 bases are not repeated. `launch_cal17.sh` remains the older bubble recipe and is not part of this screen.

The score is the center-plane gap (`slit_metric.py`). A wall is two consecutive 0.02 mm bins of metal, so one cell on the wire surface does not count as closing the gap. Depth is only the thin run (width 0.015–0.15 mm). It persists when that run is open, at least 0.10 mm deep, and 0.02–0.12 mm wide. Wider than that is a bare trailing face. Zoomed neck views go next to the radiograph crop (`plot_slit_neck.py`). The video layout is `render_slit_video.py`: radiograph, center-plane side view, zoomed neck, metal dark, trailing side on the left, time in the title.

At 4 ms none of them holds a neck slit. The center plane through the neck is gas beside the wire, and the metal volume has not left the mesh (phase fraction stays near 0.41). cal34 and cal37 are a bare trailing face. cal35 and cal36 only have a 0.02 mm run, 0.05–0.08 mm deep, up at the crown (z ≈ 1.4 mm). There is no 0.05 mm × 0.4 mm slit to extend.

Those four were stopped. A square slot in a rectangular bead is outside the hysteresis window: once the wall jumps back, the advancing angle does not bring it in again. `launch_slit_curve.sh` replaces that initial field with a smooth pool and a taller trailing dome, and cuts a groove that is already the radiograph shape (0.06 mm at z = 1.20 mm, point at z = 0.75 mm, 0.28 mm wide in y). cal39 is 300 ppm at 20 mm/s. cal40 is 50 ppm at 20 mm/s. Both keep the wire at 300 K. Six ranks each, `nice -n 10`, write every 4 ms. `launch_slit_demo.sh` is the full cal14 domain of whichever of those holds the groove, 12 ranks, and it writes `results/calibration/slit_demo.mp4`.

A film is steady only when consecutive center-plane samples stay 0.03–0.08 mm wide and at least 0.25 mm deep for 4 ms or more, with the depth moving by at most 0.08 mm (`slit_metric.py` prints `stability:`). On a 19 µm mesh that width is two or three cells, which is also how thick a VOF interface is at `cAlpha` 1. The Young force used to switch from zero inside the window to the full value on the next cell. `launch_slit_stable.sh` separates that from the beam and from Marangoni/recoil, all on the 300 ppm curved groove, 4 ranks each, out to 16 ms. These fields are painted, not mapped.

| tag | settle | contact blend | neck compression | what the neck does |
| --- | --- | --- | --- | --- |
| cal39, cal40 | off | hard switch | cAlpha 1 | bare by 4 ms (300 and 50 ppm) |
| cal41 | 6 ms, then a 2 ms ramp | hard switch | cAlpha 1 | groove filled by 2 ms; still metal on the wire at 6 ms; bare by 10 ms, after the ramp |
| cal42 | off | 8° | ×4 inside the neck box | sharp and wetted at 2 ms; bare from 6 ms on |
| cal43 | 6 ms, then a 2 ms ramp | 8° | ×4 inside the neck box | a ~0.10 mm gas core at 2 ms, filled by 4 ms; still wetted at 8 ms as the ramp ends |

None of them is a steady film. `stability:` is "no steady film" on cal41, cal42 and cal43.

The split is between the beam and the capillary collapse, not between a noisy switch and a timestep. With the laser, Marangoni and recoil off, the 0.06 mm groove fills: metal is on the wire from 2 ms through 6 ms (cal41). Neck compression ×4 only delays that. cal43 still has a gas core at 2 ms and has lost it by 4 ms. The 8° blend does not hold a gap either. The capillary step stays near 1.4×10⁻⁶ s, so this is not a collapsed timestep. A 0.05 mm meniscus has a capillary time of a few hundredths of a millisecond, so 2 ms is already the equilibrium the surface tension wants, and that equilibrium is a wetted wire.

Turning the laser, Marangoni and recoil on clears that wetted face. cal41 stays wetted for the whole settle and is gas beside the wire by 10 ms, 2 ms after the ramp finishes. cal39, cal40 and cal42, with those terms on from the first step, are bare by 4–6 ms. Tmax on cal42 is about 3080 K with 131 W absorbed, so recoil is on at the hot spot. The contact-line report in that window is mostly a pinned or advancing plate line; it is not a wire line oscillating between pin and advance.

So a short settle wets the groove shut, a smoother switch does not keep it open, and stronger neck compression only slows the fill. On cal41 the wire line starts near 50° with the receding branch already on (the 85° floor of the old 300 ppm knot) and the angle never climbs to that floor: the groove is full by 2 ms. The Young force on those cells is already at its cap, so raising the floor does not push a 50° cell any harder. It does put a force on the cells that were pinned between 85° and the new floor.

`launch_slit_nonwetting.sh` is that test. The plate stays 10°/40°. The trailing face uses the table above. All four keep the 8° blend and neck compression ×4, the curved groove, wire at 300 K, feed 20 mm/s, 3 ranks each, `nice -n 10`. The painted center-plane mouth is 0.057 mm on the narrow cases and 0.114 mm on cal46. They were stopped once the 4–6 ms side planes were in: nothing in the neck was still a film, so the remaining run to 16 ms would not have changed the score.

| tag | ppm | trailing window | groove mouth | laser, Marangoni, recoil | what the neck does |
| --- | --- | --- | --- | --- | --- |
| cal44 | 300 | 110°/145° | 0.06 mm | off | metal on the wire by 2 ms; only a 0.02 mm crown wisp at 6 ms (z 1.38–1.48 mm) |
| cal45 | 300 | 110°/145° | 0.06 mm | on | bare trailing face at 2, 4 and 6 ms |
| cal46 | 300 | 110°/145° | 0.12 mm | off | same as cal44: the resolved gap is metal on the wire by 2 ms |
| cal47 | 50 | 40°/85° | 0.06 mm | off | a capped 0.07 × 0.10 mm patch at 2 ms (z 1.08–1.18 mm); crown wisp only at 4 ms |

`stability:` is "no steady film" on all four. No depth reaches 0.25 mm, and no sample is both 0.03–0.08 mm wide and that deep. At 2 ms the 300 ppm wire line is still near 55–60°, with about half of the remaining wire cells on the receding branch, and the wire count has fallen from about 100 cells to about 15. The apparent angle never climbs to the 110° floor. The 50 ppm line sits near 40°, inside its window, and that groove is gone by 4 ms as well.

The 0.114 mm mouth is six cells on the 19 µm neck, so this closure is not the two-cell interface thickness. A 12–15 µm neck was not run: the wide groove already separates that from the angle, and it closed the same way. No full-domain demo was started.

`launch_slit_static.sh` asks whether a fixed trailing-face angle can hold a groove at all. Sahoo–Belton sigma stays at 300 ppm and the oxygen angle table is off, so the trailing window is one number: receding and advancing are both 140° (cal48, cal50) or both 160° (cal49). The sector blend and the Young-force blend are 0, the plate stays 10°/40°, and the laser, Marangoni and recoil stay off. cal48 and cal49 keep the 0.06 mm tapered groove. cal50 paints a 0.05 mm gas layer on the whole trailing half of the wire from z = 0.30 mm to 1.50 mm (the painted center-plane width is 0.057 mm from z = 0.70 mm to 1.25 mm). Four ranks each, `nice -n 10`, out to 6 ms.

Neither static angle holds a slit, and the film does not either. There is no minimum angle to map onto oxygen.

| tag | trailing angle | initial gas | neck |
| --- | --- | --- | --- |
| cal48 | 140°/140° | 0.06 mm groove | mouth closed by 0.5 ms (width 0.001 mm); crown wisp only at 2, 4 and 6 ms |
| cal49 | 160°/160° | 0.06 mm groove | same closure |
| cal50 | 140°/140° | 0.05 mm film on the trailing half | mouth closed by 0.5 ms; crown wisp only at 2–6 ms |

`stability:` is "no steady film" on all three. The wire line starts near 50° (cal50 near 61°) with almost every cell on the receding branch, so the force is trying to drive the angle up to 140° or 160°. The mean falls toward 25–45° while the count falls from about 105 cells to a handful by 2 ms. It never reaches the set angle.

`WireForce:` is the neck check in the solver log. `touch` is an interface cell within one cell of the wire surface; `touchForced` is one of those that carries a Young force. `inBand` is inside the acceptance radius R+1.75h (about 33 µm on this mesh) and `beyond` is an interface the band ignores. `missGas`, `missLiq` and `missWire` are in-band cells dropped for a missing neighbour. `atCap` hit the 2σ/h² clamp. `sink` is the velocity sink, which is on only inside the hysteresis window. A static angle has no window, so the sink is only the dozen cells whose apparent angle is already exactly 140°. There is no velocity cap on the force (`velCap none`). The tangent test does not drop the force (`noTan` 0). `pYoung` is |F|·h and `pCap` is 2σ/w at the center-plane mouth (z = 1.10–1.30 mm).

On cal48 at the first step, with the painted mouth still open at 0.058 mm: 1350 cells touch the trailing face and 93 of them carry a force. 1238 in-band cells are dropped because they have no liquid-metal neighbour, 209 because they have no unmelted-wire neighbour, and 432 interface cells sit outside the 1.75h band. 69 of the 93 forced cells are at the 2σ/h² cap. pYoung is 1.21×10⁵ Pa and pCap is 4.04×10⁴ Pa, so the force on a triple-line cell is about three times the capillary pressure of that mouth. By 2 ms the mouth is closed, the trailing line is 8 cells, and pYoung has fallen to 2.4×10⁴ Pa. The same pattern is on cal49 and on the film. The cells that actually touch the wire along the groove are mostly gas against solid wire, three cells away from the metal wall, so they never receive the angle.

The full-track trio was stopped before any side-plane write, so it has no slit depth. The mesh check on the small domain (cal35) is 34980 cells, 19 µm neck, Mesh OK. The square slit box had selected 1448 cells before the wire cylinder restored its own interior.

`launch_slit_wall.sh` separates the missing wall from the mesh size. Same slab, same 300 ppm Sahoo–Belton sigma, laser, Marangoni and recoil off, plate window 10°/40°, out to 6 ms, 12 ranks, `nice -n 10`.

(A) The wire is cut out of the mesh (`subsetMesh` on the complement of a 0.5 mm cylinder from z = 0.05 mm upward). The new patch `wireWall` is a wall, 1443 faces. `alpha.metal` is `constantAlphaContactAngle` (theta0 through the metal, limit gradient). `U` is fixedValue `(0 0 -0.02)`, the feed velocity on a static mesh. `T` is 1700 K for z < 1.35 mm and 600 K above that. A 0.05 mm gas film is painted on the trailing face after the cut (center-plane width 0.057 mm from z = 0.70 mm to 1.25 mm). The internal wire pin is off. 3 ranks each. cal51 is 140°. cal52 is 40°.

(B) cal53 keeps the cal48 wire (metal region, static 140°/140°, 0.06 mm groove, internal pin) and refines the neck four times, to 9.4 µm, in the box x 0.40–0.80 mm, y 0–0.18 mm, z 0.65–1.35 mm. 90742 cells, Mesh OK, 6 ranks.

The wall angle does change the neck, and it does not hold a slit. `stability:` is "no steady film" on cal51 and cal52.

| tag | wall angle | what the center plane does |
| --- | --- | --- |
| cal51 | 140° | at 2 ms a 0.040 × 0.075 mm open patch at z 0.78–0.85 mm; by 4 ms and at 6 ms no metal in the 0.08 mm band from z = 0.60 mm up (the pool has left the wall) |
| cal52 | 40° | by 2 ms the 0.50–0.58 mm band is metal from z = 0.60 mm to 1.30 mm, and it is still metal at 6 ms. The mouth gap in the solver log is 0.0007 mm from 0.5 ms through 6 ms |

140° does not keep a 0.05 mm film. The non-wetting wall drives the pool off the face. 40° closes the gap and the metal stays on the wall. The contact angle is being enforced. Neither state is the radiograph slit (0.03–0.08 mm wide, at least 0.25 mm deep, steady for 4 ms), so there is no oxygen-to-angle map and no change to how the lower end melts. Figure: `wall_fine_neck.png`.

cal53 does not hold the groove either. The painted mouth is 0.048 mm at the first step and 0.0005 mm from 0.25 ms onward. At 2 ms the center plane is metal on the wire from z = 0.60 mm to 1.20 mm, with a capped 0.020 × 0.050 mm wisp at z 1.25–1.30 mm. That sample already fails the film test, so later times could not accumulate 4 ms of a good film. The run was stopped at 2.3 ms. The step had stayed between 0.05 µs and 0.3 µs with a maximum Courant number near 0.4. Finer cells close the same groove faster than the 19 µm mesh. `stability:` is "no steady film".

The wall boundary condition does enforce the angle: 40° wets and stays wet, and 140° drives the pool off the wall onto a bare face. The 9.4 µm neck still fills the groove.

## Oxide skin

`launch_slit_oxide.sh`. Same slab and the same painted 0.05 mm trailing film as cal50 (static 140°/140°, plate 10°/40°, 300 ppm Sahoo–Belton sigma, angle table off, laser, Marangoni and recoil off, 19 µm neck, 12 ranks, `nice -n 10`, out to 6 ms). The skin is on from the first step. Strength is `min(ppm/300, 1)`, so 300 ppm is full strength. `muSkin` is an implicit viscosity on cells with `|grad alpha| h > 0.25`. `Kskin` damps every cell in the trailing shell (z 0.30–1.55 mm, within 0.10 mm of the wire). The radial velocity is removed. A scalar coefficient also holds the tangential velocity, so the shell stays put. The wire feed still wins inside the unmelted wire.

| tag | muSkin | Kskin | center plane |
| --- | --- | --- | --- |
| cal54 | 200 Pa·s | 1×10¹² | at 2 ms a 0.040 × 0.750 mm open film, z 0.55–1.30 mm; at 4 ms the crown from z = 1.05 mm up is bare and the metric depth is 0.050 mm |
| cal55 | 20 Pa·s | 1×10¹³ | open film at 2, 4 and 6 ms, width 0.040 mm, depth 0.750 → 0.650 mm. `stability:` drifting (depth change 0.10 mm, limit 0.08 mm) |
| cal56 | 20 Pa·s | 1×10¹⁴ | open film at 2, 4 and 6 ms, width 0.040 mm, depth 0.725 mm, z 0.55–1.28 mm, unchanged. `stability:` steady |

cal54 also ran at a time step near 0.1 µs because the Courant number sat on 0.4. cal55 and cal56 stay on the capillary step, about 1.2 µs. The mouth gap in the solver log stays 0.058 mm for the whole of cal56. Figure: `oxide_skin_slit.png`.

The recipe that holds is cal56. No gas-pressure support and no solid shell were run. The full-domain run with beams, Marangoni and recoil on is left to the other machine.

`launch_slit_oxide_sweep.sh` keeps the cal56 flags and changes one number. `ppmRef` stays 300, so the skin strength is `min(ppm/300, 1)`. Sahoo–Belton `sigma(T)` is evaluated at the same ppm. Feed runs stay at 300 ppm. Width is the metric width (0.02 mm bins). Depth is the range from 2 ms to 6 ms.

| tag | ppm | feed mm/s | width mm | depth mm | stability |
| --- | --- | --- | --- | --- | --- |
| cal57 | 50 | 20 | 0.040 | 0.600–0.725 | drifting |
| cal58 | 100 | 20 | 0.040 | 0.650–0.725 | steady |
| cal59 | 200 | 20 | 0.040 | 0.725 | steady |
| cal56 | 300 | 20 | 0.040 | 0.725 | steady |
| cal60 | 300 | 18 | 0.040 | 0.725 | steady |
| cal61 | 300 | 24 | 0.040 | 0.725 | steady |
| cal62 | 300 | 28 | 0.040 | 0.725 | steady |

Low oxygen does not close the slit. At 50 ppm the film stays 0.040 mm wide and open; the crown shortens, so the depth change is 0.125 mm and the metric calls it drifting. From 100 ppm up it is steady, and at 200 and 300 ppm the depth does not move. Depth is the same 0.725 mm at 18, 20, 24 and 28 mm/s.

## Growing skin and painted depth

That flat depth is the painted film. The uniform membrane is at full strength from the first step, so it holds whatever gas was painted. `launch_slit_oxide_depth.sh` uses the same slab, 300 ppm, 20 mm/s and 140° window, with `growth true`. Coverage starts at 0. On the exposed trailing face it rises at `(ppm/300) * (feed/0.020) / 0.5 ms` and is carried down with the wire. `Kskin` and `muSkin` in a cell are the full cal56 values times `min(coverage, 1)`. At 300 ppm and 20 mm/s the coverage reaches 1 in 0.5 ms. The painted film is 0.05 mm thick and ends at z = 1.20 mm. Depth 0 leaves the dome metal on the wire: no film and no groove.

Width and depth are the metric values at 2, 4 and 6 ms. A zero is no thin gap.

| tag | painted mm | 2 ms, depth × width | 4 ms | 6 ms | stability |
| --- | --- | --- | --- | --- | --- |
| cal63 | 0.10 | 0.025 × 0.100 | 0 | 0 | no steady film |
| cal64 | 0 | 0 | 0 | 0 | no steady film |
| cal65 | 0.30 | 0.350 × 0.070 | 0.100 × 0.080 | 0 | no steady film |
| cal66 | 0.50 | 0.475 × 0.080 | 0.025 × 0.060 | 0 | no steady film |
| cal67 | 0.75 | 0.475 × 0.080 | 0.075 × 0.080 | 0.025 × 0.020 | no steady film |

No run holds a film. The 0.10 mm paint is a 0.025 mm wisp at 2 ms and is gone after that. The wetted neck never opens a thin gap: at 6 ms the metal fraction in x = 0.50–0.56 mm is 1.00 at z = 0.70 mm and 0.08 at z = 1.10 mm, so the lower neck stays wet and the crown is gas. The 0.30, 0.50 and 0.75 mm paints are still open at 2 ms. The two shorter ones still have about the painted depth (0.35 and 0.48 mm). The 0.75 mm paint has already shortened to 0.48 mm. By 6 ms the depths are 0, 0 and 0.025 mm. The solver mouth gap is about 0.001 mm once the coverage has saturated, so the membrane is locking a closed face. The time step sits on Courant 0.4 while that face is moving.

There is no steady depth for a new oxygen and feed table. The table above is the uniform skin, which preserves the paint. The growing skin does not select a slit, and it does not keep the painted depth either.

## Gas pressure, gas flux, and a feed-length skin

The uniform skin preserves the paint, so these smokes ask whether a cavity pressure, a gas supply, or a shorter skin can choose the depth. The metric is unchanged: width 0.03–0.08 mm, depth at least 0.25 mm, open, steady for at least 4 ms. Beams, Marangoni and recoil stay off. 12 ranks, nice 10, 6 ms. A zero in the table is no thin gap. The smears that remain are one cell wide (0.020 mm) and sit above the painted film.

`pSupport` is a face force on interfaces whose gas side faces the wire, and only while that gas is within 0.10 mm of the wire. `qRef` is a gas volume flux at the highest of those interfaces, times feed/20 mm/s. Both scale with `min(ppm/300, 1)`. The oxide skin is off for cal68–cal70. All three start from a 0.1 mm film at 300 ppm and 20 mm/s.

| tag | mechanism | 2 ms, depth × width | 4 ms | 6 ms | stability |
| --- | --- | --- | --- | --- | --- |
| cal68 | 5 kPa, no flux | 0.050 × 0.020 | 0.075 × 0.020 | 0.075 × 0.020 | no steady film |
| cal69 | flux 5 mm/s, aimed above the bead | 0.050 × 0.020 | 0.075 × 0.020 | 0.075 × 0.020 | no steady film |
| cal70 | flux 50 mm/s at the cavity | 0.075 × 0.020, capped | — | — | stopped |

5 kPa does not hold a 0.05 mm film. The capillary pressure across that gap is about 20 kPa, so the 1–5 kPa range is too small. cal69 fed the bare wire above the bead (contact height 1.79 mm) and never reached the film. cal70 feeds the cavity (contact height about 1.4 mm). At 2 ms the painted film is a capped one-cell gap, and the time step has fallen to 30 ns, so the run was stopped.

The other mechanism is the cal56 membrane, on from the first step, but only over a length `feed × tau` below z = 1.20 mm. Strength is full at 300 ppm. cal71 is a 0.1 mm paint and a 0.072 mm shell (18 mm/s × 4 ms). cal72 and cal73 use a 0.75 mm paint, which is longer than the shell, so a held depth could have been the shell length rather than the paint.

| tag | shell mm | painted mm | feed mm/s | 2 ms | 4 ms | 6 ms | stability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cal71 | 0.072 | 0.10 | 18 | 0.025 × 0.020 | 0.025 × 0.020 | 0.050 × 0.020 | no steady film |
| cal72 | 0.36 | 0.75 | 18 | 0.025 × 0.020 | 0.050 × 0.020 | 0.075 × 0.020 | no steady film |
| cal73 | 0.56 | 0.75 | 28 | 0.025 × 0.020 | 0.050 × 0.020 | 0.025 × 0.020 | no steady film |

The shell does not hold the film when it stops short of the lower lip. The lip is free, and the film closes through the damped region. The depth does not become the oxidised length, and it does not change from 18 to 28 mm/s. No oxygen and feed table follows, because none of these runs left a steady slit.

## Bare neck

These three start with no painted film and no groove. The initial field is a pool and a dome sitting on the wire, the wire feeding at 20 mm/s, travel speed 4 mm/s. Wire advancing/receding angles are 140°/40° on the wire and on the trailing sector. The plate stays 10°/40°. 300 ppm, 8 ms, 12 ranks. The metric is unchanged. A zero is no thin gap. "Bare face" means the crown is open gas, which is the wetted neck, not a slit.

cal74 carries oxide coverage on the free surface. It starts at 0, moves with the mixture flux, and grows at `(ppm/300)/1 ms` on interface cells. The damper acts only where gas faces the trailing wire, so it cannot freeze the wet neck. Laser, Marangoni and recoil are off. cal75 is the same skin with those three on. cal76 has no skin: only the moving contact line and the 4 mm/s travel.

| tag | mechanism | 2 ms | 4 ms | 6 ms | 8 ms | stability |
| --- | --- | --- | --- | --- | --- | --- |
| cal74 | surface skin, 140/40 | bare face | 0.025 × 0.020 | 0.050 × 0.020 | 0.025 × 0.020 | no steady film |
| cal75 | same skin, Marangoni and recoil on | bare face | bare face | bare face | bare face | no steady film |
| cal76 | travel speed, no skin | 0 | bare face | 0.025 × 0.020 | 0.025 × 0.020 | no steady film |

None of them generates a thin open slit. On cal74 the coverage does reach the cap (oxMax = 2) and about 170 trailing cells are damped, but the mouth gap stays at about 0.001 mm, so the skin is sitting on a closed face. The only thin signal is a one-cell wisp near z = 1.4 mm. Marangoni and recoil do not push a film open in 8 ms; the neck stays a bare face. At 4 mm/s the substrate moves 0.032 mm in 8 ms, and the wire feeds 0.16 mm. That does not entrain a gas film on the trailing face. The capillary number of the travel speed is about 2×10⁻⁵.

## Wire-wall drag

cal77 starts from the same bare neck and gives the wire a real wall. The mesh is static. The wall velocity is the feed, 24 mm/s downward. `alpha.metal` on that wall is `pinnedAlphaContactAngle` with a window of 40° receding and 140° advancing: inside the window the imposed angle is the apparent angle, so the Young force is zero and the line can stay stuck. `U` is `partialSlip` at the feed. The solver sets no-slip, and a momentum sink (`Kpin` 1×10¹² kg/m³/s), on the trailing contact only: the highest metal still touching the wall, and the 0.20 mm band under it. The rest of the wall slips, so the moving wire does not pump the pool. Plate window 10°/40°. Oxygen is Sahoo–Belton at 300 ppm, with the angle table off. Laser, Marangoni and recoil are off. 10 ms, 12 ranks. No painted film.

The contact starts at z = 1.20 mm with an apparent angle of 117°. About 25 faces stay pinned. The angle falls and remains inside the window (slip stays at 0 or 1).

| time | z of the wetted top | angle | pinned faces |
| --- | --- | --- | --- |
| 0 | 1.20 mm | 117° | 24 |
| 2 ms | 1.18 mm | 73° | 27 |
| 2.7 ms | 0.58 mm | 71° | 36 |
| 4 ms | 0.65 mm | 60° | 21 |
| 6 ms | 0.63 mm | 59° | 20 |
| 8 ms | 0.63 mm | 59° | 21 |
| 10 ms | 0.65 mm | 60° | 21 |

In 10 ms the wire itself moves 0.24 mm. The wetted top moves about 0.55 mm, most of it between 2 and 3 ms, then sits near 0.63 mm.

The center-plane gap tells the other half of that motion. At 2 ms the trailing face is still metal up to 1.15 mm, and the crown above that is open gas. At 4, 6, 8 and 10 ms the face is gas from 0.35 mm to 1.55 mm (the metric cap of 0.40 mm). The metric reads a bare face at every sample. No thin open slit appears, so the feed sweep (18/24/28 mm/s) and the oxygen sweep (50/100/300 ppm) were not run.

| tag | ppm | feed | window | 2 ms | 4 ms | 6 ms | 8 ms | 10 ms | stability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cal77 | 300 | 24 mm/s | 40°/140° | bare face | bare face | bare face | bare face | bare face | no steady film |

## Imposed line pin

cal78–cal86 start from the same bare neck. The trailing contact is a material point of the wire. On the first step the solver records the wetted top on the trailing face, z0 = 1.215 mm. After that the line height is `z0 + feed_z * t`, and the log line `LinePin:` follows that height. A two-cell shell on the trailing face is held at gas above the line and metal below it, and the shell velocity is the feed. Liquid that leaves a shell cell is passed to the next cell outward. That next cell is restored toward metal, chosen by radius, so the displaced coating stays beside the gap. Cells beyond it, and the pool below the line, are free. The wall angle stays 40°/140° at every ppm. Laser, Marangoni and recoil are off. 10 ms, 12 ranks. No painted film.

ppm sets the hold. `s = min(ppm/300, 1)` is the fraction of the alpha error and the velocity error removed after every alpha solve, and the fraction of `Kpin` (1×10¹² kg/m³/s). At 50 ppm, s = 1/6. At 100 ppm, s = 1/3. At 300 ppm, s = 1 and the shell is overwritten. Sahoo–Belton `sigma` still follows ppm. The angle window does not.

The line height and the shell are imposed. The gap from the wire surface (x = 0.50 mm) to the first metal is 0.039 mm at every sample below, which is the two-cell shell (the first metal sits at x = 0.539 mm). Depth grows with the feed: at 10 ms the wire has moved 0.18, 0.24 and 0.28 mm, and the measured run is 0.175, 0.250 and 0.300 mm. The extra is one 0.025 mm slice. The two-bin metric in `slit_metric.py` reads a one-cell wall as a bare face, so its width is 0.020 mm and its depth misses the top of the run, where the wall is a single cell. Both numbers are in the table. The steady test wants width 0.03–0.08 mm, depth at least 0.25 mm, and a change of at most 0.08 mm in depth over 4 ms. Depth here increases at the feed rate, about 0.05 mm every 2 ms, so none of the runs is a steady film. The gap stays open and keeps deepening.

The metal past the shell is free. At 10 ms it is one cell thick at the top of the gap (z ≈ 1.20 mm) and extends to about 0.65–0.69 mm lower down, where the line has reached the bead. That outer extent is the pool sitting against the imposed gap. The gap width itself stays 0.039 mm from the bottom of the run to the top.

50, 100 and 300 ppm produce the same gap at a given feed. s = 1/6 still puts the shell back on the target each step, and the momentum sink stays far above ρ/Δt, so the velocity stays at the feed. Oxygen changes the hold fraction and Sahoo–Belton `sigma`. It does not change the width or the depth in this smoke.

Figures: `linepin_feed_300ppm.png` (radiograph, then 18/24/28 mm/s at 300 ppm, 10 ms) and `linepin_ppm_24mms.png` (50/100/300 ppm at 24 mm/s, 10 ms).

| tag | ppm | feed | s | 2 ms | 4 ms | 6 ms | 8 ms | 10 ms | two-bin at 10 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cal78 | 300 | 18 mm/s | 1 | 0.025 × 0.039 | 0.075 × 0.039 | 0.100 × 0.039 | 0.150 × 0.039 | 0.175 × 0.039 | 0.020 × 0.125, open |
| cal83 | 50 | 18 mm/s | 1/6 | 0.025 × 0.039 | 0.075 × 0.039 | 0.100 × 0.039 | 0.150 × 0.039 | 0.175 × 0.039 | 0.020 × 0.125, open |
| cal84 | 100 | 18 mm/s | 1/3 | 0.025 × 0.039 | 0.075 × 0.039 | 0.100 × 0.039 | 0.150 × 0.039 | 0.175 × 0.039 | 0.020 × 0.150, open |
| cal79 | 300 | 24 mm/s | 1 | 0.050 × 0.039 | 0.100 × 0.039 | 0.150 × 0.039 | 0.225 × 0.039 | 0.250 × 0.039 | 0.020 × 0.225, open |
| cal81 | 50 | 24 mm/s | 1/6 | 0.050 × 0.039 | 0.100 × 0.039 | 0.150 × 0.039 | 0.225 × 0.039 | 0.250 × 0.039 | 0.020 × 0.225, open |
| cal82 | 100 | 24 mm/s | 1/3 | 0.050 × 0.039 | 0.125 × 0.039 | 0.150 × 0.039 | 0.225 × 0.039 | 0.250 × 0.039 | 0.020 × 0.225, open |
| cal80 | 300 | 28 mm/s | 1 | 0.075 × 0.039 | 0.125 × 0.039 | 0.175 × 0.039 | 0.225 × 0.039 | 0.300 × 0.039 | 0.020 × 0.275, open |
| cal85 | 50 | 28 mm/s | 1/6 | 0.075 × 0.039 | 0.125 × 0.039 | 0.175 × 0.039 | 0.225 × 0.039 | 0.300 × 0.039 | 0.020 × 0.300, open |
| cal86 | 100 | 28 mm/s | 1/3 | 0.075 × 0.039 | 0.125 × 0.039 | 0.175 × 0.039 | 0.225 × 0.039 | 0.300 × 0.039 | 0.020 × 0.275, open |

Entries are depth × width in millimetres, from the wire surface to the first metal. Every run reports `no steady film`.

## Trailing oxide angle

cal87–cal89 start from the same bare wetted neck. There is no painted film, no `linePin` and no `wireDrag`. Coverage starts at 0 and grows on the trailing wire surface toward `s = min(ppm/300, 1)`, with a 1 ms timescale. The first cell outside the wire grows even where it is metal. Cells farther out, up to 3 cells, grow while `alpha < 0.9`. Buried metal relaxes back toward 0. The field is not advected.

That coverage is generated by the exposure law. The map applied to it is imposed. The clean wall window is 10°/40°. Coverage blends it toward 40°/140°, so the saturated window is 15°/57° at 50 ppm, 20°/73° at 100 ppm and 40°/140° at 300 ppm. `sigma` is multiplied by `max(1 - 0.5*coverage, 0.1)` after the Sahoo–Belton value, so full coverage halves it. The tangential force from that oxide part of `grad(sigma)` is on. Thermal Marangoni, the laser and recoil stay off until 0.020 s. On trailing `wireWall` faces the no-slip fraction equals coverage and the reference velocity is the feed. `Kcontact` is not set, and alpha is not overwritten. Feed 24 mm/s, 10 ms, 12 ranks. In that time the wire moves 0.24 mm.

`cMax` reaches `s` in each run. The free surface does not become a thin open slit. The two-bin metric and the first-metal gap both find no run of width 0.03–0.08 mm. What forms is a bare trailing neck, sooner at higher ppm.

| tag | ppm | s | 2 ms | 4 ms | 6 ms | 8 ms | 10 ms | stability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cal89 | 50 | 1/6 | wetted neck | wetted neck | bare window | bare window | bare from 0.65 to 1.05 mm; metal still on the wire below 0.60 mm and above 1.15 mm | no steady film |
| cal88 | 100 | 1/3 | wetted neck | wetted neck | bare neck | bare neck | bare neck | no steady film |
| cal87 | 300 | 1 | wetted neck | bare neck | bare neck | bare neck | bare neck | no steady film |

At 2 ms every run still has metal on the trailing wire. The coating extends about 0.15–0.25 mm out from the face. At 300 ppm that metal is gone by 4 ms: cells with `alpha > 0.5` in the neck (z 0.55–1.35 mm, x > 0.45 mm) fall from 5904 to 22, then to 0, and stay there. The same count at 100 ppm is still 2808 at 4 ms and 0 from 6 ms on. The metal that leaves the neck remains in the domain, on the plate. At 50 ppm the count falls from 4018 to about 900. On the center plane, and in the volume, z 0.65–1.05 mm on the trailing side is gas at 10 ms. Metal remains on the wire below that window and above it. None of the three holds a gap whose depth follows the feed.

Figures: `oxideangle_300ppm_time.png` (radiograph, then 300 ppm at 2, 4 and 10 ms) and `oxideangle_ppm_24mms.png` (50, 100 and 300 ppm at 10 ms).

## Equilateral beams, then a true-wall pin

The bare-neck pin had no melt track. cal90 grows one with the lasers on, in the cal08 arrangement, with the three beam axes 120° apart: 60°, −60° and 180°. The half-domain `symmetryY` fold is on. All three beams stay in the dictionary, including the focus at y = −0.52 mm. Each listed power is halved in the half mesh and the negative-y rays are folded to |y|, so the −60° beam is the mirror of the +60° beam and is not dropped. The gaps are 120°, 120° and 120°. Powers are 160 W, 160 W and 420 W. The rear aim is on the trailing flank. Scan 4 mm/s, feed 24 mm/s from 0.05 s, coarse 150 µm mesh, 12 ranks, `nice -n 10`. No painted drop.

At 0.60 s the center plane is a bead fused to the plate. The trailing crest is 1.91 mm at x = 0.58 mm. The leading crest is 0.84 mm. The trailing foot reaches x = 3.28 mm. The half-mesh laser power is 370 W incident, 130 W absorbed, and the peak temperature is about 2920 K.

cal91 cuts that 0.60 s wire into a true wall (291 faces on this mesh) and turns on `linePin`. `pinWire` is off. The formed bead is the initial field, the feed runs at once, and the pin window is 20 ms. The line is recorded at z0 = 1.912 mm and then moves at the feed. At 20 ms, zLine = 1.435 mm, which is the 0.48 mm the wire travels. Below that height the face is metal. Above it the face is gas and the first metal is at x = 0.875 mm, 0.375 mm from the wire surface. That width is the two-cell shell on the 150 µm mesh. The bead outside the shell is the free surface from cal90. Figures: `cal90_t060_views.png` and `cal91_pin_views.png`.
