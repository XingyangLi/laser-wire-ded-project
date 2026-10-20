# laser_wire_ded_project: laser wire-feed DED (stranded / Fe+Ni wire) in OpenFOAM

**New here?** Read **[START_HERE.md](START_HERE.md)** first — one folder, double-click bats, no Linux required.

Single-track laser wire DED simulation: a custom OpenFOAM.com solver (`laserWireDEDFoam`,
VOF + enthalpy-porosity + ray-traced laser + multi-component Fe/Ni tracers), a Python case
generator, post-processing scripts, a Windows GUI, the case setups of every run so far, and the
X-ray / EDS validation data for the Invar stranded-wire experiment (600 W, 160 mm/min).

Windows buttons live in `launch\` (double-click, or `.\launch\Name.bat` from this folder):

| Double-click | Does |
|---|---|
| `launch\Build_Solver.bat` | Rebuild solver → WSL `~/lwded_bin` |
| `launch\Build_Wiggle_Solver.bat` | Rebuild the zigzag solver → WSL `~/lwded_bin_wiggle` |
| `launch\Run_Case.bat` | Start a **new** case (default recipe = 3 mm Fe+Ni v2; will not touch the live v2 run) |
| `launch\Status.bat` | Progress / ETA |
| `launch\Open_in_ParaView.bat` | Sync + open ParaView |
| `launch\Open_in_Cursor.bat` | Open this folder in Cursor |
| `launch\Open_Studio.bat` | Model screen: geometry and parameters |
| `launch\Wiggle05_Start.bat` | 0.5 mm zigzag, 10 mm of travel |
| `launch\Wiggle10_Start.bat` | 1.0 mm zigzag, 10 mm of travel |
| `launch\Wiggle_Status.bat` | Progress of the two zigzag tracks |
| `gui\launch_gui.bat` | Older point-and-click run panel |

Solver binary after build: WSL `~/lwded_bin/laserWireDEDFoam` (see `scripts/pc/build_solver_wsl.sh`).

---------------------------------------------------------------------------------------------

## 1. Layout

```
laser_wire_ded_project/
  generate_case.py          case generator (stdlib only) -> writes an OpenFOAM case dir
  materials.py              material presets (316L, Fe, Ni, Invar36, SS304, IN718, Ti6Al4V),
                            Gao et al. paper configs, Fe-Ni liquidus/solidus table
  run_case.py               mesh + run + render driver (Linux/WSL)
  visualize.py              standard renders (3D, sections, track profile, summary.json)
  visualize_multicomp.py    Fe/Ni multi-component renders (composition, unmelted strands,
                            full-length build from the recording planes)
  compare_runs.py           side-by-side metrics of several runs
  requirements.txt          python packages for the viz scripts
  launch/                   Windows double-click buttons (each one calls scripts\pc or gui)
  solver/
    Allwmake, Allwclean
    laserWireDEDFoam/       solver source (*.C, *.H) + Make/{files,options}
  gui/                      tkinter run-control GUI (Windows -> WSL), see gui/README.md
  cases/<name>/             case SETUPS only: 0.orig, constant (no polyMesh), system,
                            Allrun, Allclean, case_params.json, FIXES.md,
                            run_log_head/tail.txt, checkMesh_tail.txt
  results/<name>/           small results: meltPool.dat, components.dat, summary*.json,
                            track_profile.csv, metrics tables
  validation/               X-ray + EDS measurements, annotated frames, metrics tables
  scripts/box/              run/status scripts used on the build box (absolute box paths;
                            reference only, edit paths before reuse)
  scripts/pc/               WSL run scripts + launch_wsl_job.ps1 + open_in_paraview.ps1/.bat
  docs/MODEL_NOTES.md       long-form model documentation
  docs/PARAVIEW.md          Windows ParaView + WSL OpenFOAM viewing
