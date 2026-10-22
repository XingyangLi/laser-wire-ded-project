#!/usr/bin/env python3
"""Side view, metrics and optional 3D iso-surface for a calibration run.

Trailing side (+x) is drawn on the left, matching the radiograph.
The 3D view needs a reconstructed time directory (reconstructPar -latestTime)
and pyvista. Pass --iso to attempt it; a missing reader is reported and skipped.
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.tri import Triangulation

# 316L from materials.py
TSOL = 1658.0
TLIQ = 1723.0
WIRE_R = 0.55e-3


def load_raw(path):
    rows = []
    if not path.is_file():
        return None
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            rows.append([float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])])
    if not rows:
        return None
    return np.asarray(rows)


def read_table(path):
    if not path.is_file():
        return []
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(line.split())
    return rows


def times_of(case):
    root = case / "postProcessing" / "sidePlane"
    if not root.is_dir():
        return []
    out = []
    for d in root.iterdir():
        if d.is_dir():
            try:
                out.append((float(d.name), d))
            except ValueError:
                pass
    out.sort()
    return out


def draw_slice(ax, pts, values, vmin, vmax, cmap):
    x = -pts[:, 0] * 1e3
    z = pts[:, 2] * 1e3
    tri = Triangulation(x, z)
    xt, zt = x[tri.triangles], z[tri.triangles]
    long_edge = (np.ptp(xt, axis=1) > 0.35) | (np.ptp(zt, axis=1) > 0.35)
    tri.set_mask(long_edge)
    tcf = ax.tricontourf(tri, values, levels=16, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_aspect("equal")
    ax.set_xlabel("trailing  <-  x [mm]  ->  leading")
    ax.set_ylabel("z [mm]")
    return tcf


def window(pts):
    m = (
        (pts[:, 0] > -0.004) & (pts[:, 0] < 0.005)
        & (pts[:, 2] > -0.0006) & (pts[:, 2] < 0.0036)
    )
    return pts[m] if m.any() else pts


def bead_metrics(alpha, temp):
    """Height and streamwise extent of metal that is not the cold wire column."""
    if alpha is None:
        return {}
    a = alpha
    tmap = None
    if temp is not None and len(temp) == len(alpha):
        tmap = temp[:, 3]
    elif temp is not None:
        # nearest temperature onto alpha samples is unnecessary: both raw files
        # share the cutting-plane points. Fall back to alpha-only if sizes differ.
        tmap = None
    r = np.hypot(a[:, 0], a[:, 1])
    metal = a[:, 3] > 0.5
    above = a[:, 2] > 0.05e-3
    cold_wire = metal & (r < WIRE_R) & above
    if tmap is not None and len(tmap) == len(a):
        cold_wire = cold_wire & (tmap < TSOL)
        liquid = metal & (tmap > TLIQ)
    else:
        liquid = np.zeros(len(a), dtype=bool)
    bead = metal & above & ~cold_wire
    out = {
        "n_bead_samples": int(bead.sum()),
        "n_liquid_samples": int(liquid.sum()),
    }
    if bead.any():
        out["bead_z_max_mm"] = float(a[bead, 2].max() * 1e3)
        out["bead_x_min_mm"] = float(a[bead, 0].min() * 1e3)
        out["bead_x_max_mm"] = float(a[bead, 0].max() * 1e3)
        # Trailing (+x) vs leading (-x) crest, outside the wire.
        trail = bead & (a[:, 0] > WIRE_R)
        lead = bead & (a[:, 0] < -WIRE_R)
        if trail.any():
            out["trail_z_max_mm"] = float(a[trail, 2].max() * 1e3)
        if lead.any():
            out["lead_z_max_mm"] = float(a[lead, 2].max() * 1e3)
    if liquid.any():
        out["liquid_z_max_mm"] = float(a[liquid, 2].max() * 1e3)
        out["liquid_T_max_K"] = float(tmap[liquid].max()) if tmap is not None else ""
    if tmap is not None:
        out["T_max_slice_K"] = float(tmap.max())
    return out


def parse_contact(rows):
    if not rows:
        return {}
    last = rows[-1]
    # zWireMax is column 19, zWireMin 20, yMax 14, xMin 11, xMax 12
    def f(i):
        try:
            return float(last[i])
        except (IndexError, ValueError):
            return None
    return {
        "t_contact_s": f(0),
        "n_wire": f(15),
        "z_wire_max_mm": None if f(19) is None or f(19) < -0.4 else f(19) * 1e3,
        "z_wire_min_mm": None if f(20) is None or f(20) < -0.4 else f(20) * 1e3,
        "contact_x_min_mm": None if f(11) is None else f(11) * 1e3,
        "contact_x_max_mm": None if f(12) is None else f(12) * 1e3,
        "contact_y_max_mm": None if f(14) is None else f(14) * 1e3,
    }


def parse_cavity(rows):
    if not rows:
        return {}
    last = rows[-1]
    def f(i):
        try:
            return float(last[i])
        except (IndexError, ValueError):
            return None
    status = {"0": "none", "1": "open", "2": "closed", "3": "mixed"}.get(last[1], last[1])
    vol = f(4)
    return {
        "t_cavity_s": f(0),
        "cavity_status": status,
        "cavity_volume_mm3": None if vol is None else vol * 1e9,
        "cavity_depth_mm": None if f(7) is None else f(7) * 1e3,
        "cavity_length_mm": None if f(8) is None else f(8) * 1e3,
        "cavity_cx_mm": None if f(9) is None else f(9) * 1e3,
        "cavity_cz_mm": None if f(11) is None else f(11) * 1e3,
    }


def write_iso(case, out, tag):
    """Iso-surface of alpha.metal = 0.5 from the latest reconstructed time."""
    times = []
    for d in case.iterdir():
        if not d.is_dir():
            continue
        name = d.name
        if name in ("0", "constant", "system", "postProcessing", "processor0"):
            continue
        try:
            times.append((float(name), d))
        except ValueError:
            continue
    if not times:
        print("no reconstructed time directory; skip 3D iso-surface")
        return None
    times.sort()
    t, td = times[-1]
    vtu = list(td.glob("*.vtu")) + list((case / "VTK").glob("*.vtu"))
    try:
        import pyvista as pv
    except ImportError:
        print("pyvista is not installed in this interpreter; skip 3D")
        return None
    mesh = None
    foam = case / "case.foam"
    if foam.is_file():
        try:
            reader = pv.OpenFOAMReader(str(foam))
            reader.set_active_time_value(t)
            mesh = reader.read()
            if isinstance(mesh, pv.MultiBlock):
                # internal mesh is usually block 0
                mesh = mesh[0]
        except Exception as exc:
            print("OpenFOAM reader failed:", exc)
            mesh = None
    if mesh is None and vtu:
        mesh = pv.read(str(vtu[-1]))
    if mesh is None:
        print("no mesh for iso-surface")
        return None
    name = None
    for cand in ("alpha.metal", "alpha.metalMean"):
        if cand in mesh.array_names:
            name = cand
            break
    if name is None:
        print("alpha.metal not on the mesh; arrays:", mesh.array_names[:12])
        return None
    surf = mesh.contour([0.5], scalars=name)
    if surf.n_points == 0:
        print("empty iso-surface")
        return None
    # Keep the bead window.
    bounds = surf.bounds
    clip = surf.clip_box(bounds=(
        -0.004, 0.005,
        -0.0002, max(bounds[3], 0.003),
        -0.0004, 0.0035,
    ), invert=False)
    pl = pv.Plotter(off_screen=True, window_size=(1100, 800))
    pl.set_background("white")
    pl.add_mesh(clip, color="#b9c4cf", smooth_shading=True, specular=0.3)
    # Look from +y so the symmetry plane faces the camera. +x (trailing) is left
    # when the view-up is +z and the camera sits on +y... verify with an axis.
    pl.camera_position = [
        (0.0005, 0.012, 0.0016),
        (0.0004, 0.0, 0.0008),
        (0.0, 0.0, 1.0),
    ]
    pl.add_axes()
    dest = out / f"{tag}_iso_alpha.png"
    pl.screenshot(str(dest))
    pl.close()
    print("wrote", dest)
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", default="results/calibration")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--iso", action="store_true")
    args = ap.parse_args()
    case = Path(args.case)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    slices = times_of(case)
    metrics = {}
    if slices:
        chosen = slices if len(slices) <= 4 else [slices[i] for i in
            sorted({0, len(slices)//2, len(slices)-1})]
        fig, axes = plt.subplots(2, len(chosen), figsize=(3.4 * len(chosen), 7.0), squeeze=False)
        im = None
        for i, (t, d) in enumerate(chosen):
            alpha = load_raw(d / "alpha.metal_xz.raw")
            temp = load_raw(d / "T_xz.raw")
            if alpha is not None:
                sub = window(alpha)
                im = draw_slice(axes[0, i], sub, sub[:, 3], 0.0, 1.0, "cividis")
                axes[0, i].set_title(f"t = {t:.3f} s\nalpha.metal")
                axes[0, i].axvline(0.0, color="w", lw=0.4, alpha=0.5)
            if temp is not None:
                sub = window(temp)
                tmax = max(1800.0, float(np.percentile(sub[:, 3], 99)))
                draw_slice(axes[1, i], sub, sub[:, 3], 300.0, tmax, "inferno")
                axes[1, i].set_title("T [K]")
        if im is not None:
            fig.colorbar(im, ax=axes[0, :].tolist(), fraction=0.02, pad=0.02, label="alpha.metal")
        fig.suptitle(f"{args.tag}: side view. Trailing bead (+x) is on the left.")
        fig.savefig(out / f"{args.tag}_side_alpha_T.png", dpi=140, bbox_inches="tight")
        plt.close(fig)
        print("wrote", out / f"{args.tag}_side_alpha_T.png")
        alpha = load_raw(slices[-1][1] / "alpha.metal_xz.raw")
        temp = load_raw(slices[-1][1] / "T_xz.raw")
        metrics.update(bead_metrics(alpha, temp))
        metrics["t_slice_s"] = slices[-1][0]

    contact = parse_contact(read_table(case / "postProcessing" / "contactLine" / "contactLine.dat"))
    cavity = parse_cavity(read_table(case / "postProcessing" / "wireCavity" / "wireCavity.dat"))
    metrics.update(contact)
    metrics.update(cavity)

    summary = out / f"{args.tag}_metrics.csv"
    with summary.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["quantity", "value"])
        for k, v in metrics.items():
            w.writerow([k, v])
    print("wrote", summary)
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    if args.iso:
        write_iso(case, out, args.tag)


if __name__ == "__main__":
    main()
