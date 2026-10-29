#!/usr/bin/env python3
"""Centre-plane movies of the 2 s cal95b rerun. One frame per written time.

No interpolation and no mirror. The symmetry plane is y = 0.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.tri import Triangulation
import imageio.v2 as imageio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_cal95b_center import (  # noqa: E402
    X0, X1, Z0, Z1, SOLIDUS, base_ax, mask_tri, read_vector,
)
from render_cal95b_cal105 import (  # noqa: E402
    cell_centres, load_addressing, read_face_pack, written_times,
)
from render_half_bead import read_labels, read_points, read_scalar  # noqa: E402

ROOT = Path("/home/xingyang/laser-wire-ded-project")
CASE = ROOT / "cases/wire_cavity_cal95b_2s"
OUT = ROOT / "results/calibration"
FPS = 30
NPROC = 12


def read_vector_any(path, n_expected):
    data = Path(path).read_bytes()
    i = data.find(b"internalField")
    head = data[i:i + 80]
    if b"uniform" in head and b"nonuniform" not in head:
        text = data[i:i + 160].decode("latin1")
        nums = text.split("(", 1)[1].split(")", 1)[0].split()
        v = np.array([float(x) for x in nums], dtype=np.float64)
        return np.tile(v, (n_expected, 1))
    return read_vector(path)


def gather_vector(case, time_name, n_cells, addressing):
    acc = np.full((n_cells, 3), np.nan)
    for i, addr in enumerate(addressing):
        path = case / f"processor{i}" / time_name / "U"
        if not path.is_file():
            return None
        vals = read_vector_any(path, addr.size)
        if vals.shape[0] != addr.size:
            return None
        acc[addr] = vals
    if np.isnan(acc).any():
        return None
    return acc


def gather_scalar(case, time_name, n_cells, addressing, field):
    acc = np.full(n_cells, np.nan)
    for i, addr in enumerate(addressing):
        path = case / f"processor{i}" / time_name / field
        if not path.is_file():
            return None
        vals = read_scalar(path)
        if vals.size != addr.size:
            return None
        acc[addr] = vals
    if np.isnan(acc).any():
        return None
    return acc


def bead_line(x, z, alpha):
    m = alpha >= 0.5
    if not np.any(m):
        return None
    trail = m & (x > 0.2) & (z > 0.05)
    lead = m & (x < -0.2) & (z > 0.05)
    return dict(
        n=int(m.sum()),
        z_trail=float(z[trail].max()) if np.any(trail) else None,
        z_lead=float(z[lead].max()) if np.any(lead) else None,
        x_foot=float(x[m & (z > 0.05)].max()) if np.any(m & (z > 0.05)) else None,
        x_nose=float(x[m & (z > 0.05)].min()) if np.any(m & (z > 0.05)) else None,
    )


def main():
    mesh = CASE / "constant/polyMesh"
    print("mesh")
    points = read_points(mesh / "points")
    offs, labels = read_face_pack(mesh / "faces")
    owner = read_labels(mesh / "owner")
    neighbour = read_labels(mesh / "neighbour")
    centres = cell_centres(points, offs, labels, owner, neighbour)
    n_cells = centres.shape[0]
    x = centres[:, 0] * 1e3
    y = centres[:, 1] * 1e3
    z = centres[:, 2] * 1e3
    plane = (
        (y < 0.12) & (x > X0 - 0.4) & (x < X1 + 0.4)
        & (z > Z0 - 0.4) & (z < Z1 + 0.4)
    )
    idx = np.flatnonzero(plane)
    xp, zp = x[idx], z[idx]
    print(f"cells {n_cells} plane {idx.size}")
    addressing = load_addressing(CASE, NPROC)
    names = written_times(CASE, NPROC)
    print(f"times {len(names)}  {names[0]} .. {names[-1]}")

    frames = []
    for name in names:
        alpha = gather_scalar(CASE, name, n_cells, addressing, "alpha.metal")
        temp = gather_scalar(CASE, name, n_cells, addressing, "T")
        vel = gather_vector(CASE, name, n_cells, addressing)
        if alpha is None or temp is None or vel is None:
            raise SystemExit(f"incomplete fields at {name}")
        frames.append((
            float(name),
            alpha[idx],
            temp[idx],
            vel[idx, 0],
            vel[idx, 2],
            np.linalg.norm(vel[idx], axis=1),
            bead_line(x, z, alpha),
        ))
        if len(frames) % 40 == 0:
            print(f"  loaded {len(frames)}")

    melt_speed = np.concatenate([
        sp[a >= 0.5] for _, a, _, _, _, sp, _ in frames
    ])
    t_all = np.concatenate([temp for _, _, temp, _, _, _, _ in frames])
    print(
        f"melt speed m/s  min {melt_speed.min():.4f}  "
        f"p50 {np.median(melt_speed):.4f}  "
        f"p99 {np.percentile(melt_speed, 99):.4f}  max {melt_speed.max():.4f}"
    )
    for target in (0.8, 2.0):
        row = min(frames, key=lambda r: abs(r[0] - target))
        b = row[6]
        print(
            f"bead t={row[0]:.2f}  nMetal {b['n']}  "
            f"zTrail {b['z_trail']:.3f}  zLead {b['z_lead']:.3f}  "
            f"xFoot {b['x_foot']:.3f}  xNose {b['x_nose']:.3f}"
        )

    tnorm = Normalize(vmin=300, vmax=max(2200.0, float(np.percentile(
        np.concatenate([temp[a >= 0.5] for _, a, temp, _, _, _, _ in frames]), 99
    ))))
    vmax = max(0.05, float(np.percentile(melt_speed, 99)))
    snorm = Normalize(vmin=0.0, vmax=vmax)
    tri = mask_tri(Triangulation(xp, zp), xp, zp)
    print(f"frames {len(frames)}  fps {FPS}  colour vmax {tnorm.vmax:.0f}  speed vmax {vmax:.3f}")

    def grab(fig):
        fig.canvas.draw()
        w, h = fig.canvas.get_width_height()
        return np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8).reshape(h, w, 3).copy()

    tw = imageio.get_writer(
        OUT / "cal95b_2s_center_temperature.mp4",
        fps=FPS, codec="libx264", quality=8, macro_block_size=1,
    )
    for i, (t, a, temp, uu, ww, sp, _) in enumerate(frames):
        fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
        ax = base_ax(fig, f"cal95b   t = {t:.2f} s    temperature")
        ax.tricontourf(tri, temp, levels=24, cmap="inferno", norm=tnorm)
        if temp.min() < SOLIDUS < temp.max():
            ax.tricontour(tri, temp, levels=[SOLIDUS], colors=["#f7f7f7"], linewidths=1.15)
        ax.tricontour(tri, a, levels=[0.5], colors=["#00e5ff"], linewidths=1.4)
        sm = plt.cm.ScalarMappable(norm=tnorm, cmap="inferno")
        sm.set_array([])
        cax = fig.add_axes([0.86, 0.14, 0.02, 0.68])
        cb = fig.colorbar(sm, cax=cax)
        cb.set_label("T  [K]", fontsize=14)
        ax.plot([], [], color="#f7f7f7", lw=1.6, label=f"solidus  {SOLIDUS:.0f} K")
        ax.plot([], [], color="#00e5ff", lw=1.6, label="free surface")
        ax.legend(loc="upper right", fontsize=11, framealpha=0.9)
        tw.append_data(grab(fig))
        plt.close(fig)
        if i % 40 == 0:
            print(f"  T {i}/{len(frames)}")
    tw.close()

    fw = imageio.get_writer(
        OUT / "cal95b_2s_center_flow.mp4",
        fps=FPS, codec="libx264", quality=8, macro_block_size=1,
    )
    for i, (t, a, temp, uu, ww, sp, _) in enumerate(frames):
        fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
        ax = base_ax(fig, f"cal95b   t = {t:.2f} s    melt velocity")
        ax.tricontourf(tri, temp, levels=24, cmap="inferno", norm=tnorm, alpha=0.28)
        ax.tricontour(tri, a, levels=[0.5], colors=["k"], linewidths=1.3)
        show = a >= 0.5
        key = np.round(xp / 0.28).astype(int) * 1000 + np.round(zp / 0.28).astype(int)
        keep = np.zeros(show.shape, dtype=bool)
        seen = set()
        for j in np.flatnonzero(show):
            if key[j] in seen:
                continue
            seen.add(int(key[j]))
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
        fw.append_data(grab(fig))
        plt.close(fig)
        if i % 40 == 0:
            print(f"  U {i}/{len(frames)}")
    fw.close()
    print("done", len(frames), "frames")


if __name__ == "__main__":
    main()
