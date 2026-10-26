#!/usr/bin/env python3
"""Demo video: radiograph, centre plane, zoomed neck, 3D metal surface.

Metal is dark on yellow. Trailing side (+x) is on the left. Frames come from
whatever times are already on disk (side-plane samples, or the volume field
when the side plane has not been written yet). Re-run it as the solver
writes more times; the mp4 is replaced with the longer cut.

    /home/asb6102/lwded-viz/bin/python results/calibration/taosun03/render_slit_video.py
    /home/asb6102/lwded-viz/bin/python results/calibration/taosun03/render_slit_video.py --tag smokeA
"""
import argparse
import subprocess
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
RADIO_PATH = ROOT / "results/calibration/radiograph.png"

CMAP = LinearSegmentedColormap.from_list(
    "metal_dark_yellow",
    ["#f4d35e", "#c48a2a", "#5c3a16", "#1a120c"],
)
YELLOW = "#f4d35e"
WIRE_R = 0.5e-3

# Wide centre plane, and the neck crop the radiograph is compared with.
FULL = (-1.2e-3, 3.2e-3, -0.15e-3, 2.15e-3, 0.04e-3)
ZOOM = (-0.15e-3, 1.35e-3, 0.40e-3, 1.90e-3, 0.02e-3)


def radio_crop():
    radio = mpimg.imread(RADIO_PATH)
    h, w = radio.shape[:2]
    r0, r1 = int(0.18 * h), int(0.62 * h)
    c0, c1 = int(0.28 * w), int(0.78 * w)
    return radio[r0:r1, c0:c1]


def after_banner(data):
    marker = b"// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n"
    i = data.find(marker)
    if i < 0:
        raise RuntimeError("OpenFOAM banner missing")
    return data[i + len(marker):].lstrip()


def read_labels(path):
    rest = after_banner(path.read_bytes())
    n_str, _, rest = rest.partition(b"\n")
    n = int(n_str.strip())
    if not rest.startswith(b"("):
        raise RuntimeError(f"{path} is not a binary label list")
    return np.frombuffer(rest[1:1 + n * 4], dtype="<i4").copy()


def read_points(path):
    rest = after_banner(path.read_bytes())
    n_str, _, rest = rest.partition(b"\n")
    n = int(n_str.strip(b"() "))
    if rest.startswith(b"("):
        rest = rest[1:]
    return np.frombuffer(rest[:n * 24], dtype="<f8").reshape(n, 3).copy()


def read_faces(path):
    rest = after_banner(path.read_bytes())
    n_str, _, rest = rest.partition(b"\n")
    n_off = int(n_str.strip())
    if not rest.startswith(b"("):
        raise RuntimeError(f"{path} is not a binary face list")
    offs = np.frombuffer(rest[1:1 + n_off * 4], dtype="<i4").copy()
    rest = rest[1 + n_off * 4:]
    end = rest.find(b"(")
    nlab = int(rest[:end].strip(b")\n "))
    labels = np.frombuffer(rest[end + 1:end + 1 + nlab * 4], dtype="<i4").copy()
    return offs, labels


def read_scalar(path):
    data = path.read_bytes()
    key = b"internalField   nonuniform List<scalar>"
    i = data.find(key)
    if i < 0:
        return None
    rest = data[i + len(key):].lstrip()
    n_str, _, rest = rest.partition(b"\n")
    n = int(n_str.strip())
    if rest.startswith(b"("):
        rest = rest[1:]
    if len(rest) < n * 8:
        return None
    return np.frombuffer(rest[:n * 8], dtype="<f8").copy()


MESHES = {}


def cell_centres(mesh_dir):
    key = str(mesh_dir)
    if key in MESHES:
        return MESHES[key]
    pts = read_points(mesh_dir / "points")
    offs, labs = read_faces(mesh_dir / "faces")
    owner = read_labels(mesh_dir / "owner")
    neigh = read_labels(mesh_dir / "neighbour")
    n_faces = len(owner)
    n_cells = int(max(int(owner.max()), int(neigh.max()))) + 1
    if len(offs) == n_faces + 1 and np.all(np.diff(offs) == 4):
        fc = pts[labs.reshape(-1, 4)].mean(axis=1)
    else:
        fc = np.zeros((n_faces, 3))
        for i in range(n_faces):
            fc[i] = pts[labs[offs[i]:offs[i + 1]]].mean(axis=0)
    cc = np.zeros((n_cells, 3))
    cnt = np.zeros(n_cells)
    np.add.at(cc, owner, fc)
    np.add.at(cnt, owner, 1)
    np.add.at(cc, neigh, fc[:len(neigh)])
    np.add.at(cnt, neigh, 1)
    cc /= np.maximum(cnt, 1)[:, None]
    MESHES[key] = cc
    return cc


