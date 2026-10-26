#!/usr/bin/env python3
"""Zoomed centre-plane neck next to a crop of the radiograph.

Metal is dark on yellow. Bins are 0.02 mm so a 0.05 mm slit is not averaged
away. Trailing side (+x) is on the left. Skips a tag that has no side-plane
write yet.

    /home/asb6102/lwded-viz/bin/python results/calibration/taosun03/render_slit_neck.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CASES = ROOT / "cases"
RADIO = mpimg.imread(ROOT / "results/calibration/radiograph.png")

CMAP = LinearSegmentedColormap.from_list(
    "metal_dark_yellow",
    ["#f4d35e", "#c48a2a", "#5c3a16", "#1a120c"],
)
YELLOW = "#f4d35e"

# Wire at x = 0. The slit is on +x, z about 0.75-1.2 mm.
X0, X1 = -0.15e-3, 1.35e-3
Z0, Z1 = 0.40e-3, 1.90e-3
DX = 0.02e-3


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


def side_roots(case):
    roots = [case / "postProcessing" / "sidePlane"]
    roots.extend(sorted(case.glob("processor*/postProcessing/sidePlane")))
    return [r for r in roots if r.is_dir()]


def latest_side(case):
    """Latest centre-plane sample, stitched across processor writes."""
    best_t = None
    files = []
    for root in side_roots(case):
        for d in root.iterdir():
            if not d.is_dir():
                continue
            try:
                tv = float(d.name)
            except ValueError:
                continue
            raw = d / "alpha.metal_xz.raw"
            if not raw.is_file():
                continue
            if best_t is None or tv > best_t + 1e-9:
                best_t = tv
                files = [raw]
            elif abs(tv - best_t) <= 1e-9:
                files.append(raw)
    if not files:
        return None
    return best_t, files


def raster(x, z, val):
    xe = np.linspace(X0, X1, int(round((X1 - X0) / DX)) + 1)
    ze = np.linspace(Z0, Z1, int(round((Z1 - Z0) / DX)) + 1)
    m = (x >= X0) & (x <= X1) & (z >= Z0) & (z <= Z1) & np.isfinite(val)
    H, _, _ = np.histogram2d(x[m], z[m], bins=[xe, ze], weights=val[m])
    C, _, _ = np.histogram2d(x[m], z[m], bins=[xe, ze])
    img = np.full(H.T.shape, np.nan)
    hit = C.T > 0
    avg = np.zeros(H.T.shape, dtype=float)
    np.divide(H.T, C.T, out=avg, where=hit)
    img[hit] = avg[hit]
    img = np.where(np.isnan(img), 0.0, img)
    img = img[:, ::-1]
    extent = [X1 * 1e3, X0 * 1e3, Z0 * 1e3, Z1 * 1e3]
    return img, extent


def radio_crop():
    """Neck of the radiograph: wire, slit, and the tall trailing dome."""
    h, w = RADIO.shape[:2]
    # The specimen sits in the middle of the photograph. The slit is the
    # thin dark line on the trailing face, under the notch.
    r0, r1 = int(0.18 * h), int(0.62 * h)
    c0, c1 = int(0.28 * w), int(0.78 * w)
    return RADIO[r0:r1, c0:c1]


def render(tag):
    case = CASES / f"wire_cavity_{tag}"
    side = latest_side(case)
    if side is None:
        print("no side plane", tag)
        return None
    t, files = side
    chunks = []
    for raw in files:
        alpha = load_raw(raw)
        if alpha is not None and len(alpha):
            chunks.append(alpha)
    if not chunks:
        print("no alpha", tag)
        return None
    alpha = np.vstack(chunks)
    img, extent = raster(alpha[:, 0], alpha[:, 2], alpha[:, 3])
    fig, ax = plt.subplots(1, 2, figsize=(8.2, 4.6))
    fig.patch.set_facecolor("#f7f1dc")
    ax[0].imshow(radio_crop())
    ax[0].set_title("Radiograph neck")
    ax[0].axis("off")
    ax[1].imshow(
        img, origin="lower", extent=extent, cmap=CMAP,
        vmin=0.0, vmax=1.0, interpolation="nearest", aspect="equal",
    )
    ax[1].set_facecolor(YELLOW)
    ax[1].set_title(f"{tag}  centre plane  t = {t:.2f} s")
    ax[1].set_xlabel("trailing  ←  x [mm]  →  leading")
    ax[1].set_ylabel("z [mm]")
    fig.tight_layout()
    dest = OUT / f"{tag}_slit_neck.png"
    fig.savefig(dest, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("wrote", dest)
    return dest


def main():
    if len(sys.argv) > 1:
        tags = sys.argv[1:]
    else:
        tags = [f"smoke{s}" for s in "ABCDEF"]
        tags += [f"cal{n}" for n in range(167, 194)]
    wrote = []
    for tag in tags:
        dest = render(tag)
        if dest is not None:
            wrote.append(dest)
    if wrote:
        # Contact sheet of whatever has a side plane, up to 6.
        n = min(6, len(wrote))
        fig, ax = plt.subplots(1, n + 1, figsize=(3.1 * (n + 1), 3.6))
        fig.patch.set_facecolor("#f7f1dc")
        ax[0].imshow(radio_crop())
        ax[0].set_title("Radiograph")
        ax[0].axis("off")
        for i, dest in enumerate(wrote[:n]):
            ax[i + 1].imshow(mpimg.imread(dest))
            ax[i + 1].set_title(dest.name.replace("_slit_neck.png", ""))
            ax[i + 1].axis("off")
        fig.tight_layout()
        sheet = OUT / "slit_neck_contact.png"
        fig.savefig(sheet, dpi=120, facecolor=fig.get_facecolor())
        plt.close(fig)
        print("wrote", sheet)


if __name__ == "__main__":
    main()
