# gap_study_2mm: initial wire-substrate gap 2 mm (val3mm_fe_ni_v2 + gap + stubbing + wire buckling)

Everything as `cases/val3mm_fe_ni_v2` (600 W, 160 mm/min, WFS 18.2 mm/s metal basis, Fe/Ni 5-strand ring
wire on Invar, focus -1.5 mm, zR 1.2 mm, A 0.25/0.35, rigid substrate x100, stub floor, 3 mm track,
end 1.1249 s, 120/60 um mesh) except:

| item | value |
|---|---|
| `--wire-gap` | 2.00 mm: lowest point of the (flat-cut) wire tip at z = 2.00 mm above the plate top at t = 0 |
| feed | starts at t = 0 at 18.18 mm/s along the (vertical) wire axis; an unmelted tip would reach the plate at t ~ 111 ms |
| `--stubbing` | ON: rigid-wire stall while solid unmelted wire rests on solid support, `postProcessing/wireTransfer/wireTransfer.dat` |
| `--wire-buckling` | ON: while stalled, the solid wire column (stub contact pinned, wireInlet clamped) bows sideways (vertical wire: +y, normal to the scan) once the stalled feed exceeds the Euler critical end shortening (Euler S_cr = pi^2 r_g^2/(K^2 L): ~0.47 / 0.33 / 0.26 mm for the ~2.4 / 3.4 / 4.4 mm free columns of the 1 / 2 / 3 mm cases); amplitude = elastica take-up of the excess feed, capped at 1.5 wire diameters / 0.2 x free length (`bk*` columns in wireTransfer.dat) |
| gas layer | 3.50 mm (uniform 120 um cells up to 2.60 mm) |
| cells | 217284 (78 x 42 x (11+27) block, wire box refined) |
| `--write-interval` | 0.01 s (v2: 0.02 s) to see the early transfer |
| beams vs tip | coaxial: the wire axis is the axis of the 3-beam cone (focus 1.5 mm below the plate on that axis). At the tip height each beam axis is 1.63 mm from the wire axis (1.18 beam radii w = 0.85 mm from the wire surface, relative intensity 0.061); at the plate 0.70 mm |

See `cases/gap_study/README.md` for what is measured and how to compare the three cases.

* Mesh check (checkMesh after meshing, 2026-10-06): 222300 cells (generator estimate printed above is slightly lower). Lowest wire cell centre at 2 mm + half a cell.
* 2026-10-06 23:45: wire buckling (stubbing/buckling) added to constant/meltProperties before the solver start; solver ~/lwded_bin_gap_buckle.
