#!/usr/bin/env python3
"""Project alpha.metal along y, the way a side-view radiograph does.

Trailing (+x) is on the left. Dark is metal. A gas pocket beside the wire
shows up here even when the y = 0 slice cuts only the solid wire.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    import pyvista as pv

    case = Path(args.case)
    foam = case / "case.foam"
    reader = pv.OpenFOAMReader(str(foam))
    times = list(reader.time_values)
    if not times:
        raise SystemExit("no times in " + str(foam))
    reader.set_active_time_value(times[-1])
    data = reader.read()
    if isinstance(data, pv.MultiBlock):
        mesh = None
        for i in range(len(data)):
            block = data[i]
            if block is None:
                continue
            if "alpha.metal" in block.array_names:
                mesh = block
                break
        if mesh is None:
            raise SystemExit("alpha.metal not found in " + str(list(data.keys())))
    else:
        mesh = data
    pts = np.asarray(mesh.points)
    alpha = np.asarray(mesh["alpha.metal"])
    # Cell data may live on cells. OpenFOAMReader usually returns cell data
    # on a mesh whose points are the cell centres when the dataset is cell-only.
    if len(alpha) != len(pts) and "alpha.metal" in mesh.cell_data:
        mesh = mesh.cell_centers()
        pts = np.asarray(mesh.points)
        alpha = np.asarray(mesh["alpha.metal"])
    x = pts[:, 0]
    y = pts[:, 1]
    z = pts[:, 2]
    m = (x > -0.004) & (x < 0.004) & (z > -0.0004) & (z < 0.0032)
    x, y, z, alpha = x[m], y[m], z[m], alpha[m]
    # Bin. Half-domain y >= 0; mirror by using |y| already in the mesh.
    nx, nz = 160, 120
    xedges = np.linspace(-0.004, 0.004, nx + 1)
    zedges = np.linspace(-0.0004, 0.0032, nz + 1)
    # Transmission: exp(-k * integral alpha dy). Use the sum of alpha*dy.
    # Approximate dy by the bin of y is unnecessary if we sum alpha * cell
    # volume / (dx dz) later. Sum of alpha weighted by a y-extent proxy:
    # each sample represents one cell; use the count-weighted mean is wrong
    # for a projection. Sum alpha (each cell once) in each (x,z) bin.
    H, _, _ = np.histogram2d(x, z, bins=[xedges, zedges], weights=alpha)
    # Display with trailing (+x) on the left: flip x.
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    extent = [-xedges[-1] * 1e3, -xedges[0] * 1e3, zedges[0] * 1e3, zedges[-1] * 1e3]
    im = ax.imshow(
        H.T, origin="lower", extent=extent, cmap="gray_r", aspect="equal",
        vmin=0, vmax=max(1.0, float(np.percentile(H, 99))),
    )
    ax.set_xlabel("trailing  <-  x [mm]  ->  leading")
    ax.set_ylabel("z [mm]")
    ax.set_title(f"{args.tag}: metal projected along y (radiograph direction)")
    fig.colorbar(im, ax=ax, fraction=0.04, label="sum of alpha.metal")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"{args.tag}_projection.png"
    fig.savefig(dest, dpi=140, bbox_inches="tight")
    print("wrote", dest)

    liquid = alpha > 0.5
    above = z > 0.05e-3
    wire = (np.hypot(x, y) < 0.55e-3) & (z > 0.3e-3) & (alpha > 0.5)
    # Metal outside the wire column.
    bead = (alpha > 0.5) & above & ~((np.hypot(x, y) < 0.52e-3) & (z > 0.4e-3))
    if bead.any():
        print("bead z max mm", float(z[bead].max() * 1e3))
        print("bead x min/max mm", float(x[bead].min() * 1e3), float(x[bead].max() * 1e3))
        trail = bead & (x > 0.55e-3)
        lead = bead & (x < -0.55e-3)
        if trail.any():
            print("trail z max mm", float(z[trail].max() * 1e3), "n", int(trail.sum()))
        if lead.any():
            print("lead z max mm", float(z[lead].max() * 1e3), "n", int(lead.sum()))
    # Where is the gas next to metal, z in 0.2-1.5 mm, x in 0-2 mm (wake)?
    gas = alpha < 0.2
    wake = gas & (x > 0.3e-3) & (x < 2.0e-3) & (z > 0.15e-3) & (z < 1.5e-3) & (y < 1.6e-3)
    if wake.any():
        print(
            "wake gas n", int(wake.sum()),
            "x", float(x[wake].mean() * 1e3),
            "y", float(y[wake].mean() * 1e3),
            "z", float(z[wake].mean() * 1e3),
        )


if __name__ == "__main__":
    main()
