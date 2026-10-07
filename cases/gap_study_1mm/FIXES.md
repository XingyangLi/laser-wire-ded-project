# gap_study_1mm: initial wire-substrate gap 1 mm (val3mm_fe_ni_v2 + gap + stubbing)

Everything as `cases/val3mm_fe_ni_v2` (600 W, 160 mm/min, WFS 18.2 mm/s metal basis, Fe/Ni 5-strand ring
wire on Invar, focus -1.5 mm, zR 1.2 mm, A 0.25/0.35, rigid substrate x100, stub floor, 3 mm track,
end 1.1249 s, 120/60 um mesh) except:

| item | value |
|---|---|
| `--wire-gap` | 1.00 mm: lowest point of the (flat-cut) wire tip at z = 1.00 mm above the plate top at t = 0 |
| feed | starts at t = 0 at 18.18 mm/s along the (vertical) wire axis; an unmelted tip would reach the plate at t ~ 56 ms |
| `--stubbing` | ON: rigid-wire stall while solid unmelted wire rests on solid support, `postProcessing/wireTransfer/wireTransfer.dat` |
| gas layer | 2.50 mm (uniform 120 um cells up to 1.60 mm) |
| cells | 165822 (78 x 42 x (11+18) block, wire box refined) |
| `--write-interval` | 0.01 s (v2: 0.02 s) to see the early transfer |
| beams vs tip | coaxial: the wire axis is the axis of the 3-beam cone (focus 1.5 mm below the plate on that axis). At the tip height each beam axis is 1.17 mm from the wire axis (0.68 beam radii w = 0.85 mm from the wire surface, relative intensity 0.391); at the plate 0.70 mm |

See `cases/gap_study/README.md` for what is measured and how to compare the three cases.

* Mesh check (checkMesh after meshing, 2026-10-06): 169650 cells (generator estimate printed above is slightly lower). Lowest wire cell centre at 1 mm + half a cell.
