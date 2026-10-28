#!/usr/bin/env python3
"""Radiograph, center-plane side view, and a top view of the three beam spots.

The top view is the plate z = 0. Each circle is the 1/e^2 spot where that
beam axis meets the plate. The half-domain mesh is y >= 0; the negative-y
spot is drawn as well, because that beam is in the dictionary and symmetry
folds its rays onto the mesh.
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle
from matplotlib.tri import Triangulation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_beam_azimuths import check, plate_hit

ROOT = Path("/home/xingyang/laser-wire-ded-project")
CROP = (240, 100, 470, 310)
WIRE_R = 0.5


def load_side(case, time_name):
    path = Path(case) / "postProcessing/sidePlane" / time_name / "alpha.metal_xz.raw"
    rows = []
    with open(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            p = line.split()
            if len(p) >= 4:
                rows.append([float(p[0]) * 1e3, float(p[2]) * 1e3, float(p[3])])
    if not rows:
        raise SystemExit(f"no side samples in {path}")
    a = np.asarray(rows)
    return -a[:, 0], a[:, 1], a[:, 2]


def latest_side(case):
    root = Path(case) / "postProcessing/sidePlane"
    if not root.is_dir():
        return None
    names = []
    for p in root.iterdir():
        if (p / "alpha.metal_xz.raw").is_file():
            try:
                names.append((float(p.name), p.name))
            except ValueError:
                continue
    if not names:
        return None
    names.sort()
    return names[-1][1]


def draw_side(ax, x, z, alpha, title):
    m = (x > -4.5) & (x < 3.5) & (z > -0.4) & (z < 2.6)
    x, z, alpha = x[m], z[m], alpha[m]
    tri = Triangulation(x, z)
    xt, zt = x[tri.triangles], z[tri.triangles]
    tri.set_mask((np.ptp(xt, axis=1) > 0.45) | (np.ptp(zt, axis=1) > 0.45))
    levels = np.linspace(0.0, 1.0, 17)
    levels[0] = -1e-3
    levels[-1] = 1.0 + 1e-3
    ax.tricontourf(tri, alpha, levels=levels, cmap="gray_r", vmin=0, vmax=1)
    ax.tricontour(tri, alpha, levels=[0.5], colors=["#d94801"], linewidths=0.8)
    ax.axhline(0.0, color="#1f4e79", lw=0.8)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("x [mm], trailing to the left")
    ax.set_ylabel("z [mm]")


def draw_top(ax, beams):
    # Outline only, so a spot that lands inside the wire radius stays visible.
    ax.add_patch(Circle((0, 0), WIRE_R, facecolor="none", edgecolor="#111111", lw=1.2, zorder=3))
    ax.add_patch(Rectangle((-4, 0), 11, 3.5, fill=False, ls="--", ec="#888888", lw=0.6))
    colors = ["#d94801", "#2c7fb8", "#c4a000"]
    for b, c in zip(beams, colors):
        hit = plate_hit(b)
        if hit is None:
            continue
        x, y = hit[0] * 1e3, hit[1] * 1e3
        r = b["radius"] * 1e3
        ax.add_patch(Circle((x, y), r, facecolor=c, alpha=0.28, edgecolor=c, lw=1.0, zorder=2))
        fx, fy = b["focus"][0] * 1e3, b["focus"][1] * 1e3
        ax.plot([0, fx], [0, fy], color=c, lw=1.0, zorder=3)
        ax.plot(fx, fy, "x", color=c, ms=7, mew=1.5, zorder=4)
        ax.plot(x, y, "o", color=c, ms=5, zorder=4)
        ang = int(round(math_az(fx, fy)))
        if ang > 180:
            ang -= 360
        ax.text(fx, fy + 0.22, f"{ang}°  {b['power']:.0f} W", color=c, fontsize=8, ha="center")
    ax.set_aspect("equal")
    ax.set_xlim(-1.6, 1.6)
    ax.set_ylim(-1.6, 1.6)
    ax.axhline(0, color="#dddddd", lw=0.5)
    ax.axvline(0, color="#dddddd", lw=0.5)
    ax.set_title("Top view: aims (×) and plate spots", fontsize=9)
    ax.set_xlabel("x [mm], +x is behind the wire")
    ax.set_ylabel("y [mm]")


def math_az(x_mm, y_mm):
    import math
    return math.degrees(math.atan2(y_mm, -x_mm)) % 360.0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--tag", default="track")
    ap.add_argument("--time", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    beams = check(args.case)
    time_name = args.time or latest_side(args.case)

    radio = plt.imread(ROOT / "results/calibration/radiograph.png")
    l, t, r, b = CROP
    crop = radio[t:b, l:r]
    n = 3 if time_name else 2
    fig, axes = plt.subplots(1, n, figsize=(4.2 * n, 4.4))
    axes[0].imshow(crop, cmap="gray", vmin=0, vmax=1 if crop.dtype.kind == "f" else 255)
    axes[0].set_title("Radiograph, neck", fontsize=9)
    axes[0].axis("off")
    if time_name:
        x, z, alpha = load_side(args.case, time_name)
        draw_side(axes[1], x, z, alpha, f"{args.tag}  t={time_name} s")
        draw_top(axes[2], beams)
    else:
        draw_top(axes[1], beams)
    fig.suptitle(
        "Beams at 60°, −60° and 180° (120° apart). "
        "Circles are the plate spots. Crosses are the aim points.\n"
        "The y < 0 spot is in the dictionary; symmetry folds those rays into the half mesh.",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(args.out, dpi=140, bbox_inches="tight")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
