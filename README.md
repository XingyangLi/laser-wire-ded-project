# laser_wire_ded_project: laser wire-feed DED (stranded / Fe+Ni wire) in OpenFOAM

Single-track laser wire DED simulation: a custom OpenFOAM.com solver (`laserWireDEDFoam`,
VOF + enthalpy-porosity + ray-traced laser + multi-component Fe/Ni tracers), a Python case
generator, post-processing scripts, a Windows GUI, the case setups of every run so far, and the
X-ray / EDS validation data for the Invar stranded-wire experiment (600 W, 160 mm/min).

Snapshot exported 2026-10-05 from the build box (`/workspace/laser_wire_ded`) plus the stranded
cases from WSL `~/laser_wire_ded_stranded`. The detailed model notes from the box are in
[`docs/MODEL_NOTES.md`](docs/MODEL_NOTES.md) (paper basis, stranded wire, Fe/Ni model, limits).

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
  scripts/pc/               WSL run scripts used on this PC + launch_wsl_job.ps1
  docs/MODEL_NOTES.md       long-form model documentation
```

### Cases included (`cases/`)

| case | what | status of the original run |
|---|---|---|
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
* Building on `/mnt/c` works but is slow (NTFS through 9P) and leaves `Make/linux64GccDPInt32Opt`
  and `lnInclude` artifacts in the Windows tree (both git-ignored). A copy in the WSL home is faster:
  `rsync -a --exclude .git /mnt/c/Users/dukyo/laser_wire_ded_project/ ~/lwded_dev/`.
* Clean: `./Allwclean`.
* The solver was developed on the box against OpenFOAM.com v2412 and verified to compile against
  v2406 in WSL (see "Build check" at the bottom).

---------------------------------------------------------------------------------------------

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
| recording planes | `--record-x`, `--record-interval` (y-z planes stacked into a full-length build by `visualize_multicomp.py`) |
| mesh | `--resolution coarse\|medium\|fine` or `--dx`, `--wire-refine`, `--refine-halfwidth`, `--refine-halfwidth-y`, `--refine-downstream`, `--uniform-downstream`, `--domain-y auto\|half\|full`, `--dim 3d\|2d`, `--upstream/--downstream/--half-width/--substrate-thickness/--gas-height` |
| physics switches | `--no-marangoni`, `--no-recoil`, `--no-evaporation`, `--no-radiation`, `--no-convection`, `--buoyancy`, `--gas-viscosity-factor`, `--mushy-C`, `--preheat` |
| run control | `--np`, `--write-interval`, `--max-co`, `--print` |

Solver-side dictionary keywords added recently (written by the generator):
`laser{ beams{ ... rayleighLength } alphaHit }`, `wireMaterial{ absorptivity }`,
`components{ liquidusUnmixedThreshold unmeltedKFactor ... }` (in `constant/meltProperties`).

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
  imposed incompressible feed can push unmelted strands into soft substrate instead of
  stubbing/lifting, no multiple reflections / Fresnel absorption.

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
6. GUI lacks the newest options (section 5).

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
