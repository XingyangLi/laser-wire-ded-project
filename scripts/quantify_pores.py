#!/usr/bin/env python3
"""Summarise contact-line pinning and porosity outputs from laserWireDEDFoam.

    python3 scripts/quantify_pores.py --case cases/single_wire_demo
    python3 scripts/quantify_pores.py --case cases/single_wire_demo --expect-demo

Reads, from the case directory:

    postProcessing/porosity/porosity.dat    time history of pore counts and volume fraction
    postProcessing/porosity/pores.dat       one row per pore per sample (id, type, size, centroid)
    postProcessing/contactLine/contactLine.dat

pore type: 1 gas entrapment, 2 lack of fusion, 3 keyhole.
The volume fraction is pore volume / (pore volume + metal volume) on the mesh
that was solved (a symmetry-plane case is not mirrored).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TYPE = {1: "gasEntrapment", 2: "lackOfFusion", 3: "keyhole"}


def _rows(path: Path):
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line.split())
    return out


def _last_time(rows):
    if not rows:
        return None
    return rows[-1][0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", default=".", help="OpenFOAM case directory")
    ap.add_argument("--expect-demo", action="store_true",
                    help="exit 1 unless the short demo produced a locked entrapment pore, "
                         "a locked lack-of-fusion pore, and a contact-line sample")
    a = ap.parse_args(argv)
    case = Path(a.case)
    por_path = case / "postProcessing" / "porosity" / "porosity.dat"
    pores_path = case / "postProcessing" / "porosity" / "pores.dat"
    cl_path = case / "postProcessing" / "contactLine" / "contactLine.dat"

    por = _rows(por_path)
    pores = _rows(pores_path)
    cl = _rows(cl_path)

    print(f"case: {case.resolve()}")
    if not por and not pores and not cl:
        print("no contact-line or porosity output found")
        print(f"  looked for {por_path}")
        print(f"  looked for {cl_path}")
        return 1

    if por:
        h = por[-1]
        # time nPores nLocked nEnt nLof nKey V vLock Vmetal vf dMean dMax
        print("porosity (last sample):")
        labels = ["time_s", "nPores", "nLocked", "nEntrapment", "nLackOfFusion", "nKeyhole",
                  "poreVolume_m3", "lockedVolume_m3", "metalVolume_m3", "volumeFraction",
                  "eqDiameterMean_m", "eqDiameterMax_m"]
        for name, val in zip(labels, h):
            print(f"  {name}: {val}")
    else:
        print("porosity.dat: not written")

    t_last = _last_time(pores)
    last = [r for r in pores if r[0] == t_last] if t_last else []
    print(f"pores at t = {t_last}: {len(last)}")
    for r in last:
        # time id type locked vol d cx cy cz nCells shell
        typ = TYPE.get(int(float(r[2])), r[2])
        locked = "locked" if int(float(r[3])) else "mobile"
        print(f"  id {int(float(r[1]))}  {typ}  {locked}  V={float(r[4]):.3e} m3  "
              f"d_eq={float(r[5])*1e3:.3f} mm  "
              f"centre=({float(r[6]):.3e}, {float(r[7]):.3e}, {float(r[8]):.3e}) m  "
              f"cells={int(float(r[9]))}  shell_fl={float(r[10]):.3f}")

    if cl:
        # time nMolten nPinned nAdv nRec nFrozen thetaMean ...
        c = cl[-1]
        print("contact line (last sample):")
        print(f"  time_s: {c[0]}")
        print(f"  nMolten: {c[1]}  nPinnedHysteresis: {c[2]}  nAdvancing: {c[3]}  "
              f"nReceding: {c[4]}  nFrozenSolidification: {c[5]}")
        print(f"  thetaMean_deg: {c[6]}  thetaMin_deg: {c[7]}  thetaMax_deg: {c[8]}")
        print(f"  lengthPinned_m: {c[9]}  lengthMobile_m: {c[10]}")
    else:
        print("contactLine.dat: not written")

    print("ParaView: colour by contactState (1 pin, 2 frozen pin, 3 advancing, 4 receding), "
          "poreMarker (1 = locked) and poreType (1 entrapment, 2 lack-of-fusion, 3 keyhole).")

    if a.expect_demo:
        # The pool can remelt a shell and vent a cavity before the end time, so the
        # check looks at the whole history, not only the last sample.
        locked_types = {int(float(r[2])) for r in pores if int(float(r[3])) == 1}
        problems = []
        if 1 not in locked_types:
            problems.append("no locked gas-entrapment pore in the history")
        if 2 not in locked_types:
            problems.append("no locked lack-of-fusion pore in the history")
        if not cl:
            problems.append("no contact-line samples")
        else:
            molten = sum(int(float(r[1])) for r in cl)
            frozen = sum(int(float(r[5])) for r in cl)
            if molten <= 0:
                problems.append("molten contact line was never flagged")
            if frozen <= 0:
                problems.append("solidification pinning was never flagged")
        if problems:
            print("demo check failed: " + "; ".join(problems))
            return 1
        print("demo check passed (history has a locked entrapment pore, a locked "
              "lack-of-fusion pore, a molten contact line and a frozen one)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
