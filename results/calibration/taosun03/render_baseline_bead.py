#!/usr/bin/env python3
"""Side view beside the radiograph, and a top view of the three fixed beams.

    python3 render_baseline_bead.py --case cases/wire_cavity_baseline \
        --out results/calibration/taosun03/baseline_bead_views.png
"""
import argparse
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Ellipse, Circle

ROOT = Path(__file__).resolve().parents[3]
RADIO = ROOT / "results/calibration/radiograph.png"
TSOL = 1658.0
TLIQ = 1723.0
WIRE_R = 0.5e-3
CMAP = LinearSegmentedColormap.from_list(
    "metal_dark_yellow",
    ["#f4d35e", "#c48a2a", "#5c3a16", "#1a120c"],
)


def beams_from_case(case):
    text = (case / "constant/meltProperties").read_text()
    rows = []
    for m in re.finditer(
        r"(beam\d+_az[^\s{]+)\s*\{\s*power\s+([eE0-9.+-]+);\s*"
        r"focus\s+\(([^)]+)\);\s*direction\s+\(([^)]+)\);\s*radius\s+([eE0-9.+-]+);",
        text,
    ):
        name = m.group(1)
        power = float(m.group(2))
        focus = tuple(float(x) for x in m.group(3).split())
        direction = tuple(float(x) for x in m.group(4).split())
        radius = float(m.group(5))
        mag = math.sqrt(sum(c * c for c in direction)) or 1.0
        d = tuple(c / mag for c in direction)
        t = (0.0 - focus[2]) / d[2]
        plate = tuple(focus[i] + t * d[i] for i in range(3))
        rows.append(dict(name=name, power=power, focus=focus, d=d,
                         radius=radius, plate=plate))
    if len(rows) != 3:
        raise SystemExit(f"expected 3 beams in {case}, found {len(rows)}")
    return rows


def load_raw(path):
    rows = []
    if not path.is_file():
        return None
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        rows.append([float(v) for v in parts[:4]])
    return np.asarray(rows) if rows else None


def latest_plane(case):
    root = case / "postProcessing" / "sidePlane"
    if not root.is_dir():
        return None
    best = None
    for d in root.iterdir():
        if not d.is_dir():
            continue
        try:
            tv = float(d.name)
        except ValueError:
            continue
        if best is None or tv > best[0]:
            best = (tv, d)
    return best


def bin_plane(samples, x0, x1, z0, z1, step):
    if samples is None:
        return None
    nx = int(round((x1 - x0) / step))
    nz = int(round((z1 - z0) / step))
    ix = np.clip(((samples[:, 0] - x0) / step).astype(int), 0, nx - 1)
    iz = np.clip(((samples[:, 2] - z0) / step).astype(int), 0, nz - 1)
    acc = np.full((nz, nx), np.nan)
    # last write wins; samples are cell centres, one per cell
    acc[iz, ix] = samples[:, 3]
    return acc


def ellipse_on_plate(beam, ax, color, ls="-"):
    """Footprint of the 1/e^2 cylinder on z = 0."""
    d = beam["d"]
    # Major axis stretches by 1/|d.z| along the horizontal projection of d.
    horiz = math.hypot(d[0], d[1]) or 1e-12
    ux, uy = d[0] / horiz, d[1] / horiz
    w = beam["radius"]
    major = 2 * w / max(abs(d[2]), 1e-6)
    minor = 2 * w
    ang = math.degrees(math.atan2(uy, ux))
    cx, cy = beam["plate"][0] * 1e3, beam["plate"][1] * 1e3
    ax.add_patch(Ellipse((cx, cy), major * 1e3, minor * 1e3, angle=ang,
                         fill=False, lw=1.4, ec=color, ls=ls))
    ax.plot([beam["focus"][0] * 1e3, cx], [beam["focus"][1] * 1e3, cy],
            lw=0.8, color=color, ls=ls)
    ax.plot(cx, cy, "o", ms=3, color=color)


