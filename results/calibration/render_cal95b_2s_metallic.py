#!/usr/bin/env python3
"""Smooth metallic view of the 2 s cal95b bead. Half domain, no mirror.

alpha.metal is averaged from cells onto points (cell-to-point). That point
field is resampled 2x in index space and a marching-cubes iso-surface is
taken at 0.5. Vertices get eight Taubin smooths (lambda 0.45, mu -0.47);
points that started on y = 0 stay there. Normals are recomputed in physical space
and lit with three lights, a tight specular lobe, a soft lobe and a Fresnel
rim (environment-style; there is no HDRI map). The symmetry cut is the same
point field, marching squares at 0.5, so its edge meets the iso-surface.
One frame per written time; nothing is interpolated in time.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse as sp
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.ndimage import map_coordinates
from skimage.measure import marching_cubes
import imageio.v2 as imageio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_cal95b_2s_center import gather_scalar  # noqa: E402
from render_cal95b_cal105 import load_addressing, read_face_pack, written_times  # noqa: E402
from render_half_bead import read_labels, read_points  # noqa: E402

ROOT = Path("/home/xingyang/laser-wire-ded-project")
CASE = ROOT / "cases/wire_cavity_cal95b_2s"
OUT = ROOT / "results/calibration"
FPS = 30
NPROC = 12
SOLIDUS = 1658.0
ELEV, AZIM = 34.0, 80.0
DIST = 10.0
FRAME_ZOOM = 1.74
SURF_ZOOM = 2
CAP_ZOOM = 3


def camera_direction(elev, azim):
    """Direction from the bead toward the matplotlib camera, in data axes."""
    e, a = np.deg2rad(elev), np.deg2rad(azim)
    v = np.array([
        np.cos(e) * np.cos(a),
        np.cos(e) * np.sin(a),
        np.sin(e),
    ], dtype=np.float64)
    return v / np.linalg.norm(v)


VIEW = camera_direction(ELEV, AZIM)
# Key sits near the camera and above; fill from the side; rim from behind.
LIGHTS = np.stack([
    VIEW + np.array([0.25, 0.05, 0.95]),
    VIEW + np.array([-0.85, 0.15, 0.15]),
    -VIEW + np.array([0.10, -0.05, 1.15]),
])
LIGHTS /= np.linalg.norm(LIGHTS, axis=1, keepdims=True)
LIGHT_W = np.array([1.15, 0.55, 0.70])


def cell_point_ids(faces, owner, neighbour, n_cells):
    bags = [[] for _ in range(n_cells)]
    n_int = neighbour.size
    for fi in range(faces.shape[0]):
        pts = [int(p) for p in faces[fi]]
        bags[owner[fi]].extend(pts)
        if fi < n_int:
            bags[neighbour[fi]].extend(pts)
    return bags


def structured_axes(points):
    xs = np.unique(np.round(points[:, 0], 9))
    ys = np.unique(np.round(points[:, 1], 9))
    zs = np.unique(np.round(points[:, 2], 9))
    if xs.size * ys.size * zs.size != points.shape[0]:
        raise SystemExit("points are not a rectilinear grid")
    ix = np.searchsorted(xs, np.round(points[:, 0], 9))
    iy = np.searchsorted(ys, np.round(points[:, 1], 9))
    iz = np.searchsorted(zs, np.round(points[:, 2], 9))
    return xs, ys, zs, ix, iy, iz


def axis_map(coord, idx):
    i0 = np.floor(idx).astype(np.int32)
    i1 = np.clip(i0 + 1, 0, coord.size - 1)
    i0 = np.clip(i0, 0, coord.size - 1)
    f = idx - i0
    return (1.0 - f) * coord[i0] + f * coord[i1]


def to_point(alpha, bags, n_pts):
    acc = np.zeros(n_pts)
    cnt = np.zeros(n_pts)
    for c, pts in enumerate(bags):
        acc[pts] += alpha[c]
        cnt[pts] += 1.0
    return acc / np.maximum(cnt, 1.0)


def smooth_vertices(verts, faces, iters=8, lam=0.45, mu=-0.47):
    """Light Taubin smooth. High-frequency stair steps shrink; the crest stays."""
    n = verts.shape[0]
    a, b, c = faces[:, 0], faces[:, 1], faces[:, 2]
    rows = np.concatenate([a, a, b, b, c, c])
    cols = np.concatenate([b, c, a, c, a, b])
    adj = sp.coo_matrix((np.ones(rows.size), (rows, cols)), shape=(n, n))
    adj.sum_duplicates()
    adj.data[:] = 1.0
    adj = adj.tocsr()
    deg = np.asarray(adj.sum(axis=1)).ravel()
    deg[deg == 0] = 1.0
    v = verts.copy()
    for _ in range(iters):
        v = v + lam * ((adj @ v) / deg[:, None] - v)
        v = v + mu * ((adj @ v) / deg[:, None] - v)
    v[:, 1] = np.where(np.abs(verts[:, 1]) < 1e-8, 0.0, v[:, 1])
    return v


def resample_index(field, zoom):
    nx, ny, nz = field.shape
    fx = np.linspace(0, nx - 1, (nx - 1) * zoom + 1)
    fy = np.linspace(0, ny - 1, (ny - 1) * zoom + 1)
    fz = np.linspace(0, nz - 1, (nz - 1) * zoom + 1)
    gx, gy, gz = np.meshgrid(fx, fy, fz, indexing="ij")
    fine = map_coordinates(field, [gx, gy, gz], order=1, prefilter=False)
    return fine, fx, fy, fz


def trilinear(field, verts):
    nx, ny, nz = field.shape
    x0 = np.clip(np.floor(verts[:, 0]).astype(np.int32), 0, nx - 2)
    y0 = np.clip(np.floor(verts[:, 1]).astype(np.int32), 0, ny - 2)
    z0 = np.clip(np.floor(verts[:, 2]).astype(np.int32), 0, nz - 2)
    xf = np.clip(verts[:, 0] - x0, 0, 1)
    yf = np.clip(verts[:, 1] - y0, 0, 1)
    zf = np.clip(verts[:, 2] - z0, 0, 1)
    c000 = field[x0, y0, z0]
    c100 = field[x0 + 1, y0, z0]
    c010 = field[x0, y0 + 1, z0]
    c110 = field[x0 + 1, y0 + 1, z0]
    c001 = field[x0, y0, z0 + 1]
    c101 = field[x0 + 1, y0, z0 + 1]
    c011 = field[x0, y0 + 1, z0 + 1]
    c111 = field[x0 + 1, y0 + 1, z0 + 1]
    c00 = c000 * (1 - xf) + c100 * xf
    c01 = c001 * (1 - xf) + c101 * xf
    c10 = c010 * (1 - xf) + c110 * xf
    c11 = c011 * (1 - xf) + c111 * xf
    c0 = c00 * (1 - yf) + c10 * yf
    c1 = c01 * (1 - yf) + c11 * yf
    return c0 * (1 - zf) + c1 * zf


def vertex_normals(verts, faces):
    # Winding from marching cubes points into the metal; flip so the
    # normal leaves the metal and faces the gas.
    tri = verts[faces]
    fn = np.cross(tri[:, 2] - tri[:, 0], tri[:, 1] - tri[:, 0])
    vn = np.zeros_like(verts)
    for k in range(3):
        np.add.at(vn, faces[:, k], fn)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-15
    return vn


def shade_vertices(verts, normals, temp, plate):
    ndotv = np.clip(normals @ VIEW, 0, 1)
    fres = 0.82 + 0.18 * (1.0 - ndotv) ** 5
    spec = np.zeros(verts.shape[0])
    soft = np.zeros(verts.shape[0])
    diff = np.zeros(verts.shape[0])
    for w, L in zip(LIGHT_W, LIGHTS):
        ndotl = np.clip(normals @ L, 0, 1)
        diff += w * ndotl
        H = L + VIEW
        H /= np.linalg.norm(H)
        ndoth = np.clip(normals @ H, 0, 1)
        spec += w * ndotl * ndoth ** 56
        soft += w * ndotl * ndoth ** 10
    up = np.clip(normals[:, 2], -1, 1)
    sky = np.array([0.62, 0.68, 0.76])
    ground = np.array([0.16, 0.15, 0.14])
    env = (0.5 + 0.5 * up)[:, None] * sky + (0.5 - 0.5 * up)[:, None] * ground
    silver = np.array([0.80, 0.82, 0.86])
    plate_c = np.array([0.42, 0.43, 0.45])
    base = np.where(plate[:, None], plate_c, silver)
    # Metal is mostly reflection; the plate stays diffuse.
    metal = ~plate
    rgb = np.where(metal, 0.10, 0.55)[:, None] * (0.35 + 0.65 * np.clip(diff, 0, 1.6) / 1.6)[:, None] * base
    rgb = rgb + np.where(metal, 0.55, 0.08)[:, None] * fres[:, None] * env
    rgb = rgb + np.where(metal, 1.65, 0.05)[:, None] * spec[:, None] * np.array([1.0, 0.98, 0.94])
    rgb = rgb + np.where(metal, 0.45, 0.05)[:, None] * soft[:, None] * base
    hot = np.clip((temp - SOLIDUS) / 420.0, 0, 1) * metal
    glow = np.array([1.0, 0.38, 0.06])
    rgb = rgb * (1.0 - 0.82 * hot[:, None]) + glow * (0.82 * hot[:, None])
    rgb = rgb + (0.55 * hot * spec)[:, None]
    return np.clip(rgb, 0, 1)


def shade_faces(xyz, faces, vcol):
    """Drop back faces and split the rest once so the specular band is smooth."""
    tri = xyz[faces]
    fn = np.cross(tri[:, 2] - tri[:, 0], tri[:, 1] - tri[:, 0])
    fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-15
    keep = faces[fn @ VIEW > -0.04]
    a, b, c = keep.T
    p0, p1, p2 = xyz[a], xyz[b], xyz[c]
    c0, c1, c2 = vcol[a], vcol[b], vcol[c]
    m01, m12, m20 = 0.5 * (p0 + p1), 0.5 * (p1 + p2), 0.5 * (p2 + p0)
    k01, k12, k20 = 0.5 * (c0 + c1), 0.5 * (c1 + c2), 0.5 * (c2 + c0)
    tris = np.concatenate([
        np.stack([p0, m01, m20], axis=1),
        np.stack([m01, p1, m12], axis=1),
        np.stack([m20, m12, p2], axis=1),
        np.stack([m01, m12, m20], axis=1),
    ], axis=0)
    cols = np.concatenate([
        np.stack([c0, k01, k20], axis=1).mean(1),
        np.stack([k01, c1, k12], axis=1).mean(1),
        np.stack([k20, k12, c2], axis=1).mean(1),
        np.stack([k01, k12, k20], axis=1).mean(1),
    ], axis=0)
    return tris, np.clip(cols, 0, 1)


def _ms_edge(c, v, i, j, level=0.5):
    t = (level - v[i]) / (v[j] - v[i] + 1e-30)
    t = float(np.clip(t, 0.0, 1.0))
    return c[i] + t * (c[j] - c[i])


def _fan(poly):
    return [np.stack([poly[0], poly[i], poly[i + 1]]) for i in range(1, len(poly) - 1)]


def solid_quad(p, v, tv, level=0.5):
    """Triangles covering the part of a quad where alpha >= 0.5.

    p is four (x_index, z_index) corners, ordered p00, p10, p11, p01.
    Each returned triangle is (3, 3): x_index, z_index, temperature.
    """
    mask = sum((1 << i) for i in range(4) if v[i] >= level)
    if mask == 0:
        return []
    c = [np.array([p[i][0], p[i][1], tv[i]], dtype=np.float64) for i in range(4)]
    if mask == 15:
        return _fan([c[0], c[1], c[2], c[3]])
    e01, e12, e23, e30 = (
        _ms_edge(c, v, 0, 1, level),
        _ms_edge(c, v, 1, 2, level),
        _ms_edge(c, v, 2, 3, level),
        _ms_edge(c, v, 3, 0, level),
    )
    table = {
        1: [c[0], e01, e30],
        2: [c[1], e12, e01],
        3: [c[0], c[1], e12, e30],
        4: [c[2], e23, e12],
        6: [c[1], c[2], e23, e01],
        7: [c[0], c[1], c[2], e23, e30],
        8: [c[3], e30, e23],
        9: [c[0], e01, e23, c[3]],
        11: [c[0], c[1], e12, e23, c[3]],
        12: [c[3], e30, e12, c[2]],
        13: [c[0], e01, e12, c[2], c[3]],
        14: [e30, e01, c[1], c[2], c[3]],
    }
    if mask == 5:
        if 0.25 * sum(v) >= level:
            return _fan([c[0], e01, e12, c[2], e23, e30])
        return [np.stack([c[0], e01, e30]), np.stack([c[2], e23, e12])]
    if mask == 10:
        if 0.25 * sum(v) >= level:
            return _fan([c[1], e12, e23, c[3], e30, e01])
        return [np.stack([c[1], e12, e01]), np.stack([c[3], e30, e23])]
    return _fan(table[mask])


def symmetry_cap(xs, zs, vol, tvol, zoom=CAP_ZOOM):
    """Solid cut on y = 0. The edge follows alpha = 0.5, not the grid."""
    nx, nz = vol.shape[0], vol.shape[2]
    xi = np.linspace(0, nx - 1, (nx - 1) * zoom + 1)
    zi = np.linspace(0, nz - 1, (nz - 1) * zoom + 1)
    xx, zz = np.meshgrid(xi, zi, indexing="ij")
    sample = vol[:, 0, :]
    temps = tvol[:, 0, :]
    a2 = map_coordinates(sample, [xx, zz], order=1, prefilter=False)
    t2 = map_coordinates(temps, [xx, zz], order=1, prefilter=False)
    tris = []
    for i in range(xi.size - 1):
        for k in range(zi.size - 1):
            v = (a2[i, k], a2[i + 1, k], a2[i + 1, k + 1], a2[i, k + 1])
            if max(v) < 0.5:
                continue
            p = (
                (xi[i], zi[k]),
                (xi[i + 1], zi[k]),
                (xi[i + 1], zi[k + 1]),
                (xi[i], zi[k + 1]),
            )
            tv = (t2[i, k], t2[i + 1, k], t2[i + 1, k + 1], t2[i, k + 1])
            tris.extend(solid_quad(p, v, tv))
    if not tris:
        return np.zeros((0, 3, 3)), np.zeros((0, 3))
    packed = np.asarray(tris)
    phys = np.empty_like(packed)
    phys[:, :, 0] = axis_map(xs, packed[:, :, 0].ravel()).reshape(packed.shape[:2])
    phys[:, :, 1] = 0.0
    phys[:, :, 2] = axis_map(zs, packed[:, :, 1].ravel()).reshape(packed.shape[:2])
    return phys, packed[:, :, 2]


def frame(tris, rgb, t, writer, png):
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    ax = fig.add_axes([0.0, 0.045, 1.0, 0.90], projection="3d")
    # Axes3D would otherwise shrink itself to a square and leave side bars.
    ax.apply_aspect = lambda position=None: None
    q = tris * 1e3
    ax.add_collection3d(Poly3DCollection(
        q, facecolors=rgb, edgecolors="none", linewidths=0, antialiased=False
    ))
    xx = np.array([[-0.9, 7.2], [-0.9, 7.2]])
    zz = np.array([[-0.2, -0.2], [1.95, 1.95]])
    ax.plot_surface(xx, np.zeros_like(xx), zz, color="#d6e6f5", alpha=0.18,
                    linewidth=0, shade=False)
    ax.text(4.6, 0.02, 1.55, "symmetry plane  y = 0", color="#08306b", fontsize=14)
    ax.set_xlim(-0.9, 7.2)
    ax.set_ylim(0.0, 1.7)
    ax.set_zlim(-0.2, 1.95)
    ax.view_init(elev=ELEV, azim=AZIM)
    ax.set_proj_type("persp")
    ax.set_box_aspect((8.1, 1.7, 2.15), zoom=FRAME_ZOOM)
    ax.dist = DIST
    wide = 16.0 / 9.0
    matplotlib.axes.Axes.set_xlim(ax, -0.095 * wide, 0.090 * wide)
    matplotlib.axes.Axes.set_ylim(ax, -0.095, 0.090)
    ax.set_axis_off()
    fig.suptitle(f"cal95b    t = {t:.2f} s", fontsize=18, y=0.975)
    fig.text(
        0.5, 0.015,
        "after ~1.6 s the bead foot touches the downstream boundary at x = 7 mm",
        ha="center", fontsize=13, color="#7f0000" if t >= 1.6 else "#333333",
    )
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    im = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8).reshape(h, w, 3).copy()
    if writer is not None:
        writer.append_data(im)
    if png is not None:
        fig.savefig(png, dpi=100)
    plt.close(fig)


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
    n_cells = int(max(owner.max(), neighbour.max())) + 1
    bags = cell_point_ids(faces, owner, neighbour, n_cells)
    xs, ys, zs, ix, iy, iz = structured_axes(points)
    print(f"grid {xs.size}x{ys.size}x{zs.size}")
    addressing = load_addressing(CASE, NPROC)
    names = written_times(CASE, NPROC)
    only = set(sys.argv[1:])
    writer = None if only else imageio.get_writer(
        OUT / "cal95b_2s_metallic.mp4",
        fps=FPS, codec="libx264", quality=8, macro_block_size=1,
    )
    kept = 0
    for name in names:
        t = float(name)
        if only and name not in only and f"{t:.2f}" not in only and f"{t:g}" not in only:
            continue
        alpha = gather_scalar(CASE, name, n_cells, addressing, "alpha.metal")
        temp = gather_scalar(CASE, name, n_cells, addressing, "T")
        if alpha is None or temp is None:
            raise SystemExit(f"missing fields at {name}")
        pa = to_point(alpha, bags, points.shape[0])
        pt = to_point(temp, bags, points.shape[0])
        vol = np.empty((xs.size, ys.size, zs.size))
        tvol = np.empty_like(vol)
        vol[ix, iy, iz] = pa
        tvol[ix, iy, iz] = pt
        vol_f, fx, fy, fz = resample_index(vol, SURF_ZOOM)
        verts, tris, _, _ = marching_cubes(vol_f, level=0.5, allow_degenerate=False)
        orig = np.column_stack([
            axis_map(fx, verts[:, 0]),
            axis_map(fy, verts[:, 1]),
            axis_map(fz, verts[:, 2]),
        ])
        xyz = np.column_stack([
            axis_map(xs, orig[:, 0]),
            axis_map(ys, orig[:, 1]),
            axis_map(zs, orig[:, 2]),
        ])
        xyz = smooth_vertices(xyz, tris)
        vt = trilinear(tvol, orig)
        normals = vertex_normals(xyz, tris)
        plate = xyz[:, 2] < 8e-5
        vcol = shade_vertices(xyz, normals, vt, plate)
        tri_xyz, fcol = shade_faces(xyz, tris, vcol)
        # The cut is drawn only when it faces the camera. From +y the outer
        # bead is the subject and the cap would sit behind it.
        cap_n = np.array([0.0, -1.0 if VIEW[1] < 0 else 1.0, 0.0])
        if cap_n[1] * VIEW[1] > 0.25:
            cap, cap_t = symmetry_cap(xs, zs, vol, tvol)
            if cap.shape[0]:
                normals_c = np.tile(cap_n, (cap.shape[0] * 3, 1))
                cap_col = shade_vertices(
                    cap.reshape(-1, 3), normals_c, cap_t.ravel(),
                    cap.reshape(-1, 3)[:, 2] < 8e-5,
                ).reshape(-1, 3, 3).mean(axis=1)
                cap_col = np.clip(cap_col * 0.94, 0, 1)
                tri_xyz = np.concatenate([tri_xyz, cap], axis=0)
                fcol = np.concatenate([fcol, cap_col], axis=0)
        png = None
        if abs(t - 0.8) < 1e-8:
            png = OUT / "cal95b_2s_metallic_t080.png"
        elif abs(t - 2.0) < 1e-8:
            png = OUT / "cal95b_2s_metallic_t200.png"
        frame(tri_xyz, fcol, t, writer, png)
        kept += 1
        if kept % 20 == 1 or only:
            print(f"  t={name} tris {tri_xyz.shape[0]}")
    if writer is not None:
        writer.close()
        print("wrote", OUT / "cal95b_2s_metallic.mp4", "frames", kept)


if __name__ == "__main__":
    main()
