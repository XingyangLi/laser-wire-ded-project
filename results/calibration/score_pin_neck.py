#!/usr/bin/env python3
"""Neck gap, bead volume and timestep for a fine-pin case.

Width and depth use the center-plane sample. A film in the target band is
0.03–0.08 mm wide, at least 0.25 mm deep, open, and steady for at least 4 ms.
sigma factors, when present, are an imposed numerical enhancement.
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_slit_neck import CROP, draw_neck  # noqa: E402
from render_cal95b_cal105 import (  # noqa: E402
    cell_centres,
    gather,
    load_addressing,
    read_face_pack,
    read_labels,
    read_points,
    written_times,
)
from slit_metric import fmt, measure  # noqa: E402

ROOT = Path("/home/xingyang/laser-wire-ded-project")
WIRE_R = 0.50


def crest_gap(x, y, z, alpha):
    """Gap on the trailing face where the line actually travels, z = 1.20–1.95 mm.

    Width is the first metal outside a gas face. Depth is the contiguous run.
    """
    edges = np.arange(1.20, 1.95, 0.02)
    spans = []
    i = 0
    while i < len(edges):
        z0 = edges[i]
        face = (y < 0.08) & (z >= z0) & (z < z0 + 0.02) & (x >= 0.48) & (x < 0.56)
        metal = (y < 0.08) & (z >= z0) & (z < z0 + 0.02) & (x >= 0.48) & (x < 1.1) & (alpha >= 0.5)
        gas_face = face.any() and float(np.mean(alpha[face] < 0.5)) > 0.6 and metal.any()
        if not gas_face:
            i += 1
            continue
        width = float(x[metal].min()) - WIRE_R
        if not (0.02 <= width <= 0.12):
            i += 1
            continue
        j = i
        widths = []
        while j < len(edges):
            z1 = edges[j]
            face = (y < 0.08) & (z >= z1) & (z < z1 + 0.02) & (x >= 0.48) & (x < 0.56)
            metal = (y < 0.08) & (z >= z1) & (z < z1 + 0.02) & (x >= 0.48) & (x < 1.1) & (alpha >= 0.5)
            if not (face.any() and float(np.mean(alpha[face] < 0.5)) > 0.6 and metal.any()):
                break
            w = float(x[metal].min()) - WIRE_R
            if not (0.02 <= w <= 0.12):
                break
            widths.append(w)
            j += 1
        depth = edges[j - 1] + 0.02 - edges[i]
        spans.append((depth, float(np.median(widths)), float(edges[i]), float(edges[j - 1] + 0.02)))
        i = j
    if not spans:
        return None
    spans.sort(reverse=True)
    depth, width, zlo, zhi = spans[0]
    return dict(depth_mm=depth, width_mm=width, z_lo_mm=zlo, z_hi_mm=zhi, open=zhi > 1.70)


def neck_row(x, y, z, alpha):
    near = (y < 0.10) & (x > 0.40) & (x < 1.30) & (z > 0.40) & (z < 1.90)
    row = measure(x[near], z[near], alpha[near])
    face = (y < 0.10) & (z > 0.45) & (z < 1.55) & (x > 0.48) & (x < 0.60)
    crest = (y < 0.12) & (x > 0.48) & (x < 0.70) & (z > 1.60) & (z < 1.95) & (alpha < 0.5)
    foot = (z > 0) & (z < 0.25) & (x > 0.5) & (x < 3.5) & (y < 0.8) & (alpha < 0.5)
    metal = face & (alpha >= 0.5)
    offset = float(x[metal].min()) - WIRE_R if metal.any() else None
    n_metal = int((alpha >= 0.5).sum())
    return row, offset, int(crest.sum()), int(foot.sum()), n_metal


def log_stats(case):
    path = Path(case) / "log.laserWireDEDFoam"
    if not path.is_file():
        return {}
    dts = []
    last_pin = ""
    last_t = None
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("deltaT"):
            dts.append(float(line.split("=", 1)[1]))
        elif line.startswith("LinePin:"):
            last_pin = line
        elif line.startswith("Time ="):
            last_t = float(line.split("=", 1)[1])
    out = {"last_t": last_t, "last_pin": last_pin}
    if dts:
        out["dt_min"] = min(dts)
        out["dt_last"] = dts[-1]
    return out


def figure(path, x, z, alpha, title):
    radio = plt.imread(ROOT / "results/calibration/radiograph.png")
    l, t, r, b = CROP
    crop = radio[t:b, l:r]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.8))
    axes[0].imshow(crop, cmap="gray")
    axes[0].set_title("Radiograph, neck", fontsize=9)
    axes[0].axis("off")
    draw_neck(axes[1], x, z, alpha, title)
    fig.suptitle(
        "Center plane. Dark is metal, white is gas.\n"
        "Green dash: trailing face. The shell on the wall is imposed; the bead outside it is free.",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    print("wrote", path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--time", default="", help="time to draw; default is the last written")
    args = ap.parse_args()
    case = Path(args.case)
    mesh = case / "constant/polyMesh"
    points = read_points(mesh / "points")
    offs, labels = read_face_pack(mesh / "faces")
    owner = read_labels(mesh / "owner")
    neighbour = read_labels(mesh / "neighbour")
    centres = cell_centres(points, offs, labels, owner, neighbour)
    nproc = len(list(case.glob("processor*")))
    addressing = load_addressing(case, nproc)
    x = centres[:, 0] * 1e3
    y = centres[:, 1] * 1e3
    z = centres[:, 2] * 1e3
    times = written_times(case, nproc)
    print(args.tag, "written", times)
    stats = log_stats(case)
    if stats:
        print(
            f"  solver t={stats.get('last_t')}  "
            f"dt_min={stats.get('dt_min')}  dt_last={stats.get('dt_last')}"
        )
        print(" ", stats.get("last_pin", ""))
    drawn = None
    want = args.time or (times[-1] if times else "")
    for tname in times:
        alpha = gather(case, tname, centres.shape[0], addressing, "alpha.metal")
        if alpha is None:
            print(f"  t={tname}: incomplete")
            continue
        row, offset, n_crest, n_foot, n_metal = neck_row(x, y, z, alpha)
        gap = crest_gap(x, y, z, alpha)
        off = "—" if offset is None else f"{offset:.3f} mm"
        gap_s = "no crest gap"
        if gap is not None:
            gap_s = (
                f"crest gap width {gap['width_mm']:.3f} mm "
                f"depth {gap['depth_mm']:.3f} mm "
                f"z {gap['z_lo_mm']:.2f}–{gap['z_hi_mm']:.2f}"
            )
        print(
            f"  t={tname}: {fmt(row)}; fine-neck wall offset {off}; "
            f"{gap_s}; crest gas {n_crest}; plate-film {n_foot}; metal cells {n_metal}"
        )
        if tname == want:
            drawn = (x, z, alpha, gap, n_crest)
    if args.out and drawn is not None:
        x, z, alpha, gap, n_crest = drawn
        if gap is None:
            title = f"{args.tag}  t={want} s\nno open crest gap\ncrest gas cells {n_crest}"
        else:
            title = (
                f"{args.tag}  t={want} s\n"
                f"imposed shell: width {gap['width_mm']:.3f} mm, "
                f"depth {gap['depth_mm']:.3f} mm"
            )
        # The neck plot wants the symmetry-plane sample, trailing +x.
        m = (y < 0.12)
        figure(Path(args.out), x[m], z[m], alpha[m], title)


if __name__ == "__main__":
    main()