def time_value(name):
    try:
        return float(name)
    except ValueError:
        return None


def volume_sources(case):
    """(time, [(mesh_dir, alpha_path), ...]) newest last."""
    proc0 = case / "processor0"
    if proc0.is_dir():
        names = []
        for d in proc0.iterdir():
            tv = time_value(d.name)
            if tv is None:
                continue
            if (d / "alpha.metal").is_file():
                names.append((tv, d.name))
        names.sort()
        out = []
        procs = sorted(p for p in case.glob("processor*") if p.is_dir())
        for tv, name in names:
            parts = []
            ok = True
            for proc in procs:
                alpha = proc / name / "alpha.metal"
                mesh = proc / "constant" / "polyMesh"
                if not alpha.is_file() or not mesh.is_dir():
                    ok = False
                    break
                parts.append((mesh, alpha))
            if ok:
                out.append((tv, parts))
        return out
    out = []
    mesh = case / "constant" / "polyMesh"
    if not mesh.is_dir():
        return out
    for d in case.iterdir():
        tv = time_value(d.name)
        if tv is None or not d.is_dir():
            continue
        alpha = d / "alpha.metal"
        if alpha.is_file():
            out.append((tv, [(mesh, alpha)]))
    out.sort()
    return out


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


def side_at(case, tv):
    chunks = []
    roots = [case / "postProcessing" / "sidePlane"]
    roots.extend(case.glob("processor*/postProcessing/sidePlane"))
    for root in roots:
        if not root.is_dir():
            continue
        for d in root.iterdir():
            got = time_value(d.name)
            if got is None or abs(got - tv) > 1e-8:
                continue
            raw = load_raw(d / "alpha.metal_xz.raw")
            if raw is not None and len(raw):
                chunks.append(raw)
    if not chunks:
        return None
    return np.vstack(chunks)


def load_volume(parts):
    xs, ys, zs, aa = [], [], [], []
    for mesh, alpha_path in parts:
        cc = cell_centres(mesh)
        alpha = read_scalar(alpha_path)
        if alpha is None or len(alpha) != len(cc):
            continue
        xs.append(cc[:, 0])
        ys.append(cc[:, 1])
        zs.append(cc[:, 2])
        aa.append(alpha)
    if not xs:
        return None
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(zs), np.concatenate(aa)


def raster(x, z, val, box):
    x0, x1, z0, z1, dx = box
    xe = np.arange(x0, x1 + dx * 0.5, dx)
    ze = np.arange(z0, z1 + dx * 0.5, dx)
    m = (x >= x0) & (x <= x1) & (z >= z0) & (z <= z1) & np.isfinite(val)
    if not np.any(m):
        return np.zeros((len(ze) - 1, len(xe) - 1)), [x1 * 1e3, x0 * 1e3, z0 * 1e3, z1 * 1e3]
    H, _, _ = np.histogram2d(x[m], z[m], bins=[xe, ze], weights=val[m])
    C, _, _ = np.histogram2d(x[m], z[m], bins=[xe, ze])
    img = np.zeros(H.T.shape)
    hit = C.T > 0
    np.divide(H.T, C.T, out=img, where=hit)
    img = img[:, ::-1]
    extent = [x1 * 1e3, x0 * 1e3, z0 * 1e3, z1 * 1e3]
    return img, extent


def plane_from_volume(vol):
    x, y, z, a = vol
    m = y < 4.0e-5
    return x[m], z[m], a[m]


