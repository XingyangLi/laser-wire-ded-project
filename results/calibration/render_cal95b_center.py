#!/usr/bin/env python3
"""Centre-plane movies of cal95b. No mirror.

Written fields are every 0.2 s. Frames between those times are linear blends
of alpha, T and U on the static mesh. A re-solve was not started.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.tri import Triangulation
import imageio.v2 as imageio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_half_bead import read_labels, read_points, read_scalar  # noqa: E402
from render_cal95b_cal105 import cell_centres, read_face_pack  # noqa: E402

ROOT = Path("/home/xingyang/laser-wire-ded-project")
CASE = ROOT / "cases/wire_cavity_cal95b"
OUT = ROOT / "results/calibration"
TIMES = [0.0, 0.2, 0.4, 0.6, 0.8]
SOLIDUS = 1658.0
FPS = 30
# 0.8 s of bead time over 8 s of video.
NFRAMES = 8 * FPS
X0, X1 = -3.0, 3.0
Z0, Z1 = 0.0, 2.5


def read_vector(path):
    data = Path(path).read_bytes()
    key = b"internalField   nonuniform List<vector> \n"
    i = data.find(key)
    if i < 0:
        key = b"internalField   nonuniform List<vector>\n"
        i = data.find(key)
    if i < 0:
        raise SystemExit(f"no vector field in {path}")
    j = i + len(key)
    nl = data.find(b"\n", j)
    n = int(data[j:nl])
    start = nl + 1
    if data[start:start + 1] == b"(":
        start += 1
    return np.frombuffer(data, dtype="<f8", count=n * 3, offset=start).copy().reshape(n, 3)


def blend(stack, times, t):
    """stack shape (nt, n). Linear in time."""
    k = int(np.searchsorted(times, t, side="right") - 1)
    k = min(max(k, 0), len(times) - 2)
    den = times[k + 1] - times[k]
    f = 0.0 if den <= 0 else (t - times[k]) / den
    return (1 - f) * stack[k] + f * stack[k + 1]


def mask_tri(tri, x, z, limit=0.22):
    xt, zt = x[tri.triangles], z[tri.triangles]
    tri.set_mask((np.ptp(xt, axis=1) > limit) | (np.ptp(zt, axis=1) > limit))
    return tri


def base_ax(fig, title):
    ax = fig.add_axes([0.06, 0.08, 0.78, 0.82])
    ax.set_xlim(X0, X1)
    ax.set_ylim(Z0, Z1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x  [mm]")
    ax.set_ylabel("z  [mm]")
    fig.suptitle(title, fontsize=18, y=0.97)
    ax.text(
        0.02, 0.04, "symmetry plane   y = 0",
        transform=ax.transAxes, va="bottom", ha="left", fontsize=13, color="white",
        bbox=dict(boxstyle="round,pad=0.2", fc="#08306b", ec="none", alpha=0.85),
    )
    return ax


def main():
    mesh = CASE / "constant/polyMesh"
    print("mesh")
    points = read_points(mesh / "points")
    offs, labels = read_face_pack(mesh / "faces")
    owner = read_labels(mesh / "owner")
    neighbour = read_labels(mesh / "neighbour")
    centres = cell_centres(points, offs, labels, owner, neighbour)
    x = centres[:, 0] * 1e3
    y = centres[:, 1] * 1e3
    z = centres[:, 2] * 1e3
    # First cell layer on the symmetry plane, plus a margin around the crop.
    plane = (y < 0.12) & (x > X0 - 0.4) & (x < X1 + 0.4) & (z > Z0 - 0.4) & (z < Z1 + 0.4)
    idx = np.flatnonzero(plane)
    print(f"plane cells {idx.size}")
    xp, zp = x[idx], z[idx]
    ncells = int(max(owner.max(), neighbour.max())) + 1
    inv = np.full(ncells, -1, dtype=np.int32)
    inv[idx] = np.arange(idx.size, dtype=np.int32)
    pair_list = []
    for f in range(neighbour.size):
        i = inv[owner[f]]
        j = inv[neighbour[f]]
        if i < 0 or j < 0:
            continue
        if np.hypot(xp[i] - xp[j], zp[i] - zp[j]) > 0.30:
            continue
        pair_list.append((int(i), int(j)))
    pairs = np.asarray(pair_list, dtype=np.int32)
    print(f"plane links {pairs.shape[0]}")

    alphas, temps, us, vs, ws = [], [], [], [], []
    for t in TIMES:
        name = f"{t:g}" if t > 0 else "0"
        print("load", name)
        alphas.append(read_scalar(CASE / name / "alpha.metal")[idx])
        temps.append(read_scalar(CASE / name / "T")[idx])
        vel = read_vector(CASE / name / "U")[idx]
        us.append(vel[:, 0])
        vs.append(vel[:, 1])
        ws.append(vel[:, 2])
    A = np.vstack(alphas)
    T = np.vstack(temps)
    U = np.vstack(us)
    V = np.vstack(vs)
    W = np.vstack(ws)
    speed = np.sqrt(U ** 2 + V ** 2 + W ** 2)
    melt = A >= 0.5
    sp_melt = speed[melt]
    print(
        f"melt speed m/s  min {sp_melt.min():.4f}  "
        f"p50 {np.median(sp_melt):.4f}  p99 {np.percentile(sp_melt, 99):.4f}  "
        f"max {sp_melt.max():.4f}"
    )
    print(f"T in crop  {T.min():.0f} .. {T.max():.0f} K")
    tnorm = Normalize(vmin=300, vmax=max(2200, float(np.percentile(T[melt], 99))))
    # Fixed arrow scale from the melt, not the gas.
    vmax = max(0.05, float(np.percentile(sp_melt, 99)))
    print(f"velocity key scale {vmax:.3f} m/s")

    tri = mask_tri(Triangulation(xp, zp), xp, zp)
    times = np.asarray(TIMES)
    frame_t = np.linspace(0.0, 0.8, NFRAMES)

    def surface_lines(alpha):
        segs = []
        for i, j in pairs:
            ai, aj = alpha[i], alpha[j]
            if (ai - 0.5) * (aj - 0.5) > 0:
                continue
            den = aj - ai
            if abs(den) < 1e-12:
                continue
            f = (0.5 - ai) / den
            if not (0.0 <= f <= 1.0):
                continue
            px = xp[i] + f * (xp[j] - xp[i])
            pz = zp[i] + f * (zp[j] - zp[i])
            dx = xp[j] - xp[i]
            dz = zp[j] - zp[i]
            L = np.hypot(dx, dz) or 1.0
            # Tangent to the surface, about one cell long.
            tx, tz = -dz / L * 0.11, dx / L * 0.11
            segs.append([(px - tx, pz - tz), (px + tx, pz + tz)])
        return segs

    def draw_temp(ax, alpha, temp):
        ax.tricontourf(tri, temp, levels=24, cmap="inferno", norm=tnorm)
        if temp.min() < SOLIDUS < temp.max():
            ax.tricontour(tri, temp, levels=[SOLIDUS], colors=["#f7f7f7"], linewidths=1.15)
        ax.tricontour(tri, alpha, levels=[0.5], colors=["#00e5ff"], linewidths=1.4)

    print("temperature movie")
    tw = imageio.get_writer(
        OUT / "cal95b_center_temperature.mp4",
        fps=FPS, codec="libx264", quality=8, macro_block_size=1,
    )
    for i, t in enumerate(frame_t):
        a = blend(A, times, t)
        temp = blend(T, times, t)
        fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
        ax = base_ax(fig, f"cal95b   t = {t:.3f} s    temperature")
        draw_temp(ax, a, temp)
        sm = plt.cm.ScalarMappable(norm=tnorm, cmap="inferno")
        sm.set_array([])
        cax = fig.add_axes([0.86, 0.14, 0.02, 0.68])
        cb = fig.colorbar(sm, cax=cax)
        cb.set_label("T  [K]", fontsize=14)
        ax.plot([], [], color="#f7f7f7", lw=1.6, label=f"solidus  {SOLIDUS:.0f} K")
        ax.plot([], [], color="#00e5ff", lw=1.6, label="free surface")
        ax.legend(loc="upper right", fontsize=11, framealpha=0.9)
        fig.canvas.draw()
        w, h = fig.canvas.get_width_height()
        im = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8).reshape(h, w, 3).copy()
        tw.append_data(im)
        plt.close(fig)
        if i % 30 == 0:
            print(f"  T frame {i}/{NFRAMES}")
    tw.close()

    print("flow movie")
    fw = imageio.get_writer(
        OUT / "cal95b_center_flow.mp4",
        fps=FPS, codec="libx264", quality=8, macro_block_size=1,
    )
    snorm = Normalize(vmin=0.0, vmax=vmax)
    # One arrow per cell is dense; keep metal cells on a 0.3 mm lattice.
    for i, t in enumerate(frame_t):
        a = blend(A, times, t)
        temp = blend(T, times, t)
        uu = blend(U, times, t)
        ww = blend(W, times, t)
        sp = np.sqrt(uu ** 2 + blend(V, times, t) ** 2 + ww ** 2)
        fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
        ax = base_ax(fig, f"cal95b   t = {t:.3f} s    melt velocity")
        ax.tricontourf(tri, temp, levels=24, cmap="inferno", norm=tnorm, alpha=0.28)
        ax.tricontour(tri, a, levels=[0.5], colors=["k"], linewidths=1.3)
        show = (a >= 0.5)
        # Thin the arrows so the scale stays readable.
        key = np.round(xp / 0.28).astype(int) * 1000 + np.round(zp / 0.28).astype(int)
        keep = np.zeros(show.shape, dtype=bool)
        seen = set()
        for j in np.flatnonzero(show):
            if key[j] in seen:
                continue
            seen.add(key[j])
            keep[j] = True
        q = ax.quiver(
            xp[keep], zp[keep], uu[keep], ww[keep], sp[keep],
            cmap="viridis", norm=snorm,
            angles="xy", scale_units="xy", scale=vmax / 0.45,
            width=0.003, pivot="mid",
        )
        ax.quiverkey(
            q, 0.86, 1.04, 0.05, "0.05 m/s",
            labelpos="E", coordinates="axes", fontproperties={"size": 12},
        )
        cax = fig.add_axes([0.86, 0.14, 0.02, 0.68])
        cb = fig.colorbar(q, cax=cax)
        cb.set_label("speed  [m/s]", fontsize=14)
        ax.plot([], [], color="k", lw=1.4, label="free surface")
        ax.legend(loc="upper right", fontsize=11, framealpha=0.9)
        fig.canvas.draw()
        w, h = fig.canvas.get_width_height()
        im = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8).reshape(h, w, 3).copy()
        fw.append_data(im)
        plt.close(fig)
        if i % 30 == 0:
            print(f"  U frame {i}/{NFRAMES}")
    fw.close()
    print("done", NFRAMES, "frames at", FPS, "fps")


if __name__ == "__main__":
    main()
