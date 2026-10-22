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

Running. Front spots miss the wire and land at r ≈ 0.8 mm. Rear axis meets the wire at z ≈ 0.56 mm and the inner ray near z ≈ 1.1 mm. Powers 350 + 350 + 520 W, spot radius 0.32 mm. End time 0.20 s. See `launch_cal03.sh`.