```

### Cases included (`cases/`)

| case | what | status of the original run |
|---|---|---|
| `gap_study_1mm`, `gap_study_2mm`, `gap_study_3mm` | **wire-substrate gap study**: `val3mm_fe_ni_v2` with the wire tip 1 / 2 / 3 mm above the plate (`--wire-gap`) and the new rigid-wire **stubbing** model with **wire buckling** (`--stubbing --wire-buckling`); 169,650 / 222,300 / 269,100 cells (gas layer raised for 2 and 3 mm). Metrics and run instructions: `cases/gap_study/README.md` | queued on the PC after v2 (`Gap_Study_Status.bat`) |
| `val3mm_fe_ni_v2` | as `val3mm_fe_ni_defocus` + **`--rigid-substrate 100 --stub-floor`** (no wire pushed into the plate), `--feed-scale 1.0` (see its `FIXES.md`) | started on the PC 2026-10-06 11:30 CT (WSL `~/laser_wire_ded_stranded/val3mm_fe_ni_v2`, ~13-14 h); smoke test: wire metal below the plate 0.0006 vs 0.019 mm3 at 0.02 s |
| `val3mm_fe_ni_defocus` | Fe+Ni 5-strand on Invar, **experiment settings** 600 W, 2.67 mm/s, WFS 18.2 mm/s, 3 mm track, **focus -1.5 mm, zR 1.2 mm**, tip touching plate, A_sub 0.35, A_wire 0.25, strand-k 0.4, unmelted-k 0.3, liquidusUnmixed 0.85 | was still running on the box at export (t = 0.69 / 1.125 s) |
| `val3mm_fe_ni_focus03_balled` | same fixes but focus +0.3 mm, collimated, A_sub 0.30, 50 um gap | stopped at 0.30 s: wire tip hung ~1.5 mm up and **balled** (kept as reference) |
| `val3mm_fe_ni_defocus_coarse` | 25 ms coarse sanity check of the defocus case | done |
| `val_exp_600W_160mmpm_fe_ni` | Fe+Ni 5-strand, experiment settings, full 10 mm track, old optics (focus 0, A 0.42) | generated, never run |
| `val_exp_600W_160mmpm_stranded` | 7-strand Invar on Invar, experiment settings, 10 mm, WFS 15.6 mm/s | generated, never run |
| `fe_ni_5strand_invar` | Fe+Ni 5-strand (Fe,Ni,Fe,Ni,Fe x 0.3 mm) on Invar, Transitional-R 600 W, 5.8 mm/s, WFS 52.2 mm/s, 5 mm | done (0.862 s) |
| `coarse_fe_ni_5strand_invar` | coarse version of the above | done |
| `full_transitional_r_stranded` | 7-strand Invar wire, Transitional-R, focus 0.5 mm (from WSL) | done |
| `full_transitional_r_stranded_contact` | 7-strand, focus 0, feed from t=0 (wire-pool contact fix) (from WSL) | done |
| `coarse_transitional_r`, `coarse_normal`, `coarse_lof` | solid 0.9 mm Invar wire on SS304, Gao et al. Table S1 conditions, coarse mesh | done |
| `full_transitional_r_solid_reference` | reconstructed setup of the protected solid-wire Transitional-R production run (older generator; see its REPRODUCE.md) | done (result kept in `C:\Users\dukyo\laser_wire_ded\results_keep`) |

The setups were written by the generator version that created them; regenerate with the current
`generate_case.py` using the options stored in each `case_params.json` if you want them to match
the current code exactly.

---------------------------------------------------------------------------------------------

## 2. Build the solver (WSL Ubuntu-24.04, OpenFOAM v2406)

```bash
# in WSL
source /usr/lib/openfoam/openfoam2406/etc/bashrc
cd /mnt/c/Users/dukyo/laser_wire_ded_project/solver      # or a copy inside the WSL home (faster)
./Allwmake                                               # wmake laserWireDEDFoam
which laserWireDEDFoam
```

* Default install target is `$FOAM_USER_APPBIN`
  (`~/OpenFOAM/<user>-v2406/platforms/linux64GccDPInt32Opt/bin`). **That directory already holds
  an older `laserWireDEDFoam` build** (used by `~/laser_wire_ded_stranded`, and possibly by other
  work under `~/laser_wire_ded`). The new solver reads every new keyword with a default, so old
  cases should still run, but if you want to keep the old binary untouched build to a separate dir:

  ```bash
  LWDED_APPBIN=$HOME/lwded_bin ./Allwmake
  export PATH=$HOME/lwded_bin:$PATH        # put first on PATH before running cases
  ```
* **Do not build directly on `/mnt/c`**: the Windows filesystem is case-insensitive, so the solver's
  `correctPhi.H` shadows OpenFOAM's `CorrectPhi.H` and the compile fails ("'CorrectPhi' was not
  declared"). Build from a copy in the WSL home, e.g. `scripts/pc/build_solver_wsl.sh`
  (rsync `solver/` to `~/lwded_v2/solver_build`, then `LWDED_APPBIN=$HOME/lwded_bin ./Allwmake`).
* Clean: `./Allwclean`.
* The solver was developed on the box against OpenFOAM.com v2412 and verified to compile against
  v2406 in WSL (see "Build check" at the bottom).

---------------------------------------------------------------------------------------------

## 2b. Single-wire track: contact-line pinning and porosity

The stranded / Fe–Ni cases are unchanged. Pinning and porosity are **off unless the case dictionary asks for them**, and the generator only writes those dictionaries with `--contact-pinning` and `--porosity`.

Two setups are in the tree:

| case | what it is |
|---|---|
| `cases/single_wire` | one solid 1.0 mm 316L wire, one vertical beam, side feed, contact-line pinning and porosity **on**, no planted pores. Coarse mesh (~0.15 mm), 3 mm of travel. This is the case to run locally when you want a real bead. It is a full melt-pool run (hours on a laptop, not a smoke test). |
| `cases/single_wire_demo` | the same physics on a tiny 2-D mesh (~150 cells), end time 30 ms, `--power-2d-factor 8`, plus `--pore-seed`. The seed makes the pore counter report one locked entrapment pore and one locked lack-of-fusion pore immediately. The run is the pipeline check (about a second here). |

### What was added

**Contact-line pinning** (`constant/meltProperties`, `contactLine{}`). The plate is meshed metal, so the bead/pool/gas triple line is inside the domain, not a boundary condition on `bottom`. While the metal at that line is liquid, the contact angle through the metal may lie anywhere between a receding angle (default 20°) and an advancing angle (default 90°). Inside that window the Young force is zero and a momentum sink holds the line on the substrate velocity: the line is pinned. Outside the window a localised Young force advances or recedes the line back to the nearer limit. As the metal at the line freezes, the allowed window opens to 0–180°, so a solidified bead stays at the angle it froze at and is carried with the plate. Unmelted wire is not treated as a wall, so the feed is not pinned. Field `contactState`: 1 hysteresis pin, 2 solidification pin, 3 advancing, 4 receding.

**Porosity** (`porosity{}`). Shielding gas is already the VOF gas phase. Gas that cannot reach the atmosphere (top, outlet, far side, wire inlet) is a pore:

- **gas entrapment** (type 1) — a closed bubble that is not a surface lack-of-fusion gap and not a still-hot keyhole;
- **lack of fusion** (type 2) — closed gas sitting on the plate and covered by deposited metal (the gap left when the contact line pins before the bead wets the substrate);
- **keyhole** (type 3) — a closed cavity whose neighbourhood is still near boiling or under recoil pressure. Recoil in this solver dents the surface but does not remove mass, so an *open* depression is not counted. A pore is tagged keyhole only after that hot cavity has closed.

Once the metal cells around the pore have a mean liquid fraction below `flLock` (0.35), the pore is locked (`poreMarker` 1, `alpha.metal` held at or below 0.05) so numerical diffusion cannot fill it. If the shell remelts, the lock releases. Evaporation still removes heat, not mass.

### Dependencies, build, run

Python 3 (standard library) for `generate_case.py`, `run_case.py` and `scripts/quantify_pores.py`. The solver needs **OpenFOAM.com v2406 or v2412**.

```bash
# build (WSL or Linux). Do not compile on a Windows mount: see section 2.
source /usr/lib/openfoam/openfoam2406/etc/bashrc   # or openfoam2412
cd solver && ./Allwmake
export PATH="$FOAM_USER_APPBIN:$PATH"              # or LWDED_APPBIN=$HOME/lwded_bin ./Allwmake