def volume_stats(case, t_target):
    try:
        import pyvista as pv
    except ImportError:
        return None
    foam = case / "case.foam"
    if not foam.is_file():
        return None
    reader = pv.OpenFOAMReader(str(foam))
    times = [float(t) for t in reader.time_values]
    if not times:
        return None
    t = min(times, key=lambda v: abs(v - t_target))
    reader.set_active_time_value(t)
    data = reader.read()
    mesh = None
    if isinstance(data, pv.MultiBlock):
        for i in range(len(data)):
            block = data[i]
            if block is not None and "alpha.metal" in block.array_names:
                mesh = block
                break
    else:
        mesh = data
    if mesh is None or "alpha.metal" not in mesh.array_names:
        return None
    cc = np.asarray(mesh.cell_centers().points)
    alpha = np.asarray(mesh.cell_data["alpha.metal"])
    temp = np.asarray(mesh.cell_data["T"]) if "T" in mesh.cell_data else None
    liq = (np.asarray(mesh.cell_data["liquidFraction"])
           if "liquidFraction" in mesh.cell_data else None)
    return dict(t=t, cc=cc, alpha=alpha, temp=temp, liq=liq)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    case = Path(args.case)
    out = Path(args.out)
    beams = beams_from_case(case)
    plane = latest_plane(case)
    vol = None
    t_show = None
    if plane is not None:
        t_show, pdir = plane
        alpha = load_raw(pdir / "alpha.metal_xz.raw")
        temp = load_raw(pdir / "T_xz.raw")
        liq = load_raw(pdir / "liquidFraction_xz.raw")
        vol = volume_stats(case, t_show)
    else:
        alpha = temp = liq = None

    x0, x1 = -3.2e-3, 3.6e-3
    z0, z1 = -0.6e-3, 2.6e-3
    step = 0.08e-3
    aimg = bin_plane(alpha, x0, x1, z0, z1, step)
    timg = bin_plane(temp, x0, x1, z0, z1, step)

    radio = mpimg.imread(RADIO)
    fig = plt.figure(figsize=(14.2, 8.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1.0], hspace=0.28, wspace=0.22)

    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(radio, cmap="gray")
    ax.set_title("Radiograph\ntrailing side on the left")
    ax.axis("off")

    ax = fig.add_subplot(gs[0, 1])
    if aimg is not None:
        # Trailing (+x) on the left, matching the radiograph panel.
        show = np.flip(aimg, axis=1)
        ax.imshow(show, origin="lower", cmap=CMAP, vmin=0, vmax=1,
                  extent=[x1 * 1e3, x0 * 1e3, z0 * 1e3, z1 * 1e3],
                  interpolation="nearest", aspect="equal")
        ax.axhline(0, color="k", lw=0.4)
        ax.set_xlabel("+x trailing  ←     mm     →  leading")
        ax.set_ylabel("z [mm]")
        ax.set_title(f"Centre plane, metal\nt = {t_show:.3f} s")
    else:
        ax.set_title("Centre plane not written yet")
        ax.axis("off")

    ax = fig.add_subplot(gs[0, 2])
    if timg is not None:
        show = np.flip(timg, axis=1)
        metal = np.flip(aimg, axis=1) if aimg is not None else None
        if metal is not None:
            show = np.where(metal > 0.5, show, np.nan)
        im = ax.imshow(show, origin="lower", cmap="inferno",
                       vmin=300, vmax=2800,
                       extent=[x1 * 1e3, x0 * 1e3, z0 * 1e3, z1 * 1e3],
                       interpolation="nearest", aspect="equal")
        ax.axhline(0, color="w", lw=0.4)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label("T [K]")
        ax.set_xlabel("+x trailing  ←     mm")
        ax.set_title("Centre plane, temperature\nsolidus 1658 K")
    else:
        ax.set_title("Temperature not written yet")
        ax.axis("off")

    ax = fig.add_subplot(gs[1, :2])
    colors = ["#c0392b", "#2980b9", "#1e8449"]
    labels = []
    if vol is not None:
        cc, al = vol["cc"], vol["alpha"]
        metal = al > 0.5
        # free-surface height in 0.15 mm bins
        xb = np.arange(-3.5, 3.5 + 0.15, 0.15)
        yb = np.arange(0.0, 3.6, 0.15)
        h = np.full((len(yb) - 1, len(xb) - 1), np.nan)
        ix = np.clip(np.digitize(cc[:, 0] * 1e3, xb) - 1, 0, len(xb) - 2)
        iy = np.clip(np.digitize(cc[:, 1] * 1e3, yb) - 1, 0, len(yb) - 2)
        for i in np.where(metal & (cc[:, 2] > 0))[0]:
            zmm = cc[i, 2] * 1e3
            if not np.isfinite(h[iy[i], ix[i]]) or zmm > h[iy[i], ix[i]]:
                h[iy[i], ix[i]] = zmm
        ax.imshow(h, origin="lower", cmap="YlOrBr", vmin=0, vmax=2.2,
                  extent=[xb[0], xb[-1], yb[0], yb[-1]],
                  interpolation="nearest", aspect="equal")
    ax.add_patch(Circle((0, 0), WIRE_R * 1e3, fill=False, ec="k", lw=1.2))
    for b, c in zip(beams, colors):
        ellipse_on_plate(b, ax, c)
        # mirror of a front beam across y = 0, drawn because the mesh is the y >= 0 half
        if abs(b["plate"][1]) > 1e-6:
            twin = dict(b)
            twin["plate"] = (b["plate"][0], -b["plate"][1], b["plate"][2])
            twin["focus"] = (b["focus"][0], -b["focus"][1], b["focus"][2])
            twin["d"] = (b["d"][0], -b["d"][1], b["d"][2])
            ellipse_on_plate(twin, ax, c, ls="--")
        labels.append(f"{b['name']}  {b['power']:.0f} W")
    ax.set_xlim(-3.2, 3.2)
    ax.set_ylim(-2.4, 2.4)
    ax.set_aspect("equal")
    ax.set_xlabel("x [mm]   +x is behind the wire (trailing)")
    ax.set_ylabel("y [mm]")
    ax.set_title("Top view: free-surface height and the 1/e² spot on the plate\n"
                 + "   ".join(labels))
    ax.axhline(0, color="k", lw=0.3)
    ax.axvline(0, color="k", lw=0.3)

    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    lines = ["Baseline, fixed aims", "no slit, no oxygen", ""]
    for b in beams:
        lines.append(
            f"{b['name']}: {b['power']:.0f} W"
        )
        lines.append(
            f"  plate hit ({b['plate'][0]*1e3:.2f}, {b['plate'][1]*1e3:.2f}) mm"
        )
        lines.append(f"  spot {b['radius']*1e3:.2f} mm")
    if vol is not None and vol["liq"] is not None:
        cc, liq, temp, al = vol["cc"], vol["liq"], vol["temp"], vol["alpha"]
        r = np.hypot(cc[:, 0], cc[:, 1])
        wire = (r < 0.55e-3) & (cc[:, 2] > 0) & (al > 0.5)
        molten = wire & (liq > 0.5)
        solid = wire & (liq < 0.5)
        lines.append("")
        if molten.any():
            lines.append(
                f"wire liquid z {cc[molten, 2].min()*1e3:.2f}"
                f"–{cc[molten, 2].max()*1e3:.2f} mm"
            )
        else:
            lines.append("wire liquid: none")
        if solid.any():
            lines.append(f"solid wire above z {cc[solid, 2].min()*1e3:.2f} mm")
        sub = (cc[:, 2] < 0) & (cc[:, 2] > -0.6e-3) & (liq > 0.5)
        bead = (cc[:, 2] > 0.05e-3) & (al > 0.5) & (r > 0.55e-3)
        trail = bead & (cc[:, 0] > WIRE_R)
        lead = bead & (cc[:, 0] < -WIRE_R)
        lines.append(f"molten substrate cells {int(sub.sum())}")
        if temp is not None and sub.any():
            lines.append(f"substrate T max {temp[sub].max():.0f} K")
        if trail.any():
            lines.append(f"trail crest {cc[trail, 2].max()*1e3:.2f} mm")
        if lead.any():
            lines.append(f"lead crest {cc[lead, 2].max()*1e3:.2f} mm")
        if temp is not None:
            lines.append(f"T max {temp.max():.0f} K")
    elif liq is not None:
        lines.append("")
        lines.append("volume fields not read;")
        lines.append("side plane only")
    text = "\n".join(lines)
    ax.text(0.0, 1.0, text, va="top", ha="left", family="monospace", fontsize=9,
            transform=ax.transAxes)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print("wrote", out)
    print(text)


if __name__ == "__main__":
    main()
