# Viewing OpenFOAM cases in ParaView (Windows + WSL)

You run the solver in **WSL** (OpenFOAM v2406). You view results in **Windows ParaView 6.2**.
You do **not** need Linux `paraFoam`.

## Easiest: one-click

Double-click **Open_in_ParaView.bat** (Desktop or repo root / `scripts\pc\`).

That:

1. Reconstructs any new times in the WSL case
2. Copies them to `C:\Users\dukyo\laser_wire_ded_project\viz\paraview_live\`
3. Opens that folder in ParaView

Default case: `val3mm_fe_ni_v2`. Other case:

```bat
Open_in_ParaView.bat my_3mm_check
```

## In ParaView (first open)

1. **Case Type = Reconstructed Case** (this mirror is reconstructed)
2. Check **Mesh Regions → internalMesh**, then **Apply**
3. Color by `T` or `alpha.metal`
4. For a smooth surface (not blocky cells): **Filters → Contour**, array `alpha.metal`, value `0.5`
5. Re-run the bat anytime to pull newer times while the solver is still going

## Advanced: open WSL case directly

```bat
scripts\pc\open_any_foam_case.bat val3mm_fe_ni_v2
```

Then use **Case Type = Decomposed Case** while `processor0`… folders exist.

## Note

Repo `cases\` folders are **setups only** (no mesh / no time folders). Live and finished results live under WSL `~/laser_wire_ded_stranded\<name>\`.
