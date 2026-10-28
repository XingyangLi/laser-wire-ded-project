# Reference wire-cavity run (oxygen off)

Oxygen model off. Same three-beam 316L track as `scripts/run_wire_cavity.sh`, shortened so the solve fits on TaoSun-01 (i9-10920X, 24 threads, 62 GiB).

## Settings

| item | value |
|---|---|
| mesh | coarse 150 µm, `--wire-refine 1` (75 µm in x,y inside ±0.8 mm of the wire) |
| cells | 34 655 |
| domain | half (y ≥ 0), upstream/downstream 5 mm, half-width 3.5 mm |
| end time | 0.40 s (2.4 mm of travel at 6 mm/s) |
| write interval | 0.05 s, plus an XZ cut at y = 0.02 mm (`sidePlane`) |
| ranks | 24 (`mpirun --use-hwthread-cpus`) |
| wire | 1.0 mm, vertical, 30 mm/s, gap 0.15 mm, feed from 0.01 s |
| beams | 700 W at ±55° / 32°, 450 W at 180° / 22° (production defaults) |
| contact angles | plate 20°/90°, wire 25°/70° |

An 8 ms timing run on this mesh reached a steady rate of about 7.6×10⁻⁵ simulated seconds per wall second once the step had grown to ~1.1×10⁻⁵ s. That scaled to roughly 1.5 h for 0.40 s. The solve `ClockTime` was 5457 s (1.52 h). No divergence.

```bash
./scripts/run_wire_cavity.sh --np 24 \
    --case cases/wire_cavity_reference \
    --wire-refine 1 --end-time 0.40 --write-interval 0.05
```

## What the run produced

The solver's own pool at 0.40 s: length 1.60 mm, width 3.08 mm, depth 0.08 mm, Tmax 2171 K. The section it samples at x = 0.99 mm is 0.25 mm high and 3.37 mm wide, area 0.37 mm². The feed and scan would support about 3.9 mm² once the track is steady, so most of the wire has not become bead.

On the XZ cut through the wire (y = 0.02 mm) the plate is flat and the wire is still a solid column. Cells above the liquidus on that cut sit at z ≈ 2.7–3.3 mm, high on the wire, not in a pool on the plate. The wire contact line reported by the solver is at z = 3.07–3.35 mm, the top of the 3.5 mm gas space. The "cavity" is then the open gas under that line: about 10 mm³, 3.3 mm deep, 4609 cells, status open for the whole run after a few milliseconds. That volume does not grow as a notch behind a bead (see `reference_cavity_contact.png`).

Porosity at 0.40 s: 0 pores, 0 entrapment. `events.dat` has 0 pinch-off events and 3 closure lines near 0.06–0.08 s, each about 10⁻¹¹ m³, which do not survive.

## Comparison with the radiograph

The radiograph is a dome of bead, taller on the trailing side, with a notch where the melt meets the wire. This run does not look like that. There is a wide, shallow cap off the amount of metal the wire should have fed, and the contact line the cavity diagnostic uses is at the top of the wire rather than on a meniscus at the bead. The centerline picture (`reference_side_alpha_T.png`, trailing direction on the left) shows the wire and the plate, not a dome or a neck.

The oxygen sweep was not started. The angles and surface tension are not what this picture is missing.

## What to change before another run

The pool is heated under the front spots, about 1.1 mm off the centerline, and the wire tip is not melting into that pool.

- Move the beam aims inward (`--beam-aim-radii`, now 1.4, 1.4, 0.9 mm) so the spots meet the wire, and put more of the 1850 W on the centerline. The rear 450 W spot is a millimetre behind the wire and does not build the trailing dome.
- Hold the wire back until a pool exists (`--feed-start` is 0.01 s). A few tenths of a second of preheat would show whether the wire is arriving on solid plate.
- The 0.25 mm height against a 3.9 mm² feed area is unmelted wire, not a scan speed that is simply too high. After the wire actually melts, scan speed and power set the dome height.
- Leave the oxygen table alone until the contact line sits on the bead. The present wire line at z ≈ 3.3 mm is not the experimental neck, so sweeping 10–1000 ppm would move angles on the wrong line.
- A 10–20 µm neck still needs `--wire-refine 3 --wire-refine-z` near the wire. That mesh is hundreds of times the cell-steps of this run; it is not useful until the dome is in the right place.