# short pipeline check (serial, well under a minute once the solver is built)
./scripts/run_single_wire_demo.sh                  # Allrun + quantify_pores.py --expect-demo

# or by hand
cd cases/single_wire_demo && ./Allrun 1
python3 ../../scripts/quantify_pores.py --case . --expect-demo

# the real single-wire track (no planted pores; long)
cd cases/single_wire && ./Allrun 4
python3 ../../scripts/quantify_pores.py --case .
```

Regenerate either case from the repo root (the command that matches `case_params.json`):

```bash
python3 generate_case.py --case cases/single_wire_demo --laser-config single \
  --wire-type solid --material 316L --dim 2d --dx 3e-4 \
  --upstream 2e-3 --downstream 3.5e-3 --substrate-thickness 1.2e-3 --gas-height 1.6e-3 \
  --power 1200 --power-2d-factor 8 --scan-speed 0.01 --wire-feed-speed 0.02 \
  --wire-diameter 1e-3 --feed-angle 55 --wire-gap 0.2e-3 --feed-start 0 --laser-ramp 5e-5 \
  --end-time 0.03 --write-interval 0.01 --max-co 0.5 --np 1 \
  --contact-pinning --porosity --pore-seed

python3 generate_case.py --case cases/single_wire --laser-config single \
  --wire-type solid --material 316L --resolution coarse \
  --power 1800 --scan-speed 0.01 --wire-feed-speed 0.02 --wire-diameter 1e-3 \
  --feed-angle 50 --wire-gap 0.2e-3 --feed-start 0 --track-length 3e-3 \
  --write-interval 0.02 --np 4 --rigid-substrate 100 \
  --contact-pinning --porosity
