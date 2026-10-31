#!/usr/bin/env python3
"""Post-process one enlarged 2D slit case. Run from the case directory later.

Writes report.txt, a neck render and a whole-domain render into this folder.
Gas entry on these cases is imposed. The pictures are not mirrored.
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

CASE = Path(__file__).resolve().parent
R = 0.5e-3


def foam_block(path):
    text = Path(path).read_text(errors="replace")
    rest = text[text.find("\n", text.find("// * * *")):].strip()
    nl = rest.find("\n")
    body = rest[nl:]
    return body[body.find("(") + 1:body.rfind(")")]


def read_mesh():
    mesh = CASE / "constant/polyMesh"
    inner = foam_block(mesh / "points")
    pts = np.asarray([
        [float(v) for v in line.strip("()").split()]
        for line in inner.splitlines() if line.strip().startswith("(")
    ])
    own = np.asarray([int(v) for v in foam_block(mesh / "owner").split()], dtype=np.int32)
    faces = []
    for tok in foam_block(mesh / "faces").replace("\n", " ").split(")"):
        k = tok.find("(")
        if k < 0:
            continue
        faces.append([int(v) for v in tok[k + 1:].split()])
    n = int(own.max()) + 1
    xmin = np.full(n, np.inf)
    xmax = -xmin.copy()
    ymin = np.full(n, np.inf)
    ymax = -ymin.copy()
    zmin = ymin.copy()
    zmax = -ymin.copy()
    for f, ids in enumerate(faces):
        if f >= len(own):
            break
        fp = pts[np.asarray(ids)]
        c = own[f]
        xmin[c] = min(xmin[c], fp[:, 0].min())
        xmax[c] = max(xmax[c], fp[:, 0].max())
        ymin[c] = min(ymin[c], fp[:, 1].min())
        ymax[c] = max(ymax[c], fp[:, 1].max())
        zmin[c] = min(zmin[c], fp[:, 2].min())
        zmax[c] = max(zmax[c], fp[:, 2].max())
    return xmin, xmax, ymin, ymax, zmin, zmax


def read_scalar(path):
    text = Path(path).read_text(errors="replace")
    rest = text[text.find("internalField"):]
    rest = rest[rest.find("\n") + 1:]
    nline = rest[:rest.find("\n")].strip()
    if nline.startswith("uniform"):
        return float(nline.split()[1])
    n = int(nline)
    return np.asarray([float(v) for v in rest[rest.find("(") + 1:].split(")")[0].split()[:n]])


def boundary_values(text):
    body = text[text.find("boundaryField"):]
    out = {}
    pos = 0
    while True:
        k = body.find("value", pos)
        if k < 0:
            break
        head = body[max(0, k - 500):k]
        brace = head.rfind("{")
        name = head[:brace].strip().split()[-1]
        seg = body[k:k + 40]
        if "uniform" in seg and "nonuniform" not in seg:
            out[name] = float(body[k:].split("uniform", 1)[1].split()[0].strip(";"))
            pos = k + 5
            continue
        p = body.find("(", k)
        q = body.find(")", p)
        vals = []
        for tok in body[p + 1:q].split():
            try:
                vals.append(float(tok))
            except ValueError:
                pass
        out[name] = np.asarray(vals, dtype=float)
        pos = q + 1
    return out


def times():
    found = []
    for p in CASE.iterdir():
        try:
            found.append((float(p.name), p))
        except ValueError:
            pass
    return sorted(found)


def slit(xmin, xmax, zmin, zmax, alpha):
    xc = 0.5 * (xmin + xmax)
    zc = 0.5 * (zmin + zmax)
    near = xc < 0.7e-3
    dx = float(np.median((xmax - xmin)[near])) if near.any() else 5e-6
    rows = []
    z = 1.15e-3
    while z < 1.75e-3:
        m = (np.abs(zc - z) <= 0.55 * dx) & (xc < 1.3e-3) & (alpha >= 0.5)
        if m.any():
            gap = float(xmin[m].min() - R)
            wall = (np.abs(zc - z) <= 0.55 * dx) & (xmin < R + 0.6 * dx)
            wa = float(alpha[wall].max()) if wall.any() else 1.0
            if wa < 0.5 and dx < gap < 0.08e-3:
                rows.append((z, gap))
        z += dx
    if not rows:
        return dx, 0.0, 0.0
    depth = (rows[-1][0] - rows[0][0]) * 1e3
    return dx, depth, rows[-1][1] * 1e3


def metal_and_flux(xmin, xmax, ymin, ymax, zmin, zmax):
    vol = (xmax - xmin) * (ymax - ymin) * (zmax - zmin)
    rows = []
    for t, d in times():
        ap = d / "alpha.metal"
        if not ap.is_file():
            continue
        alpha = read_scalar(ap)
        if np.isscalar(alpha):
            vm = float(alpha) * float(vol.sum())
            alpha = np.full(len(vol), float(alpha))
        else:
            vm = float((alpha[:len(vol)] * vol).sum())
        below = float((alpha[:len(vol)] * vol)[zmax[:len(alpha)] <= 0].sum()) if len(alpha) == len(vol) else 0.0
        fl_below = 0.0
        fp = d / "liquidFraction"
        if fp.is_file() and len(alpha) == len(vol):
            fl = read_scalar(fp)
            if not np.isscalar(fl):
                fl_below = float(((fl > 0.05) & (zmax <= 0)).sum())
        net = {}
        pp = d / "phi"
        if pp.is_file():
            phi = boundary_values(pp.read_text(errors="replace"))
            al = boundary_values(ap.read_text(errors="replace"))
            for name, ph in phi.items():
                if name not in al or name == "frontAndBack":
                    continue
                a = al[name]
                ph = np.atleast_1d(np.asarray(ph, dtype=float))
                a = np.full(len(ph), float(a)) if np.isscalar(a) else np.asarray(a, dtype=float)
                n = min(len(ph), len(a))
                net[name] = float((a[:n] * ph[:n]).sum())
        rows.append((t, vm, below, fl_below, net))
    return rows


def draw(xmin, xmax, zmin, zmax, alpha, fl, window, path, title):
    xc = 0.5 * (xmin + xmax)
    zc = 0.5 * (zmin + zmax)
    x0, x1, z0, z1 = window
    m = (xc > x0) & (xc < x1) & (zc > z0) & (zc < z1)
    gx = np.linspace(x0, x1, 480)
    gz = np.linspace(z0, z1, 420)
    X, Z = np.meshgrid(gx, gz)
    pts = np.column_stack([xc[m], zc[m]])
    A = griddata(pts, alpha[m], (X, Z), method="linear")
    F = griddata(pts, fl[m], (X, Z), method="linear") if fl is not None else None
    gas = np.array([0.76, 0.88, 0.96])
    metal = np.array([0.55, 0.50, 0.46])
    rgb = np.ones(A.shape + (3,))
    ok = np.isfinite(A)
    tt = np.clip(np.where(ok, A, 0), 0, 1)[..., None]
    rgb[ok] = (1 - tt[ok]) * gas + tt[ok] * metal
    fig, ax = plt.subplots(figsize=(5.4, 6.2), dpi=140)
    ax.imshow(rgb, origin="lower",
              extent=[x0 * 1e3, x1 * 1e3, z0 * 1e3, z1 * 1e3],
              interpolation="bilinear", aspect="equal")
    ax.contour(X * 1e3, Z * 1e3, np.ma.array(A, mask=~ok), levels=[0.5],
               colors="black", linewidths=0.7)
    if F is not None:
        show = np.ma.masked_where(~np.isfinite(F) | (F < 0.05), F)
        ax.contourf(X * 1e3, Z * 1e3, show, levels=[0.05, 0.5, 1.01],
                    colors=["#f4a26180", "#e76f5180"], zorder=2)
    ax.axhline(0.0, color="green", lw=0.8, label="plate z = 0")
    ax.axvspan(min(x0, 0.4e-3) * 1e3, 0.50, color="#2b2b2b", zorder=3)
    ax.set_xlim(x0 * 1e3, x1 * 1e3)
    ax.set_ylim(z0 * 1e3, z1 * 1e3)
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("z [mm]")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor="white")
    plt.close(fig)


def main():
    xmin, xmax, ymin, ymax, zmin, zmax = read_mesh()
    series = metal_and_flux(xmin, xmax, ymin, ymax, zmin, zmax)
    lines = ["2D, optimistic, gas entry imposed", ""]
    cum = {}
    prev = None
    lines.append("time_s  Vmetal_m3  Vmetal_below_z0  nCells_fl>0.05_below_z0")
    for t, vm, below, nfl, net in series:
        lines.append(f"{t:.4f}  {vm:.6e}  {below:.6e}  {nfl:.0f}")
        if prev is not None:
            dt = t - prev[0]
            names = set(cum) | set(prev[4]) | set(net)
            for name in names:
                cum[name] = cum.get(name, 0.0) + 0.5 * (prev[4].get(name, 0.0) + net.get(name, 0.0)) * dt
        prev = (t, vm, below, nfl, net)
    depth = mouth = 0.0
    dx = 0.0
    tdir = None
    if series:
        for t, dpath in times():
            if abs(t - series[-1][0]) < 1e-9:
                tdir = dpath
        alpha = read_scalar(tdir / "alpha.metal")
        if not np.isscalar(alpha):
            dx, depth, mouth = slit(xmin, xmax, zmin, zmax, alpha)
        fl = read_scalar(tdir / "liquidFraction") if (tdir / "liquidFraction").is_file() else None
        if np.isscalar(fl):
            fl = np.full(len(xmin), float(fl))
        if not np.isscalar(alpha):
            draw(xmin, xmax, zmin, zmax, alpha, fl,
                 (0.45e-3, 1.15e-3, -0.3e-3, 1.75e-3),
                 CASE / "neck_t8ms.png",
                 "2D, optimistic, gas entry imposed\nneck, not mirrored")
            draw(xmin, xmax, zmin, zmax, alpha, fl,
                 (0.45e-3, 3.9e-3, -1.9e-3, 3.4e-3),
                 CASE / "domain_t8ms.png",
                 "2D, optimistic, gas entry imposed\nwhole domain, not mirrored")
    lines.insert(1, f"dx_um {dx*1e6:.2f}  slit_depth_mm {depth:.3f}  mouth_mm {mouth:.3f}")
    lines.append("")
    lines.append("cumulative net metal volume flux out of the domain [m3], from saved frames")
    for name, val in sorted(cum.items()):
        lines.append(f"  {name}  {val:.6e}")
    if series:
        loss = series[0][1] - series[-1][1]
        lines.append(f"metal loss start-to-end {loss:.6e}")
        lines.append(f"sum of boundary integrals {sum(cum.values()):.6e}")
    (CASE / "report.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
