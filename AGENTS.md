# Agents working in this repository

This is an OpenFOAM.com (v2406 or v2412) laser-wire DED solver, `laserWireDEDFoam`, plus `generate_case.py`. The workstation case is the three-laser vertical-wire track in `cases/wire_cavity`. Run it on the user's Linux workstation (`taosun01`), not on a small cloud VM.

## Build

OpenFOAM.com must be on the environment. The script sources it if needed and prints Ubuntu install commands (`openfoam2406-dev` or `openfoam2412-dev` from `dl.openfoam.com`) when it is missing. The `-dev` package is required for `wmake`.

```bash
./scripts/run_wire_cavity.sh --generate-only
```

That builds `solver/` with `Allwmake` and writes `cases/wire_cavity`. Do not compile on a Windows mount (`/mnt/c`): `correctPhi.H` shadows OpenFOAM's `CorrectPhi.H`.

`cases/single_wire` and `cases/single_wire_demo` stay as they are. Do not pass `--pin-wire` when regenerating them. Pinning the unmelted wire and the wake-cavity report are opt-in (`--pin-wire`, `--wire-cavity`).

## Run

```bash
./scripts/run_wire_cavity.sh              # nproc ranks
./scripts/run_wire_cavity.sh --np 16
./scripts/run_wire_cavity.sh --smoke      # coarse 3D, 8 ms, planted wake; optional check only
```

The full case is a few tenths of a second of melt-pool time on a 0.15 mm mesh (tens of thousands of cells, capillary time step of order 10⁻⁵ s). Expect hours. Do not start it on a 4-core VM. `--smoke` is the short pipeline check; it is not a prediction of the bead.

## Monitor

The solver log is `cases/wire_cavity/log.laserWireDEDFoam` (or `cases/wire_cavity_smoke/` for `--smoke`).

```bash
tail -f cases/wire_cavity/log.laserWireDEDFoam
grep -E 'Time =|ContactLine:|WireCavity:|Porosity:|End' cases/wire_cavity/log.laserWireDEDFoam
```

`ContactLine:` reports the substrate line and, when `pinWire` is on, `wire` and `zWire`. `WireCavity:` is `open`, `closed`, `mixed` or `none`, with volume and depth. `Porosity:` is the enclosed-pore counter (entrapment, lack-of-fusion, keyhole) and is separate from the open wake. A run that is still printing `Time =` is still going. `End` is the clean finish.

## Post-process

```bash
python3 scripts/quantify_pores.py --case cases/wire_cavity
python3 scripts/quantify_pores.py --case cases/wire_cavity_smoke --expect-wire-smoke
```

Read `postProcessing/contactLine/contactLine.dat` (wire columns start at `nWire`, including `zWireMax`) and `postProcessing/wireCavity/wireCavity.dat` (status, volume, depth below the contact line, downstream length). In ParaView open `case.foam`. Use a decomposed case if `Allrun` was given more than one rank. Colour `contactState` (5–8 are the wire line), `contactSupport` (2 = wire) and `cavityMarker` (1 open, 2 closed).

Physics, defaults and the beam table are in README section "Running on a workstation" and in `docs/MODEL_NOTES.md` under "Wire-surface pinning and the wake cavity".
