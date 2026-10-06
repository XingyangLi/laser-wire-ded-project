# val3mm_fe_ni — short Fe+Ni validation with melting/pool fixes

Process: 600 W, 2.67 mm/s, WFS 18.2 mm/s metal, feed 90°, track 3 mm (end 1.125 s), feed_start 0.

| Fix | Old | New | How |
|---|---|---|---|
| 1. Wire absorptivity | 0.42 | **0.25** | `--absorptivity-wire 0.25` |
| 2. Stronger shadowing | alphaHit 0.5 (shadowing true) | **alphaHit 0.25** (shadowing true) | `--alpha-hit 0.25` |
| 3. Strand contact k | k_factor 1.0, gap 40 µm, unmeltedK 1.0 | **strand-k-factor 0.4**, **gap 80 µm**, **unmeltedKFactor 0.3** | `--strand-k-factor 0.4 --strand-gap 0.08e-3 --unmelted-k-factor 0.3` |
| 4. Fe liquidus until mixed | table always | **liquidusUnmixedThreshold 0.85** (keep Fe Tl=1811 K if max(c_i)≥0.85) | `--liquidus-unmixed-threshold 0.85` |
| 5. Shallower pool | A_sub 0.42, focus 0 | **A_sub 0.30**, **focus 0.3 mm** | `--absorptivity-substrate 0.30 --focus-height 0.3e-3` |

Post: report unmelted Fe/Ni only for deposited metal with x > 1.5 mm.
