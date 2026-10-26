#!/usr/bin/env python3
"""Radiograph-style panels for the intact score-8 domes.

Metal is dark on a yellow ground. Samples are binned onto a regular grid, so
the side view has no triangulation holes. Trailing side (+x) is on the left.

    python3 results/calibration/taosun03/render_radiograph_panels.py
"""
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

# alpha = 0 is yellow, alpha = 1 is near-black. No white in the map.
CMAP = LinearSegmentedColormap.from_list(
    "metal_dark_yellow",
    ["#f4d35e", "#c48a2a", "#5c3a16", "#1a120c"],
)
YELLOW = "#f4d35e"
WIRE_R = 0.55e-3
TSOL = 1658.0

# Latest write at which the dome was still the score-8 shape. Confirmed
# against the side-plane heights before the crest fell.
TIMES = {
    "cal113": 0.60,
    "cal114": 0.70,
    "cal117": 0.70,
    "cal127": 0.60,
    "cal131": 0.70,
    "cal138": 0.50,
    "cal140": 0.70,
}
# Contact sheet: fused dome, notch, trailing side higher, plate wetted.
BEST = ["cal113", "cal117", "cal140"]

X0, X1 = -1.4e-3, 4.2e-3   # physical x, leading to trailing
Z0, Z1 = -0.45e-3, 2.9e-3
DX = 0.07e-3


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


def plane_dir(case, t):
    root = case / "postProcessing" / "sidePlane"
    if not root.is_dir():
        return None
    best = None
    bestd = 1e9
    for d in root.iterdir():
        if not d.is_dir():
            continue
        try:
            tv = float(d.name)
        except ValueError:
            continue
        if abs(tv - t) < bestd:
            bestd = abs(tv - t)
            best = (tv, d)
    return best


def crest(alpha, temp):
    """Trailing and leading crest, mm, outside the cold wire."""
    if alpha is None:
        return None, None
    tmap = temp[:, 3] if temp is not None and len(temp) == len(alpha) else None
    r = np.hypot(alpha[:, 0], alpha[:, 1])
    metal = alpha[:, 3] > 0.5
    above = alpha[:, 2] > 0.05e-3
    cold = metal & (r < WIRE_R) & above
    if tmap is not None:
        cold = cold & (tmap < TSOL)
    bead = metal & above & ~cold
    trail = bead & (alpha[:, 0] > WIRE_R)
    lead = bead & (alpha[:, 0] < -WIRE_R)
    tr = float(alpha[trail, 2].max() * 1e3) if trail.any() else None
    ld = float(alpha[lead, 2].max() * 1e3) if lead.any() else None
    return tr, ld


def edges(a0, a1, step):
    n = int(round((a1 - a0) / step))
    return np.linspace(a0, a1, n + 1)


def fill_specks(img):
    """Fill isolated empty pixels. Leave a hole that has empty neighbours."""
    out = img.copy()
    nan = np.isnan(out)
    if not nan.any():
        return out
    finite = ~nan
    acc = np.zeros_like(out)
    cnt = np.zeros(out.shape, dtype=np.int16)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            shifted = np.zeros_like(out)
            mask = np.zeros(out.shape, dtype=bool)
            si = slice(max(di, 0), out.shape[0] + min(di, 0))
            sj = slice(max(dj, 0), out.shape[1] + min(dj, 0))
            ti = slice(max(-di, 0), out.shape[0] + min(-di, 0))
            tj = slice(max(-dj, 0), out.shape[1] + min(-dj, 0))
            shifted[ti, tj] = np.where(finite[si, sj], out[si, sj], 0.0)
            mask[ti, tj] = finite[si, sj]
            acc += shifted
            cnt += mask
    speck = nan & (cnt >= 6)
    out[speck] = acc[speck] / cnt[speck]
    return out


def raster(x, z, val):
    """Bin onto a grid. Column 0 is the trailing side. Empty stays yellow (0)."""
    xe = edges(X0, X1, DX)
    ze = edges(Z0, Z1, DX)
    m = (x >= X0) & (x <= X1) & (z >= Z0) & (z <= Z1) & np.isfinite(val)
    H, _, _ = np.histogram2d(x[m], z[m], bins=[xe, ze], weights=val[m])
    C, _, _ = np.histogram2d(x[m], z[m], bins=[xe, ze])
    img = np.full(H.T.shape, np.nan)  # (nz, nx), column 0 is the leading side
    hit = C.T > 0
    avg = np.zeros(H.T.shape, dtype=float)
    np.divide(H.T, C.T, out=avg, where=hit)
    img[hit] = avg[hit]
    img = fill_specks(img)
    img = np.where(np.isnan(img), 0.0, img)
    # Column 0 of the histogram is the leading side. imshow draws column 0
    # on the left, so flip. The extent labels that left edge as +x.
    img = img[:, ::-1]
    extent = [X1 * 1e3, X0 * 1e3, Z0 * 1e3, Z1 * 1e3]
    return img, extent


def draw_field(ax, img, extent, title, vmax=1.0):
    im = ax.imshow(
        img, origin="lower", extent=extent, cmap=CMAP,
        vmin=0.0, vmax=vmax, interpolation="bilinear", aspect="equal",
    )
    ax.set_facecolor(YELLOW)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("trailing  ←  x [mm]  →  leading")
    ax.set_ylabel("z [mm]")
    return im


