# val3mm_fe_ni_defocus — defocused laser + tip-in-pool contact

Process: 600 W, 2.67 mm/s, WFS 18.2 mm/s metal, feed 90°, track 3 mm (end 1.125 s).

Keeps the melting/pool fixes from `val3mm_fe_ni_focus03_balled`, except focus/spot and contact:

| Item | focus03_balled | defocus (this) |
|---|---|---|
| Focus height | +0.3 mm | **-1.5 mm** (waist below plate) |
| Rayleigh length | none (collimated) | **1.2 mm** (`--rayleigh-length`) |
| Spot Ø at plate | 1.00 mm (1× w0) | **1.70 mm (1.70×)** |
| Spot Ø at z=+1 mm | 1.00 mm | **2.51 mm (2.51×)** |
| A_sub | 0.30 | **0.35** (larger spot → cooler pool) |
| Wire gap | 50 µm | **0** (tip at plate) |
| Feed start | 0 | 0 |

Other fixes unchanged: A_wire 0.25, alphaHit 0.25, strand-k 0.4, gap 80 µm, unmeltedK 0.3, liquidusUnmixedThreshold 0.85.

Reference balled run: `/workspace/laser_wire_ded/val3mm_fe_ni_focus03_balled` (stopped ~0.30 s, tip hung ~1.5 mm and balled).
