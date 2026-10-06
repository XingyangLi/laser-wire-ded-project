# Viewing OpenFOAM cases in ParaView (Windows + WSL)

You run the solver in **WSL** (OpenFOAM v2406). You view results in **Windows ParaView 6.2**, which already ships an OpenFOAM reader and uses your GPU. You do **not** need Linux `paraFoam`.

## One-click: live run

Double-click either:

- Desktop: **Open live DED case (ParaView)**
- `C:\Users\dukyo\laser_wire_ded\Open live DED case (ParaView).lnk`
- Or run: `scripts\pc\open_in_paraview.bat`

That opens the current live case:

`~/laser_wire_ded_stranded/val3mm_fe_ni_v2`  
via UNC `\\wsl.localhost\Ubuntu-24.04\home\dukyong\laser_wire_ded_stranded\val3mm_fe_ni_v2\case.foam`

## Open any case

```bat
scripts\pc\open_any_foam_case.bat <case-folder>
```

Examples:

```bat
scripts\pc\open_in_paraview.bat val3mm_fe_ni_defocus
scripts\pc\open_in_paraview.bat ~/laser_wire_ded_stranded/val3mm_fe_ni_v2
scripts\pc\open_in_paraview.bat C:\Users\dukyo\laser_wire_ded_project\cases\val3mm_fe_ni_v2
```

Drag a case folder onto `open_any_foam_case.bat` works too. The launcher creates an empty `case.foam` marker if it is missing (ParaView needs that file name; content can be empty).

## First time in the Properties panel

1. **Case Type**
   - **Decomposed Case** — while `mpirun` is running (you have `processor0`…`processor7`). Use this for live watches.
   - **Reconstructed Case** — only after you ran `reconstructPar` and have time folders at the case root (`0.02`, `0.04`, …).
2. Check **Mesh Regions → internalMesh**, then **Apply**.
3. Color by `T`, `alpha.metal`, `cFe`, `neverMeltedFe`, etc.
4. Use the time scrubber. While the solver is still writing: **File → Reload Files** (or the refresh icon) to pick up new times.

## Tips

- Keep WSL running (the live job already does). If UNC paths fail, open a WSL terminal once so the distro is awake.
- Do not open the same case for writing from two ParaView windows in a way that touches results; read-only viewing is fine.
- Repo `cases/` folders are **setups only** (no mesh / no time folders). For live or finished results, open the WSL run directory under `~/laser_wire_ded_stranded/`.