def slit_on_zoom(img, box):
    """Gas between the wire face and the bead, on the zoomed centre plane.

    A slit is about 0.03-0.08 mm wide (one to four 19 µm cells) and at least
    0.25 mm deep. Width at the 0.10 mm search cap is a wide gap, not the slit.
    """
    x0, x1, z0, z1, dx = box
    # img columns were flipped so column 0 is x1 (trailing / +x on the left).
    xs = np.arange(x1, x0 - dx * 0.5, -dx)
    zs = np.arange(z0, z1, dx) + 0.5 * dx
    # wire trailing face sits near x = +R. Walk outward (+x) from just inside.
    widths = []
    z_hit = []
    for iz, zv in enumerate(zs):
        if zv < 0.55e-3 or zv > 1.45e-3:
            continue
        row = img[iz] if iz < img.shape[0] else None
        if row is None:
            continue
        # find the column nearest the wire face, then step toward +x (left, decreasing index)
        i_face = int(np.argmin(np.abs(xs - WIRE_R)))
        gas = 0
        saw_metal_out = False
        width = 0.0
        for i in range(i_face, -1, -1):
            if row[i] < 0.5:
                gas += 1
                width += dx
            elif gas:
                saw_metal_out = True
                break
            else:
                break
        if saw_metal_out and 0.025e-3 <= width <= 0.08e-3:
            widths.append(width)
            z_hit.append(zv)
    if len(z_hit) < 3:
        return None
    z_hit = np.asarray(z_hit)
    # longest contiguous run
    breaks = np.where(np.diff(z_hit) > 1.6 * dx)[0]
    spans = []
    start = 0
    for b in list(breaks) + [len(z_hit) - 1]:
        spans.append((start, b if b == len(z_hit) - 1 else b))
        start = b + 1
    # fix span ends: each segment start..end inclusive
    best = None
    i0 = 0
    for b in list(np.where(np.diff(z_hit) > 1.6 * dx)[0]) + [len(z_hit) - 1]:
        seg = z_hit[i0:b + 1]
        wseg = np.asarray(widths[i0:b + 1])
        depth = float(seg[-1] - seg[0]) if len(seg) else 0.0
        if best is None or depth > best[0]:
            best = (depth, float(np.median(wseg)), float(seg[0]), float(seg[-1]))
        i0 = b + 1
    if best is None or best[0] < 0.25e-3:
        return None
    return {"depth": best[0], "width": best[1], "z0": best[2], "z1": best[3]}


def iso_image(vol, dest):
    try:
        import pyvista as pv
    except ImportError:
        return None
    x, y, z, a = vol
    # Neck and the near bead. 40 µm voxels are enough to see a 0.05 mm gap.
    x0, x1 = -1.0e-3, 2.8e-3
    y0, y1 = 0.0, 1.6e-3
    z0, z1 = -0.2e-3, 2.1e-3
    dx = 0.04e-3
    m = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1) & (z >= z0) & (z <= z1)
    if int(m.sum()) < 20:
        return None
    xe = np.arange(x0, x1 + dx * 0.5, dx)
    ye = np.arange(y0, y1 + dx * 0.5, dx)
    ze = np.arange(z0, z1 + dx * 0.5, dx)
    nx, ny, nz = len(xe) - 1, len(ye) - 1, len(ze) - 1
    ix = np.clip(((x[m] - x0) / dx).astype(int), 0, nx - 1)
    iy = np.clip(((y[m] - y0) / dx).astype(int), 0, ny - 1)
    iz = np.clip(((z[m] - z0) / dx).astype(int), 0, nz - 1)
    acc = np.zeros((nz, ny, nx))
    cnt = np.zeros((nz, ny, nx))
    np.add.at(acc, (iz, iy, ix), a[m])
    np.add.at(cnt, (iz, iy, ix), 1)
    vox = np.zeros_like(acc)
    hit = cnt > 0
    vox[hit] = acc[hit] / cnt[hit]
    grid = pv.ImageData(
        dimensions=(nx, ny, nz),
        spacing=(dx, dx, dx),
        origin=(x0 + 0.5 * dx, y0 + 0.5 * dx, z0 + 0.5 * dx),
    )
    # VTK stores x fastest, which is C order of a (z, y, x) array.
    grid.point_data["alpha"] = np.ascontiguousarray(vox).ravel(order="C")
    surf = grid.contour([0.5], scalars="alpha")
    if surf.n_points == 0:
        return None
    print(f"iso x {surf.bounds[0]*1e3:.2f}..{surf.bounds[1]*1e3:.2f} mm  "
          f"z {surf.bounds[4]*1e3:.2f}..{surf.bounds[5]*1e3:.2f} mm  pts {surf.n_points}")
    pl = pv.Plotter(off_screen=True, window_size=(640, 720))
    pl.set_background(YELLOW)
    pl.add_mesh(surf, color="#1a120c", smooth_shading=True)
    pl.camera_position = [
        (0.0008, 0.014, 0.0011),
        (0.0007, 0.0, 0.0009),
        (0.0, 0.0, 1.0),
    ]
    # Camera on +y puts +x on the right. Roll so the trailing face is on the left.
    pl.camera.roll = 180
    pl.screenshot(str(dest))
    pl.close()
    return dest


