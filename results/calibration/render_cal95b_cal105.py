#!/usr/bin/env python3
"""cal95b bead, then the cal105 imposed pin, half domain, no mirror.

The first segment is the equal-power melt from 0 to 0.8 s. The second uses
every cal105 time that is already written on all ranks. The running solver
is not touched.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle
from matplotlib.tri import Triangulation
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import imageio.v2 as imageio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_half_bead import (  # noqa: E402
    frame as bead_frame,
    read_faces,
    read_labels,
    read_points,
    read_scalar,
    surface,
)
from slit_metric import measure  # noqa: E402
from plot_slit_neck import first_metal_gap  # noqa: E402

ROOT = Path("/home/xingyang/laser-wire-ded-project")
CAL95 = ROOT / "cases/wire_cavity_cal95b"
CAL105 = ROOT / "cases/wire_cavity_cal105"
OUT = ROOT / "results/calibration"
WIRE_R = 0.5


def read_face_pack(path):
    data = Path(path).read_bytes()
    k = data.find(b"\n(")
    n_off = int(data[:k].split()[-1])
    start = k + 2
    offs = np.frombuffer(data, dtype="<i4", count=n_off, offset=start).copy()
    marker = data.find(b")\n", start + n_off * 4)
    count_nl = data.find(b"\n", marker + 2)
    n_lab = int(data[marker + 2:count_nl])
    paren = data.find(b"(", count_nl)
    labels = np.frombuffer(data, dtype="<i4", count=n_lab, offset=paren + 1).copy()
    return offs, labels


def boundary_range(path, name):
    text = Path(path).read_text(errors="replace")
    i = text.find(f"\n    {name}\n")
    if i < 0:
        raise SystemExit(f"no patch {name}")
    block = text[i:i + 400]
    def grab(key):
        j = block.find(key)
        return int(block[j:].split()[1].rstrip(";"))
    return grab("nFaces"), grab("startFace")


def cell_centres(points, offs, labels, owner, neighbour):
    n_cells = int(max(owner.max(), neighbour.max())) + 1
    acc = np.zeros((n_cells, 3))
    cnt = np.zeros(n_cells)
    n_int = neighbour.size
    for i in range(offs.size - 1):
        c = points[labels[offs[i]:offs[i + 1]]].mean(axis=0)
        acc[owner[i]] += c
        cnt[owner[i]] += 1
        if i < n_int:
            acc[neighbour[i]] += c
            cnt[neighbour[i]] += 1
    return acc / cnt[:, None]


def surface_var(points, offs, labels, owner, neighbour, alpha, temp, sym0, sym1):
    n_int = neighbour.size
    own = owner[:n_int]
    mo = alpha[own] >= 0.5
    mn = alpha[neighbour] >= 0.5
    surf = np.flatnonzero(mo != mn)
    side = np.where(mo[surf], own[surf], neighbour[surf])
    polys = [points[labels[offs[i]:offs[i + 1]]] for i in surf]
    cols = temp[side]
    sym = owner[sym0:sym1]
    keep = np.flatnonzero(alpha[sym] >= 0.5)
    for k in keep:
        i = sym0 + int(k)
        polys.append(points[labels[offs[i]:offs[i + 1]]])
    if keep.size:
        cols = np.concatenate([cols, temp[sym[keep]]])
    return polys, cols


def gather(case, time_name, n_cells, addressing, field):
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


def written_times(case, nproc=12):
    sets = []
    for i in range(nproc):
        names = set()
        for p in (case / f"processor{i}").iterdir():
            if p.is_dir() and p.name[:1].isdigit():
                names.add(p.name)
        sets.append(names)
    common = set.intersection(*sets) if sets else set()
    return sorted(common, key=float)


def load_addressing(case, nproc=12):
    out = []
    for i in range(nproc):
        out.append(read_labels(
            case / f"processor{i}" / "constant/polyMesh/cellProcAddressing"
        ))
    return out


def gas_under_bead(centres, alpha):
    """Gas cells sitting strictly below metal in the same 0.15 mm column."""
    x = centres[:, 0]
    y = centres[:, 1]
    z = centres[:, 2]
    m = (z > 0.0) & (z < 2.2e-3) & (x > -1e-3) & (x < 5e-3) & (y < 2e-3)
    xi = np.floor(x[m] / 1.5e-4).astype(np.int32)
    yi = np.floor(y[m] / 1.5e-4).astype(np.int32)
    zz = z[m]
    aa = alpha[m]
    key = xi * 100000 + yi
    count = 0
    for k in np.unique(key):
        sel = key == k
        metal = zz[sel & (aa >= 0.5)]
        gas = zz[sel & (aa < 0.5)]
        if metal.size and gas.size:
            count += int(np.sum(gas < metal.min()))
    return count


def log_tail(path):
    last_t = last_dt = None
    last_pin = ""
    gas_counts = []
    if not path.is_file():
        return last_t, last_dt, last_pin, gas_counts
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("Time ="):
            last_t = float(line.split("=", 1)[1])
        elif line.startswith("deltaT"):
            last_dt = float(line.split("=", 1)[1])
        elif line.startswith("LinePin:"):
            last_pin = line
            # gas N
            parts = line.split()
            if "gas" in parts:
                gas_counts.append(int(parts[parts.index("gas") + 1]))
    return last_t, last_dt, last_pin, gas_counts


def gap_sentence(x_mm, y_mm, z_mm, alpha):
    """Width and depth on the trailing face. x, y, z are millimetres."""
    near = (y_mm < 0.08) & (x_mm > 0.45) & (x_mm < 1.3) & (z_mm > 0.40) & (z_mm < 1.90)
    row = measure(x_mm[near], z_mm[near], alpha[near])
    gap = first_metal_gap(x_mm[near], z_mm[near], alpha[near])
    face = near & (z_mm < 1.70) & (x_mm < 0.60)
    face_metal = bool(face.any()) and float(np.mean(alpha[face] >= 0.5)) > 0.9
    cap = (
        (y_mm < 0.40) & (x_mm > 0.50) & (x_mm < 0.90)
        & (z_mm > 1.60) & (z_mm < 2.05) & (alpha < 0.5)
    )
    if gap is not None:
        text = (
            f"width {gap['width']:.3f} mm, depth {gap['depth']:.3f} mm"
        )
    elif face_metal:
        crest = (
            (y_mm < 0.12) & (x_mm > 0.48) & (x_mm < 0.70)
            & (z_mm > 1.60) & (z_mm < 1.95) & (alpha < 0.5)
        )
        n_crest = int(crest.sum())
        if n_crest:
            text = f"fine neck: width 0, depth 0. {n_crest} coarse gas cells at the crest."
        else:
            text = "width 0 mm, depth 0 mm. Wall cell is metal."
    elif row["depth_mm"] > 0:
        text = f"width {row['width_mm']:.3f} mm, depth {row['depth_mm']:.3f} mm"
    else:
        text = "width 0 mm, depth 0 mm"
    return text, row, gap


def draw_wire_wall(ax):
    phi = np.linspace(0.0, np.pi, 28)
    zz = np.linspace(0.05, 2.6, 2)
    pp, zz = np.meshgrid(phi, zz)
    xx = WIRE_R * np.cos(pp)
    yy = WIRE_R * np.sin(pp)
    ax.plot_surface(xx, yy, zz, color="#4a4a4a", alpha=0.35, linewidth=0, shade=False)
    ax.text(0.15, 0.7, 2.55, "wire = solid wall", fontsize=8, color="k")


def pin_frame(polys, cols, norm, centres, alpha, time_s, gap_text, warn, path):
    dpi = 100
    fig = plt.figure(figsize=(12.8, 7.2), dpi=dpi)
    ax = fig.add_subplot(121, projection="3d")
    q = [p * 1e3 for p in polys]
    rgb = plt.cm.inferno(norm(cols))
    ax.add_collection3d(Poly3DCollection(
        q, facecolors=rgb, edgecolors="none", linewidths=0, antialiased=False
    ))
    xx = np.array([[-4, 6], [-4, 6]])
    zz = np.array([[-0.4, -0.4], [2.4, 2.4]])
    ax.plot_surface(xx, np.zeros_like(xx), zz, color="#9ecae1", alpha=0.18,
                    linewidth=0, shade=False)
    ax.text(4.6, 0.0, 2.2, "symmetry plane  y = 0", color="#08519c", fontsize=7)
    draw_wire_wall(ax)
    limits = ((-4, 6), (0, 3.5), (-0.5, 3.2))
    ax.set_xlim(*limits[0])
    ax.set_ylim(*limits[1])
    ax.set_zlim(*limits[2])
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.set_zlabel("z [mm]")
    ax.view_init(elev=20, azim=-70)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.fill = False
    try:
        ax.set_box_aspect((10, 3.5, 3.7))
    except Exception:
        pass
    ax.set_title(
        f"trailing view   pin window {time_s * 1e3:.2f} ms",
        fontsize=10,
    )
    sm = plt.cm.ScalarMappable(norm=norm, cmap="inferno")
    sm.set_array([])
    fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.02, label="T [K]")

    ax2 = fig.add_subplot(122)
    x = centres[:, 0] * 1e3
    y = centres[:, 1] * 1e3
    z = centres[:, 2] * 1e3
    m = (y < 0.12) & (x > 0.05) & (x < 1.45) & (z > 0.35) & (z < 1.85)
    px, pz, pa = -x[m], z[m], alpha[m]
    if px.size > 10:
        tri = Triangulation(px, pz)
        xt, zt = px[tri.triangles], pz[tri.triangles]
        tri.set_mask((np.ptp(xt, axis=1) > 0.15) | (np.ptp(zt, axis=1) > 0.15))
        levels = np.linspace(0.0, 1.0, 17)
        levels[0] = -1e-3
        levels[-1] = 1.0 + 1e-3
        ax2.tricontourf(tri, pa, levels=levels, cmap="gray_r", vmin=0, vmax=1)
        ax2.tricontour(tri, pa, levels=[0.5], colors=["#d94801"], linewidths=0.8)
    ax2.add_patch(Rectangle((-WIRE_R, 0.35), WIRE_R - 0.05, 1.75,
                            facecolor="#4a4a4a", edgecolor="none", zorder=3))
    ax2.plot([-WIRE_R, -WIRE_R], [0.35, 2.10], color="#2ca02c", lw=1.0, ls="--")
    ax2.set_aspect("equal")
    ax2.set_xlim(-1.35, -0.05)
    ax2.set_ylim(0.35, 2.15)
    ax2.set_xlabel("trailing  ←  x [mm]")
    ax2.set_ylabel("z [mm]")
    ax2.set_title(
        f"neck, symmetry plane   {time_s * 1e3:.2f} ms\n{gap_text}",
        fontsize=8,
    )
    caption = "pinned contact line: IMPOSED (hard-coded), wire = solid wall"
    if warn:
        caption = caption + "\n" + warn
    fig.suptitle(caption, fontsize=11, color="#a50f15" if warn else "k")
    fig.text(
        0.01, 0.01,
        "Half domain, no mirror. Grey cylinder and bar: the cut wire, a solid wall. "
        "Neck plot: dark metal, white gas, green dash = trailing face. "
        "Restarted from the cal95b bead at 0.80 s.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


def main():
    print("baseline mesh")
    mesh = CAL95 / "constant/polyMesh"
    points = read_points(mesh / "points")
    faces, _ = read_faces(mesh / "faces")
    owner = read_labels(mesh / "owner")
    neighbour = read_labels(mesh / "neighbour")
    t_final = read_scalar(CAL95 / "0.8/T")
    a_final = read_scalar(CAL95 / "0.8/alpha.metal")
    norm = Normalize(vmin=300, vmax=max(1800, float(np.percentile(t_final[a_final >= 0.5], 98))))

    images = []
    for tname in ["0", "0.2", "0.4", "0.6", "0.8"]:
        alpha = read_scalar(CAL95 / tname / "alpha.metal")
        temp = read_scalar(CAL95 / tname / "T")
        quads, cols = surface(points, faces, owner, neighbour, alpha, temp)
        path = OUT / f"_b95_{tname}.png"
        bead_frame(
            quads, cols, norm, (20, -70),
            "baseline: melted bead, generated\n"
            f"cal95b  t = {tname} s   trailing side, half domain",
            path,
        )
        images.append(imageio.imread(path))
        path.unlink()
        print("baseline", tname)

    print("cal105 mesh")
    cmesh = CAL105 / "constant/polyMesh"
    cpoints = read_points(cmesh / "points")
    offs, labels = read_face_pack(cmesh / "faces")
    cowner = read_labels(cmesh / "owner")
    cneighbour = read_labels(cmesh / "neighbour")
    n_sym, sym0 = boundary_range(cmesh / "boundary", "symmetry")
    print(f"cells {cowner.max()+1} symmetry faces {n_sym} at {sym0}")
    print("cell centres")
    centres = cell_centres(cpoints, offs, labels, cowner, cneighbour)
    addressing = load_addressing(CAL105)
    times = written_times(CAL105)
    print("written", times)

    y = centres[:, 1] * 1e3
    x = centres[:, 0] * 1e3
    z = centres[:, 2] * 1e3
    near = y < 0.12

    last_t, last_dt, last_pin, gas_counts = log_tail(CAL105 / "log.laserWireDEDFoam")
    warn = ""
    if last_dt is not None and last_dt < 5e-8:
        warn = f"timestep collapsed (deltaT = {last_dt:.2e} s)"
    if gas_counts and gas_counts[-1] > 200 and gas_counts[0] < 80:
        extra = f"pin gas cells rose from {gas_counts[0]} to {gas_counts[-1]}"
        warn = extra if not warn else warn + "; " + extra
    if last_t is not None:
        print(f"solver is at {last_t*1e3:.3f} ms, deltaT {last_dt}, {last_pin}")

    reports = []
    pin_images = []
    for tname in times:
        alpha = gather(CAL105, tname, centres.shape[0], addressing, "alpha.metal")
        temp = gather(CAL105, tname, centres.shape[0], addressing, "T")
        if alpha is None or temp is None:
            print("skip incomplete", tname)
            continue
        foot = (
            (centres[:, 2] > 0) & (centres[:, 2] < 0.25e-3)
            & (centres[:, 0] > 0.5e-3) & (centres[:, 0] < 3.5e-3)
            & (centres[:, 1] < 0.8e-3) & (alpha < 0.5)
        )
        under = int(foot.sum())
        text, row, gap = gap_sentence(x, y, z, alpha)
        this_warn = warn
        if under > 40:
            extra = f"gas film on the plate under the bead: {under} cells"
            this_warn = extra if not this_warn else this_warn + "; " + extra
        print(f"t={tname}: {text}; plate-film cells {under}")
        reports.append((tname, text, under, row, gap))
        polys, cols = surface_var(
            cpoints, offs, labels, cowner, cneighbour, alpha, temp, sym0, sym0 + n_sym
        )
        print(f"  surface polys {len(polys)}")
        path = OUT / f"_b105_{tname}.png"
        pin_frame(polys, cols, norm, centres, alpha, float(tname), text, this_warn, path)
        pin_images.append(imageio.imread(path))
        path.unlink()

    movie = []
    for im in images:
        movie.extend([im] * 20)
    hold = 48 if len(pin_images) <= 2 else 24
    for im in pin_images:
        movie.extend([im] * hold)
    mp4 = OUT / "cal95b_cal105_3d.mp4"
    imageio.mimsave(mp4, movie, fps=8, codec="libx264", quality=8)
    print("wrote", mp4, "seconds", len(movie) / 8)
    if reports:
        print("LAST", reports[-1][0], reports[-1][1])


if __name__ == "__main__":
    main()
