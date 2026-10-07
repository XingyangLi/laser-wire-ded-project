# track10mm_fe_ni: 10 mm validation track, wire metal forming the bead

Experiment: Invar stranded wire (here Fe,Ni,Fe,Ni,Fe x 0.3 mm on an Invar 36 plate), 600 W,
160 mm/min = 2.667 mm/s, 10 mm track (3.75 s), X-ray video + EDS long section (`validation/`).
Targets: pool length 3.33 +- 0.18 mm, bead height 1.32 +- 0.20 mm (X-ray; EDS cut 0.94 mm),
width ~2.6 mm (assumed), penetration ~0.08 mm (EDS ~0), unmelted Fe 5-12 % in ~0.19 mm pieces
along the whole track, tip in the pool, no ball. Mass balance: A* = A_metal WFS / v =
0.3534 mm2 x 18.18 mm/s / 2.667 mm/s = **2.41 mm2** steady bead cross-section (6.43 mm3/s fed).

## 1. Why the v2 bead looked too small (diagnosis, `scripts/pc/bead_volume_audit.py`)

`val3mm_fe_ni_v2` at t = 1.06 s (mm3): fed 6.804 | metal gain 6.758 (99.3 %) | deposit above the
plate 7.038 (incl. 0.28 shorter never-molten wire column) | holes below the plate 0.001 | wire metal
below the plate 0.19 | diffuse (alpha < 0.5) metal 0.36, alpha >= 0.5 cell count -0.4 % |
**wire tracer 3.628 (53.3 %), substrate tracer +3.130**.

* The fed metal IS in the bead: no loss through the top / outlet / VOF smearing, nothing pushed into
  the plate (rigidSubstrate + stub floor work).
* The bead was low because a 3 mm track is shorter than melt-ahead (1.25 mm) + pool (4.1 mm): the
  6.8 mm3 sat over x = -1.25...+3.75 mm (A(x) 1.6-2.3 mm2 under the wire, 1.4-1.95 behind it) for
  2.83 mm of travel, and the auto probe (3.43 mm) sat on the tapering start of the track (0.77 mm2).
  -> needs a track longer than pool + start transient: this 10 mm case.
* Tracer bug: legacy `cWireEqn.H` leaves c unchanged in cells with alpha <= 1e-3, through which metal
  flows every step; that destroyed 34-41 % of the inflowing wire tracer (budget below), i.e. the
  wire metal in the pool was relabelled as plate metal (wrong liquidus / dilution / unmelted
  fractions, composition renders showing the bead as substrate).

## 2. Changes (all default off, documented in `docs/MODEL_NOTES.md`)

| option | value | why |
|---|---|---|
| `--conservative-tracers` (components `conservativeTracers`, `tracerExtensionAlpha 0.01`, `tracerAlphaMin 1e-6`, `tracerBudget`) | on | tracer face values from a gas-cell extension (no stale c = 0 in gas), c = (alpha c)/alpha down to alpha = 1e-6; budget file `postProcessing/meltPool/tracerBudget.dat` incl. metal outflow per patch |
| `--wire-transfer-stats` | on | diagnostics only (tip height, bridge, hanging ball, would-be stub contacts) in `postProcessing/wireTransfer/`; feed is never stalled |
| `--stubbing`, `--wire-buckling` | **off** | a rigid feed stall triggers when unmelted strands touch the solid pool bottom, which would cut the delivered metal; the user asked for no buckling |
| `--track-length 0.010 --end-time 3.75` | 10 mm | whole experiment track; the bead reaches steady state after ~2 s, leaves the domain through the outlet (x = 6.5 mm) from ~2.4 s |
| `--refine-downstream 0.0042` (v2: 0.003) | 60 um box x = -0.77...4.97 mm, y +-1.3 mm | keeps the bead / strand fragments at 60 um past the pool tail and through the recording planes |
| `--record-x 0.0036,...,0.0048` -> 3.53, 4.01, 4.37, 4.73 mm | recording planes | just behind the ~3.1-3.5 mm pool tail (v2 default 2-5 mm had two planes inside the pool); the stacked build covers 0 to ~6.4 mm of the track, the rest is in the final field |
| `--write-interval 0.05` | 76 written times | ~31 MB each |
| `--wire-feed-speed 0.0101` | nominal 0.9 mm wire, metal basis -> 18.18 mm/s | identical feed to v2 (the old `recipe_val3mm_fe_ni_v2.sh` said 0.01818 -> 32.7 mm/s; fixed) |

Unchanged from v2: defocus -1.5 mm, zR 1.2 mm, w0 0.5 mm, 3 beams at 25 deg ('-'), A_wire 0.25 /
A_sub 0.35, alphaHit 0.25, strand-k 0.4, unmelted-k 0.3, liquidusUnmixed 0.85, tip on plate
(gap 0), feed from t = 0, rigidSubstrate 100, stub floor, dx 120 um / 60 um, full width, 8 ranks.
Mesh 78 x 42 x (11+18) = 95,004 block cells -> **184,962 cells** after the wire-box refinement.

## 3. Short-test evidence (restart of v2 @ 0.40 s, 0.40 -> 0.41 s, 4 ranks each, same binary)

| | legacy tracers | conservative tracers |
|---|---|---|
| metal fed (nominal) | 0.064 mm3 | 0.064 mm3 |
| metal gain in the domain | 0.064 (99.9 %) | 0.064 (99.9 %) |
| deposit above the plate (incl. wire-column change 0.002 / 0.008) | 0.066 | 0.072 = 0.064 + 0.008 |
| **wire-tracer gain** | **0.042 (64.7 %)** | **0.064 (100.1 %)** |
| substrate-tracer gain | +0.023 | -0.000 |
| budget: low-alpha skip | -0.0241 mm3 (-35.8 % of the 0.0672 mm3 wire tracer inflow) | +0.0002 |
| budget: clip + normalise | +0.0001 | -0.0002 |
| speed | 1.6 steps/s | 1.6 steps/s |

Metal entering = metal gained = deposit above the plate (within 1 %), and the tracer-tracked wire
volume = fed volume (100.1 %) with the fix.

## 4. Run

PC, WSL `~/laser_wire_ded_stranded/track10mm_fe_ni`, solver `~/lwded_bin_track10mm`, launched by
`scripts/pc/run_track10mm_fe_ni.sh` via `Track10mm_Start.bat` (hidden + keep-awake, restart-safe).
Status: `Track10mm_Status.bat`. Renders + comparison after the run: `C:\Users\dukyo\laser_wire_ded\viz\track10mm_fe_ni\`.
