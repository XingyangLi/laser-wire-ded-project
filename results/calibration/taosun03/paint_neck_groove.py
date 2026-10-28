#!/usr/bin/env python3
"""Cut a tapered gas groove into the settled cal117 neck.

The fused dome stays. Cells outside the wire, inside the trailing groove,
that still hold metal are turned into cool gas. The groove width is 0 at
z = 0.75 mm, reaches --width-mm at z = 1.20 mm, and stays at that width
above the mouth, so the cut runs into the free surface instead of leaving
a closed bubble. The new wall is a 14 um tanh. Wire cells are left alone.

    paint_neck_groove.py CASE TIME --width-mm 0.06
    paint_neck_groove.py CASE TIME --width-mm 0.15 --dry-run
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neck_state as ns  # noqa: E402

WIRE_R = 0.50e-3
Z_TIP = 0.75e-3
Z_MOUTH = 1.20e-3
Y_GROOVE = 0.28e-3
WALL = 14e-6


def patch_internal(path, kind, values):
    path = Path(path)
    data = path.read_bytes()
    key = f"internalField   nonuniform List<{kind}>".encode()
    i = data.find(key)
    if i < 0:
        raise SystemExit(f"{path.name}: no binary internalField")
    rest = data[i + len(key):].lstrip()
    n_str, sep, tail = rest.partition(b"\n")
    n = int(n_str.strip())
    head_end = i + len(key) + (len(data[i + len(key):]) - len(rest)) + len(n_str) + len(sep)
    if not tail.startswith(b"("):
        raise SystemExit(f"{path.name}: internal list is not binary")
    width = 8 if kind == "scalar" else 24
    blob_at = head_end + 1
    raw = np.ascontiguousarray(values, dtype="<f8").tobytes()
    if len(raw) != n * width:
        raise SystemExit(f"{path.name}: replacement has {len(raw)} bytes, field has {n}")
    path.write_bytes(data[:blob_at] + raw + data[blob_at + n * width:])


def gap_width(z, mouth):
    if z <= Z_TIP:
        return 0.0
    if z >= Z_MOUTH:
        return mouth
    return mouth * (z - Z_TIP) / (Z_MOUTH - Z_TIP)


def groove_mask(cc, mouth):
    x, y, z = cc[:, 0], cc[:, 1], cc[:, 2]
    mask = np.zeros(len(cc), dtype=bool)
    # Half-domain, y >= 0. The groove is the centre-back of the wire.
    band = (y <= Y_GROOVE) & (y < WIRE_R) & (z > Z_TIP) & (x > 0.0)
    idx = np.flatnonzero(band)
    for i in idx:
        ys = float(y[i])
        xs = math.sqrt(max(WIRE_R * WIRE_R - ys * ys, 0.0))
        xx = float(x[i])
        if xx > xs and xx < xs + gap_width(float(z[i]), mouth):
            mask[i] = True
    return mask


def paint(case, tname, mouth, dry_run):
    from scipy.spatial import cKDTree

    case = Path(case)
    mesh = case / "constant" / "polyMesh"
    src = case / tname
    cc = ns.cell_centres(mesh)
    alpha = ns.read_internal(src / "alpha.metal", "scalar")
    temp = ns.read_internal(src / "T", "scalar")
    liquid = ns.read_internal(src / "liquidFraction", "scalar")
    if alpha is None or temp is None or len(alpha) != len(cc):
        raise SystemExit(f"{src}: alpha/T missing")
    radius = np.sqrt(cc[:, 0] ** 2 + cc[:, 1] ** 2)
    groove = groove_mask(cc, mouth)
    # Metal and interface mush inside the groove. Already-gas cells stay gas.
    cut = groove & (alpha > 0.05) & (radius > WIRE_R - 5e-6)
    alpha2 = alpha.copy()
    temp2 = temp.copy()
    alpha2[cut] = 0.0
    temp2[cut] = 600.0
    if liquid is not None and len(liquid) == len(cc):
        liquid2 = liquid.copy()
        liquid2[cut] = 0.0
    else:
        liquid2 = None

    metal = alpha2 >= 0.5
    inside_wire = radius < WIRE_R - 5e-6
    if cut.any() and metal.any() and (~metal).any():
        near_lists = cKDTree(cc[cut]).query_ball_point(cc, 40e-6, workers=4)
        near = np.fromiter((len(js) > 0 for js in near_lists), dtype=bool, count=len(cc))
        near &= ~inside_wire
        d_gas = np.zeros(len(cc))
        d_met = np.zeros(len(cc))
        d_gas[near] = cKDTree(cc[~metal]).query(cc[near], k=1, workers=4)[0]
        d_met[near] = cKDTree(cc[metal]).query(cc[near], k=1, workers=4)[0]
        signed = np.where(metal, d_gas, -d_met)
        alpha2[near] = 0.5 * (1.0 + np.tanh(signed[near] / WALL))
        # Deep groove gas stays cool. The liquid wall keeps its temperature.
        cool = cut & (alpha2 < 0.2)
        temp2[cool] = 600.0
        if liquid2 is not None:
            liquid2[cool] = 0.0
            liquid2[cut & (alpha2 >= 0.2)] = liquid[cut & (alpha2 >= 0.2)]
    alpha2[inside_wire] = alpha[inside_wire]
    temp2[inside_wire] = temp[inside_wire]

    print(
        f"groove mouth {mouth * 1e3:.3f} mm  cells {len(cc)}"
        f"  geometric {int(groove.sum())}  metal_cut {int(cut.sum())}"
    )
    rows = ns.film_rows(cc, alpha2)
    closed = [(z, w) for z, _x0, w, ok in rows if ok and w is not None]
    thin = [(z, w) for z, w in closed if 0.03e-3 <= w <= 0.08e-3]
    print(f"  closed_bins {len(closed)}  thin_bins {len(thin)}")
    for z, x0, w, ok in rows:
        if w is None:
            continue
        print(
            f"  z={z * 1e3:5.2f} mm  gas_x0={x0 * 1e3:.3f}"
            f"  width={w * 1e3:.3f} mm  {'closed' if ok else 'open'}"
        )
    if dry_run:
        print("dry-run, fields not written")
        return
    patch_internal(src / "alpha.metal", "scalar", alpha2)
    patch_internal(src / "T", "scalar", temp2)
    if liquid2 is not None:
        patch_internal(src / "liquidFraction", "scalar", liquid2)
    print(f"wrote {src}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("case")
    p.add_argument("time")
    p.add_argument("--width-mm", type=float, required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    paint(args.case, args.time, args.width_mm * 1e-3, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