def load_volume(case, t):
    import pyvista as pv
    reader = pv.OpenFOAMReader(str(case / "case.foam"))
    times = list(reader.time_values)
    if not times:
        raise RuntimeError("no times in " + str(case))
    tuse = min(times, key=lambda tv: abs(tv - t))
    reader.set_active_time_value(tuse)
    data = reader.read()
    mesh = data["internalMesh"] if "internalMesh" in data.keys() else data[0]
    if "alpha.metal" in mesh.cell_data:
        alpha = np.asarray(mesh.cell_data["alpha.metal"], dtype=float)
        pts = np.asarray(mesh.cell_centers().points)
    else:
        alpha = np.asarray(mesh["alpha.metal"], dtype=float)
        pts = np.asarray(mesh.points)
    sized = mesh.compute_cell_sizes(length=False, area=False, volume=True)
    vol = np.asarray(sized.cell_data["Volume"], dtype=float)
    if len(vol) != len(alpha):
        vol = np.ones(len(alpha))
    return pts, alpha, vol, tuse


def cavity_open(case, t):
    path = case / "postProcessing" / "wireCavity" / "wireCavity.dat"
    if not path.is_file():
        return True
    best = None
    bestd = 1e9
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        try:
            tv = float(parts[0])
            vol = float(parts[4])
        except (IndexError, ValueError):
            continue
        d = abs(tv - t)
        if d < bestd:
            bestd = d
            best = (int(float(parts[1])), vol)
    if best is None:
        return True
    status, vol = best
    return status != 0 and vol > 1e-12


def render(tag, centers):
    case = CASES / f"wire_cavity_{tag}"
    t_req = TIMES[tag]
    found = plane_dir(case, t_req)
    if found is None:
        raise SystemExit(f"{tag}: no sidePlane")
    t, directory = found
    alpha = load_raw(directory / "alpha.metal_xz.raw")
    temp = load_raw(directory / "T_xz.raw")
    trail, lead = crest(alpha, temp)
    print(f"{tag}: center plane t={t:.2f} s  trail={trail}  lead={lead}")

    center, extent = raster(alpha[:, 0], alpha[:, 2], alpha[:, 3])
    centers[tag] = (center, extent, t, trail, lead)

    pts, aval, vol, tvol = load_volume(case, t)
    # Wake cut. The open-cavity centroid on these half-domain runs sits near y = 1 mm.
    band = np.abs(pts[:, 1] - 1.0e-3) <= 0.18e-3
    if band.sum() < 30:
        band = np.abs(pts[:, 1] - 1.0e-3) <= 0.35e-3
    wake, _ = raster(pts[band, 0], pts[band, 2], aval[band])
    # Projection: metal thickness along y, radiograph sense (thicker = darker).
    depth = aval * vol
    H, _ = raster(pts[:, 0], pts[:, 2], depth)
    positive = H[H > 0]
    vmax = float(np.percentile(positive, 99)) if positive.size else 1.0

    fig, ax = plt.subplots(2, 2, figsize=(11.2, 8.4))
    fig.patch.set_facecolor("#f7f1dc")
    ax[0, 0].imshow(RADIO)
    ax[0, 0].set_title("Radiograph (trailing side on the left)")
    ax[0, 0].axis("off")
    draw_field(
        ax[0, 1], H, extent,
        f"{tag}  metal projected along y",
        vmax=vmax,
    )
    draw_field(
        ax[1, 0], center, extent,
        f"center plane  y = 0.02 mm   t = {t:.2f} s",
    )
    if cavity_open(case, t):
        ynote = f"wake cut  y = 1.0 mm   t = {tvol:.2f} s"
    else:
        ynote = f"y = 1.0 mm (no cavity reported)   t = {tvol:.2f} s"
    draw_field(ax[1, 1], wake, extent, ynote)
    for a in ax[0, 1], ax[1, 0], ax[1, 1]:
        a.set_xlim(extent[0], extent[1])
        a.set_ylim(extent[2], extent[3])
    fig.tight_layout()
    dest = OUT / f"{tag}_vs_radiograph.png"
    fig.savefig(dest, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("wrote", dest)


def contact_sheet(centers):
    fig, ax = plt.subplots(1, 4, figsize=(14.5, 4.3))
    fig.patch.set_facecolor("#f7f1dc")
    ax[0].imshow(RADIO)
    ax[0].set_title("Radiograph")
    ax[0].axis("off")
    for i, tag in enumerate(BEST, start=1):
        img, extent, t, trail, lead = centers[tag]
        tr = "-" if trail is None else f"{trail:.2f}"
        ld = "-" if lead is None else f"{lead:.2f}"
        draw_field(
            ax[i], img, extent,
            f"{tag}   t = {t:.2f} s\ntrail {tr} / lead {ld} mm",
        )
        ax[i].set_xlim(extent[0], extent[1])
        ax[i].set_ylim(extent[2], extent[3])
    fig.tight_layout()
    dest = OUT / "best3_vs_radiograph.png"
    fig.savefig(dest, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("wrote", dest)


def main():
    centers = {}
    for tag in TIMES:
        render(tag, centers)
    contact_sheet(centers)


if __name__ == "__main__":
    main()