def draw_frame(tag, tv, plane_x, plane_z, plane_a, vol, radio, frame_path, iso_path):
    full, full_ext = raster(plane_x, plane_z, plane_a, FULL)
    zoom, zoom_ext = raster(plane_x, plane_z, plane_a, ZOOM)
    slit = slit_on_zoom(zoom, ZOOM)
    fig, ax = plt.subplots(1, 4, figsize=(14.2, 4.8))
    fig.patch.set_facecolor("#f7f1dc")
    ax[0].imshow(radio)
    ax[0].set_title("Radiograph")
    ax[0].axis("off")
    for a, img, ext, title in (
        (ax[1], full, full_ext, "Centre plane"),
        (ax[2], zoom, zoom_ext, "Neck"),
    ):
        a.imshow(img, origin="lower", extent=ext, cmap=CMAP, vmin=0, vmax=1,
                 interpolation="nearest", aspect="equal")
        a.set_facecolor(YELLOW)
        a.set_title(title)
        a.set_xlabel("trailing  ←  x [mm]")
        a.set_ylabel("z [mm]")
    iso = iso_image(vol, iso_path) if vol is not None else None
    if iso is not None and Path(iso).is_file():
        ax[3].imshow(mpimg.imread(iso))
        ax[3].set_title("Metal surface")
    else:
        ax[3].set_facecolor(YELLOW)
        ax[3].text(0.5, 0.5, "no surface", ha="center", va="center")
        ax[3].set_title("Metal surface")
    ax[3].axis("off")
    note = f"{tag}    t = {tv:.4f} s"
    if slit:
        note += f"    slit {slit['depth']*1e3:.2f} mm × {slit['width']*1e3:.3f} mm"
    fig.suptitle(note, fontsize=13)
    fig.tight_layout()
    fig.savefig(frame_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    return slit


def encode(frames, dest):
    if len(frames) < 1:
        return None
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    list_file = dest.with_suffix(".frames.txt")
    # Hold each frame. A handful of writes should still read as a clip.
    dur = 0.35 if len(frames) < 8 else 0.18
    lines = []
    for frame in frames:
        lines.append(f"file '{frame}'")
        lines.append(f"duration {dur}")
    lines.append(f"file '{frames[-1]}'")
    list_file.write_text("\n".join(lines) + "\n")
    cmd = [
        ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dest


def render_case(tag, min_frames):
    case = CASES / f"wire_cavity_{tag}"
    if not case.is_dir():
        print("no case", tag)
        return None
    sources = volume_sources(case)
    if len(sources) < min_frames:
        print(f"{tag}: {len(sources)} volume times, waiting for {min_frames}")
        return None
    radio = radio_crop()
    frame_dir = OUT / "frames" / tag
    frame_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    slit_best = None
    for i, (tv, parts) in enumerate(sources):
        vol = load_volume(parts)
        side = side_at(case, tv)
        if side is not None:
            px, pz, pa = side[:, 0], side[:, 2], side[:, 3]
        elif vol is not None:
            px, pz, pa = plane_from_volume(vol)
        else:
            continue
        frame = frame_dir / f"frame_{i:04d}.png"
        iso = frame_dir / f"iso_{i:04d}.png"
        slit = draw_frame(tag, tv, px, pz, pa, vol, radio, frame, iso)
        frames.append(frame)
        if slit and (slit_best is None or slit["depth"] > slit_best["depth"]):
            slit_best = dict(slit, t=tv, tag=tag)
        print(f"{tag} t={tv:.4f} slit={slit}")
    dest = OUT / f"{tag}_slit_demo.mp4"
    encode(frames, dest)
    print("wrote", dest, "frames", len(frames))
    if slit_best:
        line = (f"{slit_best['tag']} t={slit_best['t']:.4f} "
                f"depth_mm={slit_best['depth']*1e3:.3f} "
                f"width_mm={slit_best['width']*1e3:.3f}")
        (OUT / "slit_found.txt").write_text(line + "\n")
        print("SLIT", line)
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", action="append", default=[])
    ap.add_argument("--min-frames", type=int, default=2)
    args = ap.parse_args()
    tags = args.tag or [f"smoke{s}" for s in "ABCDEF"] + ["slitfull"]
    wrote = []
    for tag in tags:
        dest = render_case(tag, args.min_frames)
        if dest is not None:
            wrote.append(dest)
    if not wrote:
        sys.exit(2)
    # The clip to watch is the one with the most frames, slitfull first if present.
    if any("slitfull" in str(p) for p in wrote):
        print("DEMO", OUT / "slitfull_slit_demo.mp4")
    else:
        print("DEMO", wrote[-1])


if __name__ == "__main__":
    main()
