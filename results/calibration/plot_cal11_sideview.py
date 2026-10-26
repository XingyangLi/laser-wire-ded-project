#!/usr/bin/env python3
"""Center-plane side view of cal11, trailing side on the left.

Reads the written side-plane samples (y = 0.02 mm). Does not touch the
running solver.
"""
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.tri import Triangulation

ROOT = Path("/home/xingyang/laser-wire-ded-project")
WIRE_R = 0.5  # mm


def load(case, time_name):
    path = case / "postProcessing/sidePlane" / time_name / "alpha.metal_xz.raw"
    rows = []
    with open(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            p = line.split()
            if len(p) >= 4:
                rows.append([float(p[0]), float(p[1]), float(p[2]), float(p[3])])
    a = np.asarray(rows)
    # Trailing (+x) on the left.
    x = -a[:, 0] * 1e3
    z = a[:, 2] * 1e3
    return x, z, a[:, 3], a[:, 1]


def beam_segment(az, th, aim_r_mm, aim_z_mm, z_hi=2.4, z_lo=-0.2):
    """Axis of one beam in plot coordinates (x flipped)."""
    phi = math.radians(az)
    thb = math.radians(th)
    sx, sy = -math.cos(phi), math.sin(phi)
    d = (math.sin(thb) * sx, math.sin(thb) * sy, -math.cos(thb))
    mag = math.sqrt(sum(c * c for c in d)) or 1.0
    d = tuple(c / mag for c in d)
    aim = (aim_r_mm * sx, aim_r_mm * sy, aim_z_mm)
    if abs(d[2]) < 1e-9:
        return None
    s_hi = (z_hi - aim[2]) / d[2]
    s_lo = (z_lo - aim[2]) / d[2]
    p_hi = tuple(aim[k] + s_hi * d[k] for k in range(3))
    p_lo = tuple(aim[k] + s_lo * d[k] for k in range(3))
    return (-p_hi[0], p_hi[2]), (-p_lo[0], p_lo[2]), (-aim[0], aim[2])


def draw(ax, x, z, alpha, title):
    m = (x > -3.2) & (x < 2.2) & (z > -0.55) & (z < 2.55)
    x, z, alpha = x[m], z[m], alpha[m]
    tri = Triangulation(x, z)
    xt, zt = x[tri.triangles], z[tri.triangles]
    tri.set_mask((np.ptp(xt, axis=1) > 0.35) | (np.ptp(zt, axis=1) > 0.35))
    # tricontourf only fills strictly between levels, so a cell at exactly 0 or 1
    # is left unfilled and the white axes background shows through. The solid
    # wire and the plate are alpha = 1, and that hole was painting them as gas.
    levels = np.linspace(0.0, 1.0, 17)
    levels[0] = -1e-3
    levels[-1] = 1.0 + 1e-3
    ax.tricontourf(tri, alpha, levels=levels, cmap="gray_r", vmin=0, vmax=1)
    ax.tricontour(tri, alpha, levels=[0.5], colors=["#d94801"], linewidths=1.15)
    # Plate and the wire outline on this plane.
    ax.axhline(0.0, color="#1f4e79", lw=1.0)
    ax.plot([-WIRE_R, -WIRE_R], [0.0, 2.45], color="#2ca02c", lw=0.9, ls="--")
    ax.plot([WIRE_R, WIRE_R], [0.0, 2.45], color="#2ca02c", lw=0.9, ls="--")
    ax.plot([-WIRE_R, WIRE_R], [2.45, 2.45], color="#2ca02c", lw=0.9, ls="--")
    # Rear beam, on this plane. Front spots hit off the plane.
    rear = beam_segment(180, -38, 0.24, 0.55)
    if rear:
        (x0, z0), (x1, z1), aim = rear
        ax.plot([x0, x1], [z0, z1], color="#e6c200", lw=1.1)
        ax.plot(aim[0], aim[1], marker="o", color="#e6c200", ms=4)
        top = (x0, z0) if z0 > z1 else (x1, z1)
        ax.text(top[0] - 0.05, top[1] - 0.12, "rear beam", color="#8a6d00", fontsize=7, ha="right")
    # Front-spot plate hits, x = -0.49 mm in the lab, so +0.49 on this plot.
    ax.plot([0.49], [0.0], marker="v", color="#e6c200", ms=6)
    # 1 mm scale.
    ax.plot([-2.7, -1.7], [-0.32, -0.32], color="k", lw=2.0, solid_capstyle="butt")
    ax.text(-2.2, -0.48, "1 mm", ha="center", va="top", fontsize=8)
    ax.set_aspect("equal")
    ax.set_xlim(-3.05, 2.05)
    ax.set_ylim(-0.55, 2.5)
    ax.set_xlabel("trailing  ←  x [mm]  →  leading")
    ax.set_ylabel("z [mm]")
    ax.set_title(title)
    ax.text(-2.9, 2.28, "trailing", fontsize=8, color="#333333")
    ax.text(1.85, 2.28, "leading", fontsize=8, color="#333333", ha="right")


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", default=str(ROOT / "cases/wire_cavity_cal10"))
    ap.add_argument("--tag", default="cal11")
    ap.add_argument("--times", nargs="+", default=["0.8", "0.9"])
    ap.add_argument("--out", default="")
    ap.add_argument("--with-radiograph", action="store_true",
                    help="put the radiograph in the first panel")
    args = ap.parse_args()
    case = Path(args.case)
    times = args.times
    out = Path(args.out) if args.out else ROOT / "results/calibration" / f"{args.tag}_sideview.png"
    n = len(times) + (1 if args.with_radiograph else 0)
    fig, axes = plt.subplots(1, n, figsize=(5.2 * n, 5.2), squeeze=False)
    axes = list(axes[0])
    if args.with_radiograph:
        radio = plt.imread(ROOT / "results/calibration/radiograph.png")
        axes[0].imshow(radio, cmap="gray")
        axes[0].set_title("Radiograph")
        axes[0].axis("off")
        axes = axes[1:]
    for ax, t in zip(axes, times):
        x, z, alpha, y = load(case, t)
        draw(ax, x, z, alpha, f"t = {t} s    y = {y[0]*1e3:.2f} mm")
        # Gas with metal both above and below, just behind the wire.
        world_x = -x * 1e-3
        zz = z * 1e-3
        trail = (world_x > 0.45e-3) & (world_x < 1.2e-3) & (zz > 0.15e-3) & (zz < 1.8e-3)
        gas = trail & (alpha < 0.5)
        metal = trail & (alpha > 0.5)
        n_enc = 0
        zlo = zhi = None
        if gas.any() and metal.any():
            zm = zz[metal]
            for zg in zz[gas]:
                if (zm < zg).any() and (zm > zg).any():
                    n_enc += 1
                    zlo = zg if zlo is None else min(zlo, zg)
                    zhi = zg if zhi is None else max(zhi, zg)
        if zlo is None:
            print(f"t={t} enclosed gas behind wire: none")
        else:
            print(f"t={t} enclosed gas behind wire: n={n_enc} z={zlo*1e3:.2f}..{zhi*1e3:.2f} mm")
    fig.suptitle(
        f"{args.tag} center plane. Dark is metal, white is gas. Orange is alpha = 0.5.\n"
        "Green dashes: 1 mm wire. Yellow: rear-beam axis and front-spot plate hit.",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
