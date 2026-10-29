#!/usr/bin/env python3
"""Polished-metal view of the 2 s cal95b bead. Half domain, no mirror.

One frame per written time. The free surface is alpha = 0.5. The plate is
matte; the bead and wire take a simple specular shade, with a warm tint
where T is above the solidus.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import imageio.v2 as imageio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_cal95b_2s_center import gather_scalar  # noqa: E402
from render_cal95b_cal105 import cell_centres, load_addressing, read_face_pack, written_times  # noqa: E402
from render_half_bead import read_labels, read_points  # noqa: E402

ROOT = Path("/home/xingyang/laser-wire-ded-project")
CASE = ROOT / "cases/wire_cavity_cal95b_2s"
OUT = ROOT / "results/calibration"
FPS = 30
NPROC = 12
SYM0, SYMN = 105685, 1856
SOLIDUS = 1658.0
# Light from above and from the trailing side.
LIGHT = np.array([0.50, 0.25, 0.83], dtype=np.float64)
LIGHT /= np.linalg.norm(LIGHT)
FILL = np.array([-0.35, 0.45, 0.70], dtype=np.float64)
FILL /= np.linalg.norm(FILL)
VIEW = np.array([0.55, 0.30, 0.78], dtype=np.float64)
VIEW /= np.linalg.norm(VIEW)


def metal_surface(points, faces, owner, neighbour, centres, alpha, temp):
    n_int = neighbour.size
    own = owner[:n_int]
    mo = alpha[own] >= 0.5
    mn = alpha[neighbour] >= 0.5
    surf = np.flatnonzero(mo != mn)
    side = np.where(mo[surf], own[surf], neighbour[surf])
    quads = points[faces[:n_int][surf]]
    temps = temp[side]
    cens = centres[side]
    # Metal faces on the symmetry plane, so the cut is solid.
    sym = np.arange(SYM0, SYM0 + SYMN)
    keep = alpha[owner[sym]] >= 0.5
    if np.any(keep):
        quads = np.concatenate([quads, points[faces[sym][keep]]], axis=0)
        temps = np.concatenate([temps, temp[owner[sym][keep]]])
        cens = np.concatenate([cens, centres[owner[sym][keep]]])
    return quads, temps, cens


def shade(quads, temps, cens):
    v1 = quads[:, 1] - quads[:, 0]
    v2 = quads[:, 2] - quads[:, 0]
    n = np.cross(v1, v2)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-15
    fc = quads.mean(axis=1)
    flip = np.einsum("ij,ij->i", n, fc - cens) < 0
    n[flip] *= -1
    ndotl = np.clip(n @ LIGHT, 0, 1)
    ndotf = np.clip(n @ FILL, 0, 1)
    half = LIGHT + VIEW
    half /= np.linalg.norm(half)
    spec = np.clip(n @ half, 0, 1) ** 28
    z = fc[:, 2]
    plate = z < 8e-5
    silver = np.array([0.78, 0.80, 0.84])
    plate_c = np.array([0.55, 0.56, 0.58])
    base = np.where(plate[:, None], plate_c, silver)
    amb = np.where(plate, 0.55, 0.34)
    rgb = amb[:, None] * base
    rgb = rgb + np.where(plate, 0.40, 0.70)[:, None] * ndotl[:, None] * base
    rgb = rgb + 0.28 * ndotf[:, None] * base
    rgb = rgb + np.where(plate, 0.04, 0.85)[:, None] * spec[:, None]
    hot = np.clip((temps - SOLIDUS) / 700.0, 0, 1) * (~plate)
    glow = np.array([1.0, 0.42, 0.10])
    rgb = rgb * (1 - 0.62 * hot[:, None]) + glow * (0.62 * hot[:, None])
    return np.clip(rgb, 0, 1)


def frame(quads_m, rgb, t, path=None, writer=None):
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    ax = fig.add_axes([0.0, 0.04, 1.0, 0.90], projection="3d")
    q = quads_m * 1e3
    ax.add_collection3d(Poly3DCollection(
        q, facecolors=rgb, edgecolors="none", linewidths=0, antialiased=False
    ))
    # Symmetry plane.
    xx = np.array([[-2.0, 7.2], [-2.0, 7.2]])
    zz = np.array([[-0.2, -0.2], [2.6, 2.6]])
    ax.plot_surface(
        xx, np.zeros_like(xx), zz, color="#9ecae1", alpha=0.16,
        linewidth=0, shade=False,
    )
    ax.text(6.4, 0.0, 2.45, "symmetry plane  y = 0", color="#08306b", fontsize=11)
    ax.set_xlim(-2.0, 7.2)
    ax.set_ylim(0.0, 3.6)
    ax.set_zlim(-0.3, 2.7)
    ax.view_init(elev=22, azim=-64)
    try:
        ax.set_proj_type("persp")
        ax.set_box_aspect((9.2, 3.6, 3.0))
        ax.dist = 8.6
    except Exception:
        pass
    ax.set_axis_off()
    fig.suptitle(f"cal95b    t = {t:.2f} s", fontsize=18, y=0.98)
    note = "after ~1.6 s the bead foot touches the downstream boundary at x = 7 mm"
    fig.text(0.5, 0.02, note, ha="center", fontsize=13,
             color="#7f0000" if t >= 1.6 else "#333333")
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    im = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8).reshape(h, w, 3).copy()
    if writer is not None:
        writer.append_data(im)
    if path is not None:
        fig.savefig(path, dpi=100)
    plt.close(fig)
    return im


def main():
    mesh = CASE / "constant/polyMesh"
    print("mesh")
    points = read_points(mesh / "points")
    offs, labels = read_face_pack(mesh / "faces")
    if not np.all(np.diff(offs) == 4):
        raise SystemExit("mesh has non-quad faces")
    faces = labels.reshape(-1, 4)
    owner = read_labels(mesh / "owner")
    neighbour = read_labels(mesh / "neighbour")
    centres = cell_centres(points, offs, labels, owner, neighbour)
    n_cells = centres.shape[0]
    addressing = load_addressing(CASE, NPROC)
    names = written_times(CASE, NPROC)
    print(f"times {len(names)}")
    only = sys.argv[1:] 
    out = imageio.get_writer(
        OUT / "cal95b_2s_metallic.mp4",
        fps=FPS, codec="libx264", quality=8, macro_block_size=1,
    ) if not only else None
    still = None
    for i, name in enumerate(names):
        t = float(name)
        if only and f"{t:.2f}" not in only and name not in only:
            continue
        alpha = gather_scalar(CASE, name, n_cells, addressing, "alpha.metal")
        temp = gather_scalar(CASE, name, n_cells, addressing, "T")
        if alpha is None or temp is None:
            raise SystemExit(f"missing fields at {name}")
        quads, temps, cens = metal_surface(
            points, faces, owner, neighbour, centres, alpha, temp
        )
        rgb = shade(quads, temps, cens)
        png = None
        if abs(t - 0.8) < 1e-6 or abs(t - 2.0) < 1e-6:
            png = OUT / ("cal95b_2s_metallic_t080.png" if t < 1.5 else "cal95b_2s_metallic_t200.png")
            still = png
        im_path = png
        frame(quads, rgb, t, path=im_path, writer=out)
        if i % 20 == 0 or only:
            print(f"  frame {name} faces {quads.shape[0]}")
    if out is not None:
        out.close()
        print("wrote", OUT / "cal95b_2s_metallic.mp4", "frames", len(names))
    if still:
        print("still", still)


if __name__ == "__main__":
    main()
