#!/usr/bin/env python3
"""Side view of the pinned bead beside the radiograph, and a top view of the
three beam spots.

The beams are imposed: azimuths 0/120/-120 deg, each axis through the wire,
full domain. The bead is the mapped cal117 melt track. Nothing is painted.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import neck_state as ns
import render_hq_demo as hq

INK = "#1a120c"
PAPER = "#f6f1e4"
SPOT_COLORS = ("#1f4e79", "#8c2f1b", "#2f6b3a")


def beam_spots(case, z_plane=0.8e-3):
    """Name, power, axis hit at z_plane, 1/e^2 radius. Parsed from the case."""
    import re
    text = (Path(case) / "constant/meltProperties").read_text()
    spots = []
    for m in re.finditer(
        r"(beam\d+_az-?\d+)\s*\{\s*power\s+([0-9.eE+-]+);\s*"
        r"focus\s+\(([^)]+)\);\s*direction\s+\(([^)]+)\);\s*"
        r"radius\s+([0-9.eE+-]+);",
        text,
    ):
        name, power, focus, direction, radius = m.groups()
        fx, fy, fz = (float(v) for v in focus.split())
        dx, dy, dz = (float(v) for v in direction.split())
        t = (z_plane - fz) / dz
        spots.append((name, float(power), fx + t * dx, fy + t * dy, float(radius)))
    if len(spots) != 3:
        raise RuntimeError(f"expected 3 beams, found {len(spots)}")
    return spots


def load_scalar(case, tname, field):
    case = Path(case)
    procs = sorted(p for p in case.glob("processor*") if p.is_dir())
    parts = []
    for proc in procs:
        path = proc / tname / field
        vals = ns.read_internal(path, "scalar")
        if vals is None:
            n = len(ns.cell_centres(proc / "constant" / "polyMesh"))
            vals = ns.read_uniform(path, "scalar", n)
        if vals is None:
            return None
        parts.append(vals)
    return np.concatenate(parts)


def main():
    case = Path(sys.argv[1] if len(sys.argv) > 1 else "cases/wire_cavity_pin24")
    t0 = 0.7
    names = []
    root = case / "processor0"
    for p in root.iterdir():
        if not p.is_dir():
            continue
        try:
            t = float(p.name)
        except ValueError:
            continue
        if t + 1e-9 >= t0 and (p / "alpha.metal").is_file():
            names.append((t, p.name))
    names.sort()
    if not names:
        raise SystemExit(f"no times at or after {t0}")
    t_end, name = names[-1]
    x, y, z, a = hq.load_alpha(case, name)
    # Coarse full mesh: the first cell off y = 0 sits near 0.08 mm.
    xp, zp, ap = hq.plane_samples(x, y, z, a, y_max=2.5e-4, bin_m=4.0e-5)
    side = (-2.0e-3, 3.6e-3, -0.15e-3, 2.3e-3)
    Xmm, Zmm, A = hq.regular_grid(xp, zp, ap, side, 0.05e-3)
    # Crests on the centre plane, outside the wire, above the plate.
    lead = (ap > 0.5) & (xp < -0.6e-3) & (zp > 0.05e-3) & (zp < 2.2e-3)
    trail = (ap > 0.5) & (xp > 0.6e-3) & (zp > 0.05e-3) & (zp < 2.2e-3)
    lead_z = float(zp[lead].max() * 1e3) if lead.any() else float("nan")
    trail_z = float(zp[trail].max() * 1e3) if trail.any() else float("nan")
    spots = beam_spots(case)

    fig = plt.figure(figsize=(14.2, 5.6), dpi=140, facecolor=PAPER)
    grid = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.25, 1.15], wspace=0.28)
    ax_r = fig.add_subplot(grid[0, 0])
    ax_s = fig.add_subplot(grid[0, 1])
    ax_t = fig.add_subplot(grid[0, 2])
    for ax in (ax_r, ax_s, ax_t):
        ax.set_facecolor(PAPER)

    ax_r.imshow(hq.radio_crop())
    ax_r.set_axis_off()
    ax_r.set_title("radiograph", color=INK, fontsize=13, pad=6)

    ms = (t_end - t0) * 1e3
    hq.draw_metal(
        ax_s, Xmm, Zmm, A,
        f"centre plane at {ms:.1f} ms\ntrail {trail_z:.2f} mm   lead {lead_z:.2f} mm",
    )
    ax_s.set_title(
        f"centre plane at {ms:.1f} ms\ntrail {trail_z:.2f} mm   lead {lead_z:.2f} mm",
        color=INK, fontsize=12, pad=6,
    )

    # Top view: bead footprint and absorbed heat near the plate, with the
    # three geometric spots. Heat on the wire is not the substrate spot.
    foot = (a > 0.5) & (z > 0.05e-3) & (z < 1.8e-3)
    q = load_scalar(case, name, "Qheat")
    ax_t.set_facecolor("#efe8d6")
    xb = np.arange(-2.2e-3, 2.4e-3, 0.08e-3)
    yb = np.arange(-2.0e-3, 2.0e-3, 0.08e-3)
    if foot.any():
        H, xe, ye = np.histogram2d(x[foot], y[foot], bins=[xb, yb])
        ax_t.pcolormesh(
            xe * 1e3, ye * 1e3, (H.T > 0).astype(float),
            cmap="Greys", vmin=0, vmax=1.6, shading="flat", zorder=1,
        )
    if q is not None:
        # Heat off the wire, from the plate up through the bead. The wire
        # core is brighter and would hide the three spots.
        r = np.sqrt(x * x + y * y)
        band = (z > -0.1e-3) & (z < 1.6e-3) & (r > 0.55e-3)
        if band.any() and np.nanmax(q[band]) > 0:
            Hb, _, _ = np.histogram2d(
                x[band], y[band], bins=[xb, yb], weights=np.maximum(q[band], 0)
            )
            show = np.ma.masked_where(Hb.T <= 0, np.log10(Hb.T + 1))
            ax_t.pcolormesh(
                xb * 1e3, yb * 1e3, show, cmap="YlOrRd", shading="flat",
                alpha=0.9, zorder=2,
            )
    theta = np.linspace(0, 2 * np.pi, 80)
    for (bname, power, sx, sy, radius), color in zip(spots, SPOT_COLORS):
        sx_mm, sy_mm, r_mm = sx * 1e3, sy * 1e3, radius * 1e3
        az = bname.split("_az")[-1]
        ax_t.plot(
            sx_mm + r_mm * np.cos(theta), sy_mm + r_mm * np.sin(theta),
            color=color, lw=1.6, zorder=4,
        )
        ax_t.plot([0, sx_mm], [0, sy_mm], color=color, lw=0.8, ls="--", zorder=4)
        ax_t.text(
            sx_mm, sy_mm + r_mm + 0.12, f"{az}°  {power:.0f} W",
            color=color, fontsize=8, ha="center",
        )
    ax_t.plot(0, 0, marker="o", color=INK, ms=5, zorder=5)
    ax_t.set_aspect("equal", adjustable="box")
    ax_t.set_xlim(2.2, -2.2)
    ax_t.set_ylim(-2.0, 2.0)
    ax_t.set_xlabel("x [mm]    trailing on the left", color=INK, fontsize=10)
    ax_t.set_ylabel("y [mm]", color=INK, fontsize=10)
    ax_t.set_title("plate spots, 120° around the wire", color=INK, fontsize=13, pad=6)
    ax_t.tick_params(colors=INK, labelsize=9)
    for spine in ax_t.spines.values():
        spine.set_color("#5c5346")
    print(f"crests trail {trail_z:.2f} mm  lead {lead_z:.2f} mm")
    for bname, power, sx, sy, radius in spots:
        print(f"  {bname} {power:.0f} W  plate ({sx*1e3:.2f}, {sy*1e3:.2f}) mm")

    fig.suptitle(
        "Unpainted cal117 bead on a full mesh. Three beams at 0/120/−120°, spots around the wire.\n"
        "Hard-pin at 24 mm/s. Nothing painted. The circles are the beam axes; the colour is absorbed heat.",
        color=INK, fontsize=12, y=1.05,
    )
    out = HERE / "pin24_bead.png"
    fig.savefig(out, bbox_inches="tight", facecolor=PAPER)
    print(f"wrote {out} from t={name}")


if __name__ == "__main__":
    main()
