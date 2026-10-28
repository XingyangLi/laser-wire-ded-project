# Wire-cavity calibration (oxygen off)

Goal: a 3D melt pool that looks like the side-view radiograph. A 1 mm vertical wire melts into a dome on the plate, taller on the trailing side, with a notch where the three-phase line sits on the wire near the top of the dome, and a gas cavity in the wake. Process parameters are free. Oxygen stays off.

The reference run (`results/reference`) aimed the beams outward. With shadowing on, each ray deposits on the first metal it meets, and those rays met the wire at the top of the domain (front-beam axis at z = 3.44 mm). The plate pool was wide and shallow and the wire contact line sat at z ≈ 3.3 mm.

Negative inclination reverses that. The beam moves inward as it descends, so the first hit is the foot or the flank instead of the top. `scripts/preview_beam_hits.py` prints that hit before a run.

Side views put the trailing side (+x) on the left. Scores are against the radiograph, not against the previous iteration.

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

From 1:20 PM CT on 22 Oct 2026 the workstation is shared. Every calibration run uses at most 12 MPI ranks and `nice -n 10`. The 24-rank refined rate (cal09) was about 1.5×10⁻⁵ simulated seconds per wall second, so 12 ranks are planned at about half of that, near 8×10⁻⁶ s/s: 0.10 s of refined time is a little over 3 h, and 0.30 s is about 11 h. After cal09 about 9 h of the 24 h budget remained, so the refined end time stays at or under 0.30 s and is cut further if the measured 12-rank rate would run past that. A coarse step that took about 15 min for 0.15 s on 24 ranks takes about half an hour on 12.

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

The recipe that holds is cal56. No gas-pressure support and no solid shell were run. No full-domain demo was started.