```

`--pore-seed` is only for the demo. It plants one gas bubble inside the plate and one gas gap under a solid cap so the counter and the lock run immediately. A production track should omit it and let pores appear only if the free surface actually closes one in.

### Outputs and how to view them

| file / field | meaning |
|---|---|
| `postProcessing/contactLine/contactLine.dat` | time, counts of molten / pinned / advancing / receding / frozen cells, mean contact angle, pinned length |
| `postProcessing/porosity/porosity.dat` | time, pore count by type, locked count, pore volume, volume fraction, mean and max equivalent diameter |
| `postProcessing/porosity/pores.dat` | one row per pore: id, type, locked flag, volume, equivalent diameter, centroid, cell count, shell liquid fraction |
| `contactState` | ParaView: where the triple line is pinned or moving |
| `poreMarker`, `poreType` | ParaView: locked pores and their class |
| `log.laserWireDEDFoam` | lines `ContactLine:` and `Porosity:` |

`python3 scripts/quantify_pores.py --case <case>` prints the last sample. `--expect-demo` checks the **whole history** of the short case: a locked entrapment pore, a locked lack-of-fusion pore, a molten contact line and a solidification-pinned line. On the 30 ms demo the planted pores lock immediately; once the pool (T well above the liquidus, contact angle inside the 20–90° window, most of the line pinned) remelts their shells, the lock releases and a cavity can disappear before the end time. That is the model, not a failed run. Equivalent diameter is the sphere with the same gas volume, `(6V/π)^(1/3)`. Volume fraction is pore volume / (pore volume + metal volume) on the mesh that was solved. The demo fraction is not a process prediction: the planted pores are large next to a 150-cell 2-D domain.

In ParaView, open `case.foam` (Decomposed Case if you used `mpirun`), colour by `contactState`, `poreMarker` or `poreType`. The usual melt-pool file `postProcessing/meltPool/meltPool.dat` is unchanged.

### Assumptions that matter

- Default angles (20° / 90°) are a wide hysteresis window for liquid steel on solid steel, not a measurement for one alloy pair. Change them with `--theta-receding` / `--theta-advancing`.
- Pinning acts where the free surface meets solid substrate or already-deposited metal. It does not pin the unmelted wire.
- A pore has to be topologically closed. An open keyhole depression is not a pore; this solver's recoil does not bore a vapour channel by removing mass.
- Locking a pore deletes the metal that numerical diffusion had pushed into it. That is intentional, and it is a small mass error equal to that diffusion.
- 2-D demo "volumes" are the extruded cell volumes (one cell in y). Use `cases/single_wire` for a 3-D bead.

## 3. Generate, mesh, run, visualize a case

Run everything inside WSL with OpenFOAM sourced. Cases are best run from a WSL-home directory
(not `/mnt/c`), because the solver writes many files.

```bash
source /usr/lib/openfoam/openfoam2406/etc/bashrc
mkdir -p ~/lwded_runs && cd ~/lwded_runs
cp /mnt/c/Users/dukyo/laser_wire_ded_project/*.py .

# 1) generate (stdlib only)
python3 generate_case.py --print  <options>              # derived values only, nothing written
python3 generate_case.py --case my_case <options> --np 8

# 2) mesh + initial fields + run (Allrun: blockMesh, topoSet, refineMesh, createPatch,
#    0.orig -> 0, setFields, setExprFields, decomposePar, mpirun laserWireDEDFoam)
cd my_case
MESH_ONLY=1 ./Allrun 8        # mesh + decompose only, to check the mesh
./Allrun 8                    # full run (8 MPI ranks)
# restart after a stop: mpirun -np 8 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1

# or use the driver:
python3 run_case.py --case my_case --np 8                 # mesh + run + render
python3 run_case.py --case my_case --smoke 50 --np 4      # 50-step sanity check

# 3) monitor
grep '^Time =' log.laserWireDEDFoam | tail -1
grep '^MeltPool\|^Components' log.laserWireDEDFoam | tail -2
tail postProcessing/meltPool/meltPool.dat       # columns are listed in its header line

# 4) visualize (needs the viz venv, see section 7)
~/vizenv/bin/python visualize.py           --case my_case --out viz/my_case
~/vizenv/bin/python visualize_multicomp.py --case my_case --out viz/my_case_mc   # Fe/Ni cases
```

Re-running a stored setup from `cases/`: copy the folder to WSL and run `./Allrun 8` (mesh and
`0/` are regenerated from `system/` and `0.orig/`).

Example: the current validation case (defocused, experiment settings):

```bash
python3 generate_case.py --case val3mm_fe_ni_defocus --laser-config transitional_r \
  --wire-type stranded --strands 5 --strand-layout ring --strand-diameter 0.3e-3 \
  --strand-materials Fe,Ni,Fe,Ni,Fe --substrate-material Invar36 \
  --power 600 --scan-speed 0.002667 --wire-feed-speed 0.0101 --feed-angle 90 \
  --focus-height=-1.5e-3 --rayleigh-length 1.2e-3 \
  --absorptivity-substrate 0.35 --absorptivity-wire 0.25 --alpha-hit 0.25 \
  --strand-gap 8e-5 --strand-k-factor 0.4 --unmelted-k-factor 0.3 \
  --liquidus-unmixed-threshold 0.85 --wire-gap 0 --feed-start 0 \
  --track-length 3e-3 --dx 1.2e-4 --refine-downstream 3e-3 --refine-halfwidth-y 1.3e-3 \
  --uniform-downstream 5.6e-3 --write-interval 0.02 --np 8
```
This reproduces `cases/val3mm_fe_ni_defocus` exactly (verified). Notes:
* `--wire-feed-speed` is the *nominal* WFS on the 0.9 mm solid-wire basis; with
  `--strand-feed-basis metal` (default) it is raised to the same metal volume rate through the
  strands (0.0101 -> 18.2 mm/s here). `case_params.json` stores both (`wire_feed_speed_nominal`).
* Negative values need `=` (`--focus-height=-1.5e-3`), otherwise argparse reads them as an option.
* `case_params.json` in every case is the authoritative record of the options used.

### Wire-substrate gap study (PC queue)

`python3 scripts/pc/gap_study_generate.py` writes `~/laser_wire_ded_stranded/gap_study_{1,2,3}mm`
(options copied from the v2 `case_params.json`, plus `--wire-gap`, `--stubbing`, `--write-interval 0.01`)
and copies the setups to `cases/`. `scripts/pc/gap_study_queue.sh` (installed in
`~/laser_wire_ded_stranded/gap_study_queue/`, launched hidden with `launch_wsl_job.ps1`) waits for v2,
benchmarks 1 x 8 ranks against 3 x 5 ranks, runs the cases with `scripts/pc/run_gap_case.sh`
(restart-safe), renders to `C:\Users\dukyo\laser_wire_ded\viz\gap_study_<n>mm` and runs
`scripts/pc/compare_gap_study.py` -> `viz\gap_study_compare`. Status: `Gap_Study_Status.bat`
(`scripts/pc/gap_study_status.py`); restart: `Gap_Study_Start_Queue.bat`. Smoke test of the stubbing
model: `scripts/pc/smoke_stubbing.sh`; of the buckling response: `scripts/pc/smoke_buckling.sh`.

---------------------------------------------------------------------------------------------

## 4. Main `generate_case.py` options

`python3 generate_case.py -h` lists everything. Units are SI (m, m/s, W, K).

| group | options |
|---|---|
| process preset | `--laser-config single\|normal\|lof\|transitional_r` (Gao et al. Table S1 triple-beam coaxial head), `--power`, `--scan-speed`, `--wire-feed-speed`, `--track-length` (sets end time), `--end-time` |
| beams | `--beam-angle` (deg from vertical, default 25), `--focus-height` (where the beams cross the wire axis; negative = below the plate), `--beam-radius` (1/e^2 waist), `--beam-direction +\|-`, `--profile gaussian\|tophat`, `--spot-radius` (single beam), `--laser-ramp` |
| **NEW optics** | `--rayleigh-length zR`: w(z) = w0 sqrt(1+(z/zR)^2), so a focus below the plate gives a larger, gentler spot on the plate and on the wire. Default None = collimated |
| **NEW absorption** | `--absorptivity` (both), `--absorptivity-substrate`, `--absorptivity-wire` (wire / every strand component), `--alpha-hit` (ray first-hit alpha threshold; lower = stronger shadowing of inner strands), `--no-shadowing` |
| materials | `--material`, `--wire-material`, `--substrate-material` (presets in `materials.py`) |
| wire geometry | `--wire-type solid\|stranded`, `--wire-diameter`, `--strands`, `--strand-layout auto\|ring\|centre`, `--strand-diameter`, `--strand-gap`, `--lay-length`, `--lay-direction`, `--strand-feed-basis metal\|wfs`, `--feed-reference-diameter`, `--max-wfs` |
| feed | `--feed-angle` (90 = vertical/coaxial), `--feed-side`, `--wire-aim`, `--wire-gap` (0 = tip touching the plate), `--feed-start` |
| **multi-component Fe/Ni** | `--strand-materials Fe,Ni,Fe,Ni,Fe` turns on tracers cFe/cNi + unmelted markers uFe/uNi; `--liquidus table\|mixture`; **NEW** `--strand-k-factor` (scales solid k of the strands: weaker strand-to-strand conduction), **NEW** `--unmelted-k-factor` (solver further scales k in never-molten wire cells), **NEW** `--liquidus-unmixed-threshold` (cell dominated >thr by one component keeps that component's Tsol/Tliq, so pure Fe stays at 1811 K until mixed), `--no-melted-follow-substrate`, `--no-wire-stubbing` |
| **NEW anti-sinking / feed** | `--rigid-substrate KFACTOR` (solver `rigidSubstrate{}`: Carman-Kozeny coefficient x KFACTOR, e.g. 100, in solid metal below the original plate surface, so the imposed feed cannot indent the solid plate with a cold wire tip), `--stub-floor` (components `stubFloorZ`: the original plate surface is always a support for the stubbing rule, so never-molten strands are not driven below the plate line), `--feed-scale` (multiplies the final WFS; default 1.0, check the metal mass balance before using it). All default off / 1.0 |
| **NEW gap / stubbing** | `--wire-gap g` (vertical distance plate top -> lowest point of the wire tip at t = 0; the generator raises the gas layer to g + 1.5 mm when needed and prints the beam-axis offset at the tip), `--gas-uniform-height`, `--stubbing` (solver `stubbing{}`: never-molten wire landing on solid support stops the feed, see `docs/MODEL_NOTES.md`), `--stub-response-time` (5e-4 s), `--stub-min-length` (default 1.9 dx), `--no-stub-drag`, `--wire-transfer-stats` (only the diagnostics file, feed unchanged), `--wire-buckling` (solver `stubbing{ buckling{} }`: the stalled solid wire column bows sideways beyond the Euler critical stall, elastica amplitude capped at `--buckle-max-amplitude` 1.5 diameters; `--buckle-critical-stall`, `--buckle-path-factor`, `--buckle-plane`, `--buckle-no-springback`). Default off |
| recording planes | `--record-x`, `--record-interval` (y-z planes stacked into a full-length build by `visualize_multicomp.py`) |
| mesh | `--resolution coarse\|medium\|fine` or `--dx`, `--wire-refine`, `--refine-halfwidth`, `--refine-halfwidth-y`, `--refine-downstream`, `--uniform-downstream`, `--domain-y auto\|half\|full`, `--dim 3d\|2d`, `--upstream/--downstream/--half-width/--substrate-thickness/--gas-height` |
| physics switches | `--no-marangoni`, `--no-recoil`, `--no-evaporation`, `--no-radiation`, `--no-convection`, `--buoyancy`, `--gas-viscosity-factor`, `--mushy-C`, `--preheat` |
| run control | `--np`, `--write-interval`, `--max-co`, `--print` |

Solver-side dictionary keywords added recently (written by the generator):
`laser{ beams{ ... rayleighLength } alphaHit }`, `wireMaterial{ absorptivity }`,
`components{ liquidusUnmixedThreshold unmeltedKFactor stubFloorZ ... }`,
`rigidSubstrate{ enabled zTop KFactor flMax }`,
`stubbing{ enabled writeStats wireFlMax supportFlMax contactDist minLength minContactCells responseTime dragContact useFloor diagRadius buckling{ enabled plane direction endCondition criticalStall gyrationRadius pathFactor absorbFraction maxAmplitude maxSlope maxLateralSpeed responseTime releaseTime springBack minColumnLength nBins } }`
(in `constant/meltProperties`). With a `stubbing{}` block the solver writes
`postProcessing/wireTransfer/wireTransfer.dat` (tip height, gap, bridging, hanging ball, stub events, stalled feed, buckling: compression, commanded and measured bow, tip offset).

---------------------------------------------------------------------------------------------

## 5. GUI (Windows)

`gui\launch_gui.bat` (Python 3.11 from python.org with tkinter). The GUI writes bash job scripts
into `gui/jobs/` and runs them in WSL Ubuntu-24.04 through `scripts\pc\launch_wsl_job.ps1`
(keeps the PC awake). It copies the repo-root `*.py` into the WSL work dir (default
`~/laser_wire_ded_stranded`), generates/meshes/runs there with the `laserWireDEDFoam` on PATH
(`$FOAM_USER_APPBIN`), and renders into `<project>\viz\<case>\` (git-ignored).

In this repo copy, `gui/app.py` reads the generators from the repo root (the old `gui/project/`
copies are gone) and uses the repo root as "Windows project root". The GUI does not yet expose the
newest options (`--rayleigh-length`, `--absorptivity-substrate/-wire`, `--alpha-hit`,
`--strand-k-factor`, `--unmelted-k-factor`, `--liquidus-unmixed-threshold`); use the CLI for those
or add them to `Params` in `app.py`. Rebuild the solver first (section 2) or the GUI runs the old
WSL binary, which does not know those keywords. The GUI refuses `~/laser_wire_ded` and
`~/laser_wire_ded_scan` as work dirs (they belong to other work) and `full_transitional_r*` case names.

---------------------------------------------------------------------------------------------


## 5b. View results in ParaView (Windows)

Use **Windows ParaView 6.2** against the WSL case over UNC. Linux `paraFoam` is not installed and not needed.

- Double-click Desktop **Open live DED case (ParaView)** (or `C:\Users\dukyo\laser_wire_ded\Open live DED case (ParaView).lnk`)
- Or: `scripts\pc\open_in_paraview.bat`  (default = live `val3mm_fe_ni_v2`)
- Any case: `scripts\pc\open_any_foam_case.bat <case-folder>`

After open: Properties -> **Case Type = Decomposed Case** for live `mpirun` jobs (`processor*`), check **internalMesh**, Apply. Color by `T` / `alpha.metal` / `cFe`. **File -> Reload Files** to pick up new times while the solver runs. Full notes: [`docs/PARAVIEW.md`](docs/PARAVIEW.md).
## 6. Model summary

Full details: `docs/MODEL_NOTES.md`.

* **Frame:** laboratory frame. Laser and wire nozzle fixed; the substrate (and the deposited bead)
  moves through the domain in +x at the scan speed (inlet at x-min, outlet at x-max). The wire
  enters through a `wireInlet` patch on the top boundary. Solid metal is moved rigidly by a
  Carman-Kozeny sink towards U_solid (substrate: v_scan; never-molten wire in the wire zone:
  feed velocity).
* **Flow / free surface:** two-phase incompressible VOF (metal / argon), MULES with interface
  compression (interFoam based), one metal density. Argon viscosity x20 by default.
* **Energy:** enthalpy-porosity melting/solidification (linear fl between Tsol and Tliq, latent heat
  with iterative fl update), k(fl), constant cp per material.
* **Laser:** ray-traced surface heat flux. Triple-beam coaxial head (Gao et al.), beams inclined
  25 deg; each ray deposits A * P into the first cell along the ray with alpha >= alphaHit
  (shadowing; inner strands are shaded by outer ones). Optional Gaussian beam caustic with
  Rayleigh length zR (defocus). Separate absorptivity for substrate and wire.
* **Surface forces:** CSF surface tension sigma(T) on liquid metal only, Marangoni stress,
  recoil pressure (Clausius-Clapeyron), evaporative cooling (Hertz-Knudsen-Langmuir), radiation and
  convection losses, gravity, optional Boussinesq buoyancy.
* **Stranded wire:** 1 centre + ring, or ring-only helical strands resolved in the VOF field
  (5 cells per 0.3 mm strand with `--wire-refine 1`), gas gaps between strands.
* **Multi-component Fe/Ni:** tracers cFe, cNi (substrate Invar = remainder) transported with the
  MULES flux (bounded vanLeer); properties by rule of mixtures; Tsol/Tliq from the Fe-Ni phase
  diagram in the local Ni content (pure Fe 1811 K, minimum ~1712 K near 60 % Ni, Invar ~1700/1725 K);
  unmelted markers uFe/uNi are cleared once fl > 0.5 -> anything with u > 0 in the build is wire
  that never melted. Strand contact conductance controlled through `strandKFactor` /
  `unmeltedKFactor` and the strand gap. `liquidusUnmixedThreshold` keeps pure-component cells at
  their own melting range until mixed.
* **Materials** (`materials.py`, authoritative, sources in its docstring): Invar36, Fe, Ni, SS304,
  316L, IN718, Ti6Al4V. Absorptivities are estimates (calibrated 0.42 baseline; validation runs use
  0.35 plate / 0.25 wire).
* **Outputs:** `postProcessing/meltPool/meltPool.dat` (pool L/W/D, Tmax, incident/absorbed power,
  wire tip z, bead h/w/area, penetration, dilution), `components.dat` (per-component unmelted
  volumes in wire / deposit / track), recording planes (`recordPlanes/*.raw`), fields
  `alpha.metal T liquidFraction U p_rgh cFe cNi uFe uNi meltHistory ...`.
* **Known limits:** single metal density (fragments don't sink/float), no dissolution kinetics
  (melting decided by cell T vs local liquidus), constant cp, evaporation removes heat but not mass,
  imposed incompressible feed can push unmelted strands into the substrate instead of
  stubbing/lifting (use `--rigid-substrate 100 --stub-floor`, new 2026-10-06), no multiple
  reflections / Fresnel absorption.

---------------------------------------------------------------------------------------------

## 7. Python environment for visualization (WSL)

```bash
sudo apt install python3-venv ffmpeg libgl1 libxrender1     # pyvista off-screen needs GL libs
python3 -m venv ~/vizenv
~/vizenv/bin/pip install -r /mnt/c/Users/dukyo/laser_wire_ded_project/requirements.txt
```
`generate_case.py`, `materials.py` and `run_case.py` need only the standard library.
The GUI needs only tkinter on Windows. (`~/vizenv` may already exist in WSL from the earlier runs.)

---------------------------------------------------------------------------------------------

## 8. Validation status (Invar stranded wire, 600 W, 160 mm/min = 2.67 mm/s, 10 mm track)

Data in `validation/` (`validation_metrics.md`, `xray_measurements.json`, `eds_measurements.json`,
`validation_side_by_side.png`, `annotated/`). The X-ray video itself is not in the repo (47 MB; the
original is on the Desktop: `Stranded_wire (laser power 600W, scanning speed 160 mm per min,
feeding amount 40 g).mp4`).

Experiment: conduction mode, wire fed vertically and kept in contact with the pool (no balling),
bead height 1.32 +/- 0.20 mm (X-ray; EDS cut 0.94 mm), pool length 3.33 +/- 0.18 mm, penetration
~0.1-0.4 mm (EDS interface ~0), unmelted Fe 5-12 % of the bead area in ~0.2 mm pieces **along the
whole track**. Feed: "40 g" does not match the bead size under any reading; WFS was set from the
bead volume (~15.6 mm/s for the 7-strand wire, 18.2 mm/s metal basis for the Fe+Ni wire) -
**still to be confirmed with the experiment record.**

| metric | experiment | 7-strand contact (5.8 mm/s) | Fe+Ni 5-strand (5.8 mm/s) |
|---|---|---|---|
| bead height | 1.32 mm | 1.57 mm | 1.65 mm |
| pool length | 3.33 mm | 3.17 mm | ~4.8 mm (tail) |
| penetration | ~0.1-0.4 mm | 0.55 mm | ~0.02 mm |
| unmelted Fe | 5-12 %, whole track | n/a | 13.7 %, start-up (first ~1.5 mm) only |

Runs at the experiment settings (3 mm Fe+Ni test):
* `val3mm_fe_ni_focus03_balled` (focus +0.3 mm, collimated): beams crossed the wire ~1-1.5 mm
  above the plate, the tip melted up there and **balled**; deposit formed by dripping. Stopped.
* `val3mm_fe_ni_defocus` (focus -1.5 mm, zR 1.2 mm -> spot 1.70 mm on the plate, 2.5 mm at
  z = +1 mm; tip starts on the plate): at t ~ 0.56-0.69 s the tip stays at the plate (~0.06 mm), no
  ball, pool ~2.7-3.0 mm long, 2.3-2.4 mm wide, 0.06-0.17 mm deep, Tmax ~2070-2100 K, 181 W of
  600 W absorbed. Penetration reads 0 so far; final comparison pending (run on the box was due to
  finish ~1 AM CT 2026-10-06; its results are not in this snapshot).
- **val3mm_fe_ni_defocus** (Oct 6, 2026; 600 W, 2.67 mm/s, WFS 18.2 mm/s, focus -1.5 mm, A_wire 0.25 / A_sub 0.35, 3 mm track): finished. Wire tip stays in the pool with no balling; penetration ~0.09 mm and unmelted Fe ~11.5 % (pieces ~0.2 mm) match the experiment, but bead height is ~0.85 mm vs 1.32 mm, pool is ~11-17 % long (3.7-3.9 vs 3.33 mm), unmelted Fe sits below the plate line and ~12 % Ni stays unmelted. See `results/val3mm_fe_ni_defocus/val3mm_defocus_vs_experiment.png`.

- **Re-check of the defocus run (Oct 6):** the metal inventory (meltPool.dat `metalVolume`) grew by
  7.18 mm3 in 1.125 s = 6.38 mm3/s vs 6.43 mm3/s fed, so **99 % of the fed metal is delivered**
  (the earlier "56 %" was a tracer/probe-based estimate). The low bead comes from (a) the 3 mm track
  being shorter than the 3.7 mm pool (no steady bead behind the pool yet; mid-track cross-sections
  1.6-2.1 mm2 vs 2.41 mm2 steady), (b) ~1 mm3 of wire metal pushed **into the solid plate** during
  the cold start (fl = 0 there; 0.75 mm3 by 0.2 s, down to z = -0.51 mm), (c) melt held ahead of the
  wire. A 1.8x feed would overshoot the X-ray bead (~2.4 mm2). Fix for (b): `--rigid-substrate 100
  --stub-floor` (`val3mm_fe_ni_v2`). A steady bead height needs a longer track (>= 6 mm).

### Open issues
1. **Fe strands surviving along the track.** The experiment keeps unmelted Fe over the whole 10 mm;
   the 5.8 mm/s Fe+Ni run only in the start-up zone. Fixes now in the model: lower wire
   absorptivity (0.25), stronger shadowing (alphaHit 0.25), weaker strand contact (strand-k 0.4,
   80 um gap, unmelted-k 0.3), pure-Fe liquidus until mixed (threshold 0.85). Needs checking for
   x > 1.5 mm in the defocus run (`visualize_multicomp.py`, `components.dat` "track" fractions).
2. **Penetration.** The 7-strand run penetrates too deep (0.55 mm); the Fe+Ni and defocus runs
   read ~0, while the experiment shows ~0.1-0.4 mm. Plate absorptivity / spot size need tuning
   between those.
3. **Balling vs focus and contact.** Focus above the plate + low strand conduction + weak plate
   pool -> the tip melts in the beam above the plate and balls. Focus below the plate (defocus with
   zR) and the tip starting in contact avoid it. Keep `--wire-gap 0 --feed-start 0` and a negative
   focus for the validation cases.
4. **Bead height** is 15-25 % too high at 5.8 mm/s and depends on the uncertain feed rate ("40 g").
5. Full 10 mm cases at the experiment settings (`val_exp_*`) are set up but have the old optics
   (focus 0, A 0.42); regenerate them with the defocus/absorption fixes before a long run
   (~32 h box / ~45 h PC on 8 cores).
6. GUI lacks the newest options (section 5), incl. `--rigid-substrate`, `--stub-floor`, `--feed-scale`.
7. Wire tracer inventory: in the defocus run sum(alpha (cFe+cNi) V) was 4.9 mm3 at the end vs
   ~7.2 mm3 fed (VOF metal is conserved, the tracers are not quite: clipping in `cWireEqn.H`).
   Affects composition / dilution numbers, not the bead size.

---------------------------------------------------------------------------------------------

## 9. Build check (2026-10-05, WSL Ubuntu-24.04, OpenFOAM v2406)

* `solver/` copied to `~/lwded_build_test`, built with
  `LWDED_APPBIN=~/lwded_build_test/bin ./Allwmake` against `/usr/lib/openfoam/openfoam2406`:
  **compiled and linked cleanly** (g++ -std=c++17, -DOPENFOAM=2406). Only `-Wunused-variable`
  warnings (createMeltFields.H / createComponents.H: nTCorr, flRelax, TminClip, TmaxClip,
  alphaMinFl, uMeltFl, laser*Power), no errors. No path changes were needed.
* Runtime smoke test with that binary: `cases/val3mm_fe_ni_defocus_coarse` (87,768 cells), `./Allrun 4`
  with endTime 2e-4 s: mesh, setFields, decomposePar and 41 solver steps ran to `End`, multi-component
  model, `liquidusUnmixedThreshold 0.85` and `unmeltedKFactor 0.3` were read, laser power balance OK.
* The existing `$FOAM_USER_APPBIN/laserWireDEDFoam` (Oct 3 build) was not replaced by this test.
  Run `./Allwmake` (default target) when you want the GUI / `~/laser_wire_ded_stranded` jobs to use
  the new solver.
