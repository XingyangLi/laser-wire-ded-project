#!/usr/bin/env python3
"""Width and depth of the feed-24 drag shell, beside the radiograph.

The contact line is imposed. The slit, if any, is whatever the free pool
did. Times are milliseconds after the shell starts moving.

    /home/asb6102/lwded-viz/bin/python results/calibration/taosun03/plot_drag.py \
        --case cases/wire_cavity_drag24 --t0 0.7047
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import render_hq_demo as hq
import score_film as sf

INK = "#1a120c"
PAPER = "#f6f1e4"


def series(case, t0):
    rows = []
    for t, name in sf.times_in(case, t0, 10.0):
        row = sf.centre_plane(case, name)
        rows.append((t, name, row))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", default="cases/wire_cavity_drag24")
    ap.add_argument("--t0", type=float, default=0.7047)
    ap.add_argument("--out", default=str(HERE / "drag24_slit.png"))
    ap.add_argument(
        "--suptitle",
        default=(
            "Pinned trailing face, feed 24 mm/s. Laser, recoil and Marangoni off.\n"
            "The pin is imposed; the pool behind the shell is free."
        ),
    )
    ap.add_argument(
        "--series-title",
        default="",
        help="Right-hand panel title. Default names the imposed-line travel.",
    )
    args = ap.parse_args()
    case = Path(args.case)
    rows = series(case, args.t0)
    if not rows:
        raise SystemExit(f"no times at or after {args.t0} in {case}")
    t_end, name_end, row_end = rows[-1]
    elapsed = [(t - args.t0) * 1e3 for t, _name, _row in rows]
    depth = [row["depth_mm"] for _t, _name, row in rows]
    width = [row["width_mm"] for _t, _name, row in rows]

    fig = plt.figure(figsize=(13.2, 5.4), dpi=140, facecolor=PAPER)
    grid = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.15, 1.35], wspace=0.28)
    ax_r = fig.add_subplot(grid[0, 0])
    ax_n = fig.add_subplot(grid[0, 1])
    ax_s = fig.add_subplot(grid[0, 2])
    for ax in (ax_r, ax_n, ax_s):
        ax.set_facecolor(PAPER)

    crop = hq.radio_crop()
    ax_r.imshow(crop)
    ax_r.set_axis_off()
    ax_r.set_title("radiograph", color=INK, fontsize=13, pad=6)

    x, y, z, a = hq.load_alpha(case, name_end)
    xp, zp, ap = hq.plane_samples(x, y, z, a)
    Xmm, Zmm, A = hq.regular_grid(xp, zp, ap, hq.ZOOM, hq.ZOOM_DX)
    ms = (t_end - args.t0) * 1e3
    title = (
        f"neck at {ms:.1f} ms\n"
        f"depth {row_end['depth_mm']:.3f} mm   "
        f"width {row_end['width_mm']:.3f} mm"
    )
    hq.draw_metal(ax_n, Xmm, Zmm, A, title)
    hq.mark_slit(ax_n, row_end)
    ax_n.set_title(title, color=INK, fontsize=11, pad=6)
    ax_n.tick_params(labelsize=9)
    ax_n.set_xlabel("x [mm]    trailing on the left", color=INK, fontsize=10)
    ax_n.set_ylabel("z [mm]", color=INK, fontsize=10)

    ax_s.plot(elapsed, depth, color="#8c2f1b", lw=2.0, marker="o", ms=4, label="depth")
    ax_s.plot(elapsed, width, color="#1f4e79", lw=2.0, marker="s", ms=4, label="width")
    ax_s.axhline(0.25, color="#8c2f1b", lw=0.7, ls="--", alpha=0.7)
    ax_s.axhline(0.05, color="#1f4e79", lw=0.7, ls="--", alpha=0.7)
    ax_s.set_xlim(left=0)
    ymax = max(0.30, max(depth + width) * 1.25)
    ax_s.set_ylim(0, ymax)
    drop_mm = 24.0 * (t_end - args.t0)
    series_title = args.series_title or (
        f"centre-plane slit\nimposed line moved {drop_mm:.2f} mm"
    )
    ax_s.set_xlabel("time after the start [ms]", color=INK, fontsize=11)
    ax_s.set_ylabel("millimetres", color=INK, fontsize=11)
    ax_s.set_title(series_title, color=INK, fontsize=13, pad=6)
    ax_s.legend(frameon=False, fontsize=11, loc="upper right")
    if max(depth) < 1e-6 and max(width) < 1e-6:
        ax_s.text(
            0.04, 0.08, "width = 0 and depth = 0\nat every sample",
            transform=ax_s.transAxes, color=INK, fontsize=11, va="bottom",
        )
    ax_s.tick_params(colors=INK, labelsize=10)
    for spine in ax_s.spines.values():
        spine.set_color("#5c5346")

    fig.suptitle(args.suptitle, color=INK, fontsize=13, y=1.02)
    out = Path(args.out)
    fig.savefig(out, bbox_inches="tight", facecolor=PAPER)
    print(f"wrote {out}")
    for t, name, row in rows:
        print(
            f"t={name}  dt={(t - args.t0) * 1e3:.2f} ms  "
            f"depth {row['depth_mm']:.3f}  width {row['width_mm']:.3f}  "
            f"{'open' if row['open'] else 'closed'}"
        )


if __name__ == "__main__":
    main()
