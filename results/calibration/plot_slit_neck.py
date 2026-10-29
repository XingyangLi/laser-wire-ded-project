#!/usr/bin/env python3
"""Zoomed center-plane neck next to the radiograph crop.

Trailing side on the left, same orientation as the radiograph crop
(wire near the right of the crop, slit on its trailing face).
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.tri import Triangulation

from slit_metric import fmt, load_alpha, measure

ROOT = Path("/home/xingyang/laser-wire-ded-project")
# Neck crop of results/calibration/radiograph.png (656 x 372). The wire is the
# dark vertical bar near x = 370 px. The bright slit is on its trailing face,
# around x = 310-330 px and y = 180-220 px.
CROP = (240, 100, 470, 310)  # left, top, right, bottom
WIRE_R = 0.5


def first_metal_gap(x, z, alpha):
    """Gap from the wire face to the first metal, where the face itself is gas.

    The two-bin metric in slit_metric treats a one-cell wall as a bare face.
    This reports that wall: width is x of the first metal minus the wire radius,
    depth is the contiguous run that reaches highest.
    """
    edges = np.arange(0.70, 1.45, 0.025)
    ok = []
    for z0 in edges:
        face = (z >= z0) & (z < z0 + 0.025) & (x > 0.49) & (x < 0.53)
        metal = (z >= z0) & (z < z0 + 0.025) & (x > 0.48) & (x < 1.2) & (alpha >= 0.5)
        if not np.any(face) or float(np.mean(alpha[face] < 0.5)) <= 0.6 or not np.any(metal):
            ok.append(None)
            continue
        width = float(x[metal].min()) - 0.50
        ok.append(width if 0.02 <= width <= 0.12 else None)
    best = None
    i = 0
    while i < len(ok):
        if ok[i] is None:
            i += 1
            continue
        j = i
        while j < len(ok) and ok[j] is not None:
            j += 1
        lo = float(edges[i])
        hi = float(edges[j - 1] + 0.025)
        widths = [w for w in ok[i:j] if w is not None]
        rec = (hi, hi - lo, lo, float(np.median(widths)))
        if best is None or rec[0] > best[0]:
            best = rec
        i = j
    if best is None:
        return None
    hi, depth, lo, width = best
    return {"z_hi": hi, "depth": depth, "z_lo": lo, "width": width}


def draw_neck(ax, x, z, alpha, title):
    """x, z are millimetres in the lab frame (trailing is +x)."""
    plot_x = -x
    m = (x > 0.05) & (x < 1.45) & (z > 0.35) & (z < 1.85)
    px, pz, pa = plot_x[m], z[m], alpha[m]
    tri = Triangulation(px, pz)
    xt, zt = px[tri.triangles], pz[tri.triangles]
    tri.set_mask((np.ptp(xt, axis=1) > 0.12) | (np.ptp(zt, axis=1) > 0.12))
    levels = np.linspace(0.0, 1.0, 17)
    levels[0] = -1e-3
    levels[-1] = 1.0 + 1e-3
    # The cut-out wire has no cells. Fill that disk so it reads as metal
    # next to the radiograph; the VOF contour covers it when the cells exist.
    ax.add_patch(Rectangle((-WIRE_R, 0.40), WIRE_R - 0.05, 1.40,
                           facecolor="#1a1a1a", edgecolor="none", zorder=1))
    ax.tricontourf(tri, pa, levels=levels, cmap="gray_r", vmin=0, vmax=1, zorder=2)
    ax.tricontour(tri, pa, levels=[0.5], colors=["#d94801"], linewidths=0.9, zorder=3)
    ax.plot([-WIRE_R, -WIRE_R], [0.40, 1.80], color="#2ca02c", lw=0.8, ls="--", zorder=4)
    ax.plot([0.0, 0.0], [0.40, 1.80], color="#2ca02c", lw=0.6, ls=":", zorder=4)
    # Target slit: 0.05 mm wide, z = 0.75..1.20, on the trailing face.
    ax.plot(
        [-WIRE_R - 0.05, -WIRE_R - 0.05],
        [0.75, 1.20],
        color="#1f77b4", lw=1.0, ls=":", zorder=4,
    )
    ax.set_aspect("equal")
    ax.set_xlim(-1.40, -0.05)
    ax.set_ylim(0.40, 1.80)
    ax.set_xlabel("trailing  ←  x [mm]")
    ax.set_ylabel("z [mm]")
    ax.set_title(title, fontsize=9)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", action="append", required=True)
    ap.add_argument("--tag", action="append", default=[])
    ap.add_argument("--time", action="append", required=True,
                    help="one time directory name per case, same order")
    ap.add_argument("--out", required=True)
    ap.add_argument("--suptitle", default=None)
    args = ap.parse_args()
    tags = list(args.tag)
    while len(tags) < len(args.case):
        tags.append(Path(args.case[len(tags)]).name.replace("wire_cavity_", ""))
    times = args.time
    if len(times) == 1 and len(args.case) > 1:
        times = times * len(args.case)
    if len(times) != len(args.case):
        raise SystemExit("pass one --time per --case, or a single --time")

    radio = plt.imread(ROOT / "results/calibration/radiograph.png")
    l, t, r, b = CROP
    crop = radio[t:b, l:r]
    n = 1 + len(args.case)
    fig, axes = plt.subplots(1, n, figsize=(3.3 * n, 4.6), squeeze=False)
    axes = list(axes[0])
    axes[0].imshow(crop, cmap="gray", vmin=0, vmax=1 if crop.dtype.kind == "f" else 255)
    axes[0].set_title("Radiograph, neck", fontsize=9)
    axes[0].axis("off")
    for ax, case, tag, time_name in zip(axes[1:], args.case, tags, times):
        x, z, alpha = load_alpha(case, time_name)
        row = measure(x, z, alpha)
        gap = first_metal_gap(x, z, alpha)
        print(f"{tag} t={time_name}: {fmt(row)}")
        if gap is not None:
            print(
                f"{tag} t={time_name}: first metal {gap['width']:.3f} mm, "
                f"depth {gap['depth']:.3f} mm, z {gap['z_lo']:.3f}..{gap['z_hi']:.3f}"
            )
            title = (
                f"{tag}  t={time_name} s\n"
                f"{gap['depth']:.2f} mm deep, {gap['width']:.3f} mm to first metal"
            )
        else:
            title = (
                f"{tag}  t={time_name} s\n{row['depth_mm']:.2f} mm deep, "
                f"{row['width_mm']:.3f} mm wide"
            )
        draw_neck(ax, x, z, alpha, title)
    fig.suptitle(
        args.suptitle
        or (
            "Center plane at the neck. Dark is metal, white is gas.\n"
            "Green dash: trailing wire face. Blue dots: 0.05 mm × z 0.75–1.20 mm."
        ),
        fontsize=10,
    )
    fig.tight_layout()
    out = Path(args.out)
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
