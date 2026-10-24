#!/usr/bin/env python3
"""Side-view plots and time series for a wire-cavity run.

Reads postProcessing/sidePlane/*/xz_*.raw (XZ cut at y = 20 um) plus
wireCavity.dat, contactLine.dat and porosity.dat. +x is the trailing
direction (substrate motion). Figures put +x on the left so the deposited
bead sits on the left of the wire, as in the side-view radiograph.
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.tri import Triangulation


def load_raw(path):
    rows = []
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
        return None, []
    header = []
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if "time" in line and not header:
                    header = line.lstrip("#").split()
                continue
            rows.append([float(x) if _is_float(x) else x for x in line.split()])
    return header, rows


def _is_float(text):
    try:
        float(text)
        return True
    except ValueError:
        return False


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


def draw_slice(ax, pts, vmin, vmax, cmap, label):
    x = -pts[:, 0] * 1e3   # +x (trailing) to the left
    z = pts[:, 2] * 1e3
    tri = Triangulation(x, z)
    # Drop triangles that span a gap (wire / gas jumps).
    xt, zt = x[tri.triangles], z[tri.triangles]
    long_edge = (
        (np.ptp(xt, axis=1) > 0.35) | (np.ptp(zt, axis=1) > 0.35)
    )
    tri.set_mask(long_edge)
    tcf = ax.tricontourf(tri, pts[:, 3], levels=16, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_aspect("equal")
    ax.set_xlabel("trailing  ←   x [mm]   →  leading")
    ax.set_ylabel("z [mm]")
    return tcf


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", default="results/reference")
    ap.add_argument("--tag", default="reference")
    args = ap.parse_args()
    case = Path(args.case)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    slices = times_of(case)
    # A handful of times spread across the run, plus the last sample.
    if slices:
        if len(slices) <= 6:
            chosen = slices
        else:
            pick_i = [int(round(i * (len(slices) - 1) / 5)) for i in range(6)]
            chosen = [slices[i] for i in sorted(set(pick_i))]
        n = len(chosen)
        fig, axes = plt.subplots(2, n, figsize=(3.2 * n, 7.2), squeeze=False)
        im = None
        for i, (t, d) in enumerate(chosen):
            alpha = load_raw(d / "alpha.metal_xz.raw")
            temp = load_raw(d / "T_xz.raw")
            if alpha is not None:
                # Window on the bead and the wire.
                m = (alpha[:, 0] > -0.004) & (alpha[:, 0] < 0.005) & (alpha[:, 2] > -0.0008) & (alpha[:, 2] < 0.0035)
                sub = alpha[m] if m.any() else alpha
                im = draw_slice(axes[0, i], sub, 0.0, 1.0, "cividis", "alpha")
                axes[0, i].set_title(f"t = {t:.3f} s\nalpha.metal")
            if temp is not None:
                m = (temp[:, 0] > -0.004) & (temp[:, 0] < 0.005) & (temp[:, 2] > -0.0008) & (temp[:, 2] < 0.0035)
                sub = temp[m] if m.any() else temp
                draw_slice(axes[1, i], sub, 300.0, max(1800.0, float(np.percentile(sub[:, 3], 98))), "inferno", "T")
                axes[1, i].set_title("T [K]")
        if im is not None:
            fig.colorbar(im, ax=axes[0, :].tolist(), fraction=0.02, pad=0.02, label="alpha.metal")
        fig.suptitle(f"{args.tag}: XZ side view. Trailing bead (+x) is on the left.")
        fig.savefig(out / f"{args.tag}_side_alpha_T.png", dpi=140, bbox_inches="tight")
        plt.close(fig)
        print("wrote", out / f"{args.tag}_side_alpha_T.png")

    # Cavity volume and wire contact height.
    _, cav = read_table(case / "postProcessing" / "wireCavity" / "wireCavity.dat")
    _, cl = read_table(case / "postProcessing" / "contactLine" / "contactLine.dat")
    _, por = read_table(case / "postProcessing" / "porosity" / "porosity.dat")
    fig, ax = plt.subplots(2, 1, figsize=(7.2, 6.2), sharex=True)
    if cav:
        tt = np.array([r[0] for r in cav], float)
        vol = np.array([r[4] for r in cav], float) * 1e9  # mm^3
        ax[0].plot(tt, vol, color="C0")
        ax[0].set_ylabel("cavity volume [mm³]")
    if cl:
        # zWireMax is the 20th numeric column (index 19) in the writer.
        # Fall back to column 19 only when the row is long enough.
        zt, zz = [], []
        for r in cl:
            if len(r) > 19 and isinstance(r[19], float) and r[19] > -0.4:
                zt.append(r[0])
                zz.append(r[19] * 1e3)
        if zt:
            ax[1].plot(zt, zz, color="C1")
        ax[1].set_ylabel("wire contact z [mm]")
    ax[1].set_xlabel("time [s]")
    fig.suptitle(f"{args.tag}: cavity volume and wire contact height")
    fig.tight_layout()
    fig.savefig(out / f"{args.tag}_cavity_contact.png", dpi=140)
    plt.close(fig)
    print("wrote", out / f"{args.tag}_cavity_contact.png")

    summary = out / f"{args.tag}_summary.csv"
    with summary.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["quantity", "value"])
        if cav:
            w.writerow(["t_last_s", cav[-1][0]])
            w.writerow(["cavity_status_last", cav[-1][1]])
            w.writerow(["cavity_volume_last_m3", cav[-1][4]])
            w.writerow(["cavity_volume_max_m3", max(r[4] for r in cav)])
        if por:
            # time nPores nLocked nEntrapment nLackOfFusion nKeyhole ...
            w.writerow(["pores_last", por[-1][1] if len(por[-1]) > 1 else ""])
            w.writerow(["entrapment_last", por[-1][3] if len(por[-1]) > 3 else ""])
            w.writerow(["lackOfFusion_last", por[-1][4] if len(por[-1]) > 4 else ""])
            w.writerow(["keyhole_last", por[-1][5] if len(por[-1]) > 5 else ""])
        ev = case / "postProcessing" / "wireCavity" / "events.dat"
        n_pinch = n_close = 0
        if ev.is_file():
            for line in ev.read_text().splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                if "pinchoff" in line:
                    n_pinch += 1
                if "closure" in line:
                    n_close += 1
        w.writerow(["pinchoff_events", n_pinch])
        w.writerow(["closure_events", n_close])
    print("wrote", summary)


if __name__ == "__main__":
    main()
