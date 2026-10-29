#!/usr/bin/env python3
"""Half-domain 3D render of a cal95b time. No mirror across y = 0.

The symmetry plane is drawn and labelled. Beam spots that lie in this half
(60° and 180°) are marked. The −60° beam is folded into this half by the
solver; it is named in the caption and not drawn on a mirrored mesh.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import imageio.v2 as imageio

ROOT = Path("/home/xingyang/laser-wire-ded-project")
CASE = ROOT / "cases/wire_cavity_cal95b"
OUT = ROOT / "results/calibration"

# Plate spots of the equal-power beams, millimetres. Only y >= 0 is simulated.
SPOTS = [
    ("60°  247 W", -0.275, 0.477),
    ("180°  247 W", 0.550, 0.0),
]
SPOT_R = 0.26


def _after_header(data):
    i = data.find(b"\n// * * *")
    j = data.find(b"\n", i + 10)
    return data, j + 1


def read_points(path):
    data = Path(path).read_bytes()
    k = data.find(b"\n", data.find(b"object"))
    # count is the first integer line after the banner
    rest = data[data.find(b"// *"):]
    line_end = rest.find(b"\n", rest.find(b"\n") + 1)
    # simpler: the count line is '\n\n\nN\n('
    k = data.find(b"\n(")
    head = data[:k]
    n = int(head.split()[-1])
    start = k + 2
    pts = np.frombuffer(data, dtype="<f8", count=n * 3, offset=start).reshape(n, 3).copy()
    return pts


def read_labels(path):
    data = Path(path).read_bytes()
    k = data.find(b"\n(")
    n = int(data[:k].split()[-1])
    start = k + 2
    return np.frombuffer(data, dtype="<i4", count=n, offset=start).copy()


def read_faces(path):
    data = Path(path).read_bytes()
    k = data.find(b"\n(")
    n_off = int(data[:k].split()[-1])
    start = k + 2
    offs = np.frombuffer(data, dtype="<i4", count=n_off, offset=start)
    pos = start + n_off * 4
    # b')\nCOUNT\n('
    rest = data[pos:]
    # skip )\n
    rest = rest[2:]
    nl = rest.find(b"\n")
    n_lab = int(rest[:nl])
    lab_start = pos + 2 + nl + 1 + 1  # )\n COUNT \n (
    # recompute from the known marker
    marker = data.find(b")\n", pos)
    count_nl = data.find(b"\n", marker + 2)
    n_lab = int(data[marker + 2:count_nl])
    paren = data.find(b"(", count_nl)
    labels = np.frombuffer(data, dtype="<i4", count=n_lab, offset=paren + 1).copy()
    n_faces = n_off - 1
    if labels.size != n_lab or offs[-1] != n_lab:
        raise SystemExit(f"face list mismatch {labels.size} {n_lab} {offs[-1]}")
    return labels.reshape(n_faces, 4), n_faces


def read_scalar(path):
    data = Path(path).read_bytes()
    key = b"internalField   nonuniform List<scalar> \n"
    i = data.find(key)
    if i < 0:
        key = b"internalField   nonuniform List<scalar>\n"
        i = data.find(key)
    if i < 0:
        raise SystemExit(f"no scalar field in {path}")
    j = i + len(key)
    nl = data.find(b"\n", j)
    n = int(data[j:nl])
    start = nl + 1
    if data[start:start + 1] == b"(":
        start += 1
    return np.frombuffer(data, dtype="<f8", count=n, offset=start).copy()


def surface(points, faces, owner, neighbour, alpha, temp):
    n_int = neighbour.size
    own = owner[:n_int]
    mo = alpha[own] >= 0.5
    mn = alpha[neighbour] >= 0.5
    surf = mo != mn
    side = np.where(mo[surf], own[surf], neighbour[surf])
    quads = points[faces[:n_int][surf]]
    cols = temp[side]
    # Metal faces on the symmetry plane, so the cut reads as solid.
    sym0, sym1 = 105685, 105685 + 1856
    sym = owner[sym0:sym1]
    keep = alpha[sym] >= 0.5
    if keep.any():
        quads = np.concatenate([quads, points[faces[sym0:sym1][keep]]], axis=0)
        cols = np.concatenate([cols, temp[sym[keep]]])
    return quads, cols


def add_spots(ax):
    """Rings sit above the bead so the top view can see them.

    The −60° beam is traced and then folded into this half (y -> |y|), so its
    power lands on the 60° spot. It is labelled there; no mirrored geometry.
    """
    th = np.linspace(0, 2 * np.pi, 64)
    z_hi = 2.90
    for name, x, y in SPOTS:
        ring = np.stack(
            [
                x + SPOT_R * np.cos(th),
                np.clip(y + SPOT_R * np.sin(th), 0.0, None),
                np.full_like(th, z_hi),
            ],
            axis=1,
        )
        ax.plot(ring[:, 0], ring[:, 1], ring[:, 2], color="#00e5ff", lw=2.4, zorder=10)
        ax.plot([x, x], [y, y], [0.05, z_hi], color="#00e5ff", lw=1.0, ls="--", zorder=10)
        ax.plot([x], [y], [0.08], color="#00e5ff", marker="x", ms=7, zorder=10)


def draw(ax, quads, cols, norm, title, limits=None):
    # millimetres
    q = quads * 1e3
    rgb = plt.cm.inferno(norm(cols))
    coll = Poly3DCollection(
        q, facecolors=rgb, edgecolors="none", linewidths=0, antialiased=False
    )
    ax.add_collection3d(coll)
    # Symmetry plane y = 0, the cut of the half domain.
    xx = np.array([[-4, 6], [-4, 6]])
    zz = np.array([[-0.4, -0.4], [2.4, 2.4]])
    yy = np.zeros_like(xx)
    ax.plot_surface(xx, yy, zz, color="#9ecae1", alpha=0.18, linewidth=0, shade=False)
    ax.text(5.2, 0.0, 2.15, "symmetry plane  y = 0", color="#08519c", fontsize=8)
    add_spots(ax)
    if limits is None:
        limits = ((-4, 6), (0, 3.5), (-0.5, 3.2))
    ax.set_xlim(*limits[0])
    ax.set_ylim(*limits[1])
    ax.set_zlim(*limits[2])
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.set_zlabel("z [mm]")
    ax.set_title(title, fontsize=11)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.fill = False
    try:
        ax.set_box_aspect(
            (
                limits[0][1] - limits[0][0],
                limits[1][1] - limits[1][0],
                limits[2][1] - limits[2][0],
            )
        )
    except Exception:
        pass


def frame(quads, cols, norm, view, title, path, size=(1280, 720), limits=None):
    dpi = 100
    fig = plt.figure(figsize=(size[0] / dpi, size[1] / dpi), dpi=dpi)
    ax = fig.add_subplot(111, projection="3d")
    draw(ax, quads, cols, norm, title, limits=limits)
    ax.view_init(elev=view[0], azim=view[1])
    sm = plt.cm.ScalarMappable(norm=norm, cmap="inferno")
    sm.set_array([])
    fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, label="T [K]")
    fig.text(
        0.01, 0.02,
        "cyan rings, above the wire:  60° 247 W at (−0.28, 0.48) mm"
        "    180° 247 W at (0.55, 0) mm"
        "    −60° 247 W folded onto the 60° spot\n"
        "dashed stems drop to the plate aim.  Blue sheet: symmetry plane y = 0.",
        fontsize=8, va="bottom",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


def main():
    mesh = CASE / "constant/polyMesh"
    print("reading mesh")
    points = read_points(mesh / "points")
    faces, n_faces = read_faces(mesh / "faces")
    owner = read_labels(mesh / "owner")
    neighbour = read_labels(mesh / "neighbour")
    print(f"points {points.shape[0]} faces {n_faces} internal {neighbour.size}")

    times = ["0", "0.2", "0.4", "0.6", "0.8"]
    views = {
        "trailing": (20, -70),
        "front": (20, 110),
        "top": (78, -90),
    }
    top_limits = ((-1.6, 4.6), (0.0, 2.2), (-0.3, 3.2))
    # Colour scale from the final bead, shared by every frame.
    t_final = read_scalar(CASE / "0.8/T")
    a_final = read_scalar(CASE / "0.8/alpha.metal")
    metal = a_final >= 0.5
    norm = Normalize(vmin=300, vmax=max(1800, np.percentile(t_final[metal], 98)))

    print("stills at 0.8 s")
    quads, cols = surface(points, faces, owner, neighbour, a_final, t_final)
    print(f"surface faces {quads.shape[0]}")
    stills = []
    for name, view in views.items():
        path = OUT / f"cal95b_3d_{name}.png"
        frame(
            quads, cols, norm, view,
            "cal95b  t = 0.80 s   half domain, no mirror\n"
            "−60° beam is folded into this half by the symmetry plane",
            path,
            limits=top_limits if name == "top" else None,
        )
        stills.append(path)
        print("wrote", path)

    print("movie")
    frames = []
    for tname in times:
        alpha = read_scalar(CASE / tname / "alpha.metal")
        temp = read_scalar(CASE / tname / "T")
        quads, cols = surface(points, faces, owner, neighbour, alpha, temp)
        path = OUT / f"_frame_{tname}.png"
        frame(
            quads, cols, norm, views["trailing"],
            f"cal95b  t = {tname} s   trailing side, half domain",
            path,
        )
        frames.append(imageio.imread(path))
        path.unlink()
    # 12 s at 8 fps: 96 frames, 5 snapshots.
    per = 20
    movie = []
    for im in frames:
        movie.extend([im] * per)
    mp4 = OUT / "cal95b_3d.mp4"
    imageio.mimsave(mp4, movie, fps=8, codec="libx264", quality=8)
    print("wrote", mp4, "frames", len(movie), "seconds", len(movie) / 8)


if __name__ == "__main__":
    main()
