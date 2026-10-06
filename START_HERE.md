# START HERE — Laser Wire DED on your PC

Everything you edit lives in **one folder**:

`C:\Users\dukyo\laser_wire_ded_project`

You do **not** need to type Linux commands. Use the double-click buttons below (or the copies on your Desktop).

---

## 1. Open the project in Cursor

- Double-click **Open_in_Cursor.bat**, or
- In Cursor: **File → Open Folder** → `C:\Users\dukyo\laser_wire_ded_project`

Edit code under:

- `solver\laserWireDEDFoam\` — the OpenFOAM solver (C++)
- `generate_case.py`, `materials.py` — case generator
- `visualize.py`, `visualize_multicomp.py` — pictures after a run
- `gui\` — optional point-and-click run panel

---

## 2. After you change the solver code: rebuild

Double-click **Build_Solver.bat**

- Waits until the build finishes and tells you OK or FAILED
- New binary goes to WSL `~/lwded_bin/laserWireDEDFoam` (leaves the older GUI binary alone)

---

## 3. Start a NEW simulation

Double-click **Run_Case.bat**

- Default recipe: same settings as the current 3 mm Fe+Ni check (`val3mm_fe_ni_v2`)
- Default **new** case name: `val3mm_fe_ni_v2_copy` (it will **not** touch the live `val3mm_fe_ni_v2` run)
- Or from a Command Prompt:

```bat
cd C:\Users\dukyo\laser_wire_ded_project
scripts\pc\Run_Case.bat val3mm_fe_ni_v2 val3mm_fe_ni_v2b
```

That means: use recipe `val3mm_fe_ni_v2`, write results as case `val3mm_fe_ni_v2b`.

**Where results go**

| What | Where |
|------|--------|
| Live solver files | WSL `~/laser_wire_ded_stranded\<caseName>` |
| Pictures / logs | `C:\Users\dukyo\laser_wire_ded_project\viz\<caseName>` |

A full 3 mm run is roughly **11–15 hours** on 8 cores.

---

## 4. Check progress

Double-click **Status.bat**

- Default watches the live case `val3mm_fe_ni_v2`
- For another case: `Status.bat val3mm_fe_ni_v2b`

---

## 5. Look at the result in ParaView

Double-click **Open_in_ParaView.bat**

- Syncs the latest times to a Windows folder, then opens ParaView
- In ParaView: **Case Type = Reconstructed Case**, check **internalMesh**, **Apply**
- Color by `T` or `alpha.metal`
- For a smooth surface: **Filters → Contour**, array `alpha.metal`, value `0.5`

More detail: `docs\PARAVIEW.md`

---

## Optional: GUI

Double-click `gui\launch_gui.bat` for a form to set laser / wire / mesh and launch jobs. It uses the same project folder and the new `~/lwded_bin` solver.

---

## What NOT to touch

- Do **not** delete or overwrite `full_transitional_r*` or `results_keep`
- Do **not** point jobs at WSL `~/laser_wire_ded` or `~/laser_wire_ded_scan`
- Do **not** re-run into the live name `val3mm_fe_ni_v2` while it is still computing (use a new name like `val3mm_fe_ni_v2b`)
- Leave untracked `case_lwded\` alone unless you know you want it

---

## Example: “run another 3 mm Fe+Ni like the current one”

1. Wait until Status shows the current run is finished **or** just use a new name now.
2. Double-click **Run_Case.bat**, or run:

```bat
C:\Users\dukyo\laser_wire_ded_project\scripts\pc\Run_Case.bat val3mm_fe_ni_v2 my_3mm_check
```

3. Watch with `Status.bat my_3mm_check`
4. When done (or mid-run), `Open_in_ParaView.bat my_3mm_check`
