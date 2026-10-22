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

## cal10 — trailing wire window

Screen first (`launch_cal10_screen.sh`), then the refined run (`launch_cal10.sh`) if the line stays on the wire. Same beams and speeds as cal08. Front of the wire 25°/70°, trailing half 60°/140°, cosine blend 30°, head frame. Plate window still 110°/150°, Marangoni off. The refined mesh is `--wire-refine 2` (about 38 µm in x and y).
