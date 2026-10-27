#!/usr/bin/env python3
"""1920x1080 slit demo: radiograph, smooth centre plane, labelled neck, 3D.

Alpha is interpolated onto a fine regular grid and drawn as a filled
metal region with an alpha = 0.5 contour. The neck title is the centre-plane
slit depth and width in millimetres. Playback is one solver write per frame.

    /home/asb6102/lwded-viz/bin/python results/calibration/taosun03/render_hq_demo.py \
        --case cases/wire_cavity_skincold --tag skincold --fps 20
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from scipy.interpolate import griddata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import render_slit_video as rv
import slit_metric as sm

OUT = HERE
RADIO_PATH = ROOT / "results/calibration/radiograph.png"
YELLOW = "#f4d35e"
METAL = "#1a120c"
PAPER = "#f6f1e4"
INK = "#1a120c"

# x, z in metres. Trailing (+x) is drawn on the left.
FULL = (-1.0e-3, 3.2e-3, -0.25e-3, 2.15e-3)
ZOOM = (0.28e-3, 0.95e-3, 0.30e-3, 1.60e-3)
FULL_DX = 0.008e-3
ZOOM_DX = 0.0025e-3

# 3D crop in metres, then plotted in millimetres.
BOX3 = (-0.8e-3, 2.6e-3, 0.0, 1.5e-3, -0.15e-3, 2.05e-3)


def radio_crop():
    radio = mpimg.imread(RADIO_PATH)
    h, w = radio.shape[:2]
    r0, r1 = int(0.18 * h), int(0.62 * h)
    c0, c1 = int(0.28 * w), int(0.78 * w)
    return radio[r0:r1, c0:c1]


def physics_line(case):
    text = (Path(case) / "constant/meltProperties").read_text()
    laser_at = text.find("\nlaser ")
    laser_chunk = text[laser_at:laser_at + 500] if laser_at >= 0 else ""
    laser_on = "enabled         true" in laser_chunk or "enabled     true" in laser_chunk
    t_start = re.search(r"tStart\s+([0-9.eE+-]+)", laser_chunk)
    if t_start and float(t_start.group(1)) > 0.05:
        laser_on = False
    recoil = re.search(r"recoil\s+(true|false)", text)
    recoil_on = bool(recoil and recoil.group(1) == "true")
    in_shell = re.search(r"recoilInShell\s+(true|false)", text)
    cap = re.search(r"recoilMax\s+([0-9.eE+-]+)", text)
    mara = re.search(r"marangoni\s+(true|false)", text)
    mara_on = bool(mara and mara.group(1) == "true")
    skin_at = text.find("oxideSkin")
    skin_chunk = text[skin_at:skin_at + 250] if skin_at >= 0 else ""
    skin_on = "enabled         true" in skin_chunk or "enabled     true" in skin_chunk
    feed = re.search(r"feedVelocity\s+\(\s*([^)]+)\)", text)
    feed_on = False
    if feed:
        comps = [abs(float(v)) for v in feed.group(1).split()]
        feed_on = max(comps) > 0
    def bit(name, on):
        return f"{name} {'on' if on else 'off'}"
    if not recoil_on:
        recoil_bit = "recoil off"
    elif in_shell and in_shell.group(1) == "false":
        recoil_bit = "recoil off in the shell"
    elif cap:
        recoil_bit = f"recoil cap {cap.group(1)} Pa"
    else:
        recoil_bit = "recoil on"
    return ", ".join([
        bit("laser", laser_on),
        recoil_bit,
        bit("Marangoni", mara_on),
        bit("skin", skin_on),
        bit("feed", feed_on),
    ])


def load_alpha(case, tname):
    case = Path(case)
    procs = sorted(p for p in case.glob("processor*") if p.is_dir())
    xs, ys, zs, aa = [], [], [], []
    for proc in procs:
        alpha_path = proc / tname / "alpha.metal"
        if not alpha_path.is_file():
            continue
        cc = rv.cell_centres(proc / "constant" / "polyMesh")
        alpha = rv.read_scalar(alpha_path)
        if alpha is None or len(alpha) != len(cc):
            raise RuntimeError(f"{alpha_path} does not match the mesh")
        xs.append(cc[:, 0])
        ys.append(cc[:, 1])
        zs.append(cc[:, 2])
        aa.append(alpha)
    if not xs:
        raise RuntimeError(f"no alpha at {tname}")
    return (
        np.concatenate(xs), np.concatenate(ys),
        np.concatenate(zs), np.concatenate(aa),
    )


def plane_samples(x, y, z, a, y_max=2.0e-4, bin_m=1.2e-5):
    """Cells nearest the symmetry plane, one sample per x-z bin."""
    m = (y >= -1e-9) & (y < y_max)
    x, y, z, a = x[m], y[m], z[m], a[m]
    if len(x) < 10:
        raise RuntimeError(f"centre plane has {len(x)} cells")
    kx = np.round(x / bin_m).astype(np.int64)
    kz = np.round(z / bin_m).astype(np.int64)
    key = kx * np.int64(1_000_003) + kz
    order = np.argsort(y, kind="mergesort")
    _, first = np.unique(key[order], return_index=True)
    sel = order[first]
    return x[sel], z[sel], a[sel]


def score_plane(x, y, z, a):
    m = np.abs(y) < 4.0e-5
    if int(m.sum()) < 10:
        m = y < 8.0e-5
    row = sm.measure(x[m] * 1e3, z[m] * 1e3, a[m])
    return row


def regular_grid(x, z, a, box, dx):
    x0, x1, z0, z1 = box
    gx = np.arange(x0, x1 + dx * 0.5, dx)
    gz = np.arange(z0, z1 + dx * 0.5, dx)
    X, Z = np.meshgrid(gx, gz)
    inside = (
        (x >= x0 - 2 * dx) & (x <= x1 + 2 * dx)
        & (z >= z0 - 2 * dx) & (z <= z1 + 2 * dx)
    )
    if int(inside.sum()) < 4:
        return X * 1e3, Z * 1e3, np.full(X.shape, np.nan)
    A = griddata(
        np.column_stack((x[inside], z[inside])),
        a[inside],
        (X, Z),
        method="linear",
    )
    return X * 1e3, Z * 1e3, A


def draw_metal(ax, Xmm, Zmm, A, title):
    ax.set_facecolor(YELLOW)
    if np.isfinite(A).any():
        ax.contourf(
            Xmm, Zmm, A, levels=[0.5, 1.5], colors=[METAL],
        )
        ax.contour(
            Xmm, Zmm, np.ma.masked_invalid(A), levels=[0.5],
            colors=["#f3e6b2"], linewidths=0.7,
        )
    ax.set_xlim(Xmm.max(), Xmm.min())
    ax.set_ylim(Zmm.min(), Zmm.max())
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, color=INK, fontsize=15, pad=6)
    ax.set_xlabel("x [mm]    trailing on the left", color=INK, fontsize=12)
    ax.set_ylabel("z [mm]", color=INK, fontsize=12)
    ax.tick_params(labelsize=11, colors=INK)
    for spine in ax.spines.values():
        spine.set_color("#5c5346")


def mark_slit(ax, row):
    if row["z_lo_mm"] is None or row["width_mm"] <= 0:
        return
    z0, z1 = row["z_lo_mm"], row["z_hi_mm"]
    zmid = 0.5 * (z0 + z1)
    x_face = 0.50
    x_wall = x_face + row["width_mm"]
    ax.annotate(
        "",
        xy=(x_wall, zmid), xytext=(x_face, zmid),
        arrowprops=dict(arrowstyle="<->", color="#8c2f1b", lw=1.4),
    )
    ax.plot([x_wall + 0.012, x_wall + 0.012], [z0, z1], color="#8c2f1b", lw=1.2)
    ax.plot(
        [x_wall + 0.006, x_wall + 0.018], [z0, z0], color="#8c2f1b", lw=1.0,
    )
    ax.plot(
        [x_wall + 0.006, x_wall + 0.018], [z1, z1], color="#8c2f1b", lw=1.0,
    )
    ax.text(
        0.5 * (x_face + x_wall), min(z0, z1) - 0.04,
        f"width {row['width_mm']:.3f} mm",
        color="#8c2f1b", fontsize=12, va="top", ha="center",
    )
    ax.text(
        x_wall + 0.03, zmid, f"depth {row['depth_mm']:.3f} mm",
        color="#8c2f1b", fontsize=12, va="center", ha="left",
    )


def metal_surface(x, y, z, a, dest):
    import pyvista as pv
    x0, x1, y0, y1, z0, z1 = BOX3
    m = (
        (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
        & (z >= z0) & (z <= z1)
    )
    pts = np.column_stack((x[m] * 1e3, y[m] * 1e3, z[m] * 1e3))
    if len(pts) < 50:
        return None
    cloud = pv.PolyData(pts)
    cloud["alpha"] = np.asarray(a[m], dtype=np.float64)
    # Tet size covers the coarse cells. The 0.5 contour still falls inside
    # a gas-filled slit because those cells are in the point set.
    vol = cloud.delaunay_3d(alpha=0.35)
    vol = vol.cell_data_to_point_data()
    surf = vol.contour([0.5], scalars="alpha")
    if surf.n_points < 10:
        return None
    # Light smoothing keeps the slit edges and removes the faceted delaunay look.
    surf = surf.smooth(
        n_iter=30,
        relaxation_factor=0.06,
        feature_smoothing=True,
        feature_angle=75,
        boundary_smoothing=False,
        convergence=0,
    )
    surf.compute_normals(inplace=True, auto_orient_normals=True)
    pl = pv.Plotter(off_screen=True, window_size=(1800, 860))
    pl.set_background(PAPER)
    pl.add_mesh(
        surf, color=METAL, smooth_shading=True,
        specular=0.45, specular_power=18, diffuse=0.75, ambient=0.18,
    )
    wire = pv.Cylinder(
        center=(0.0, 0.0, 0.85), direction=(0, 0, 1),
        radius=0.50, height=1.7, resolution=64,
    )
    wire = wire.clip(normal=(0, -1, 0), origin=(0, 0, 0))
    pl.add_mesh(
        wire, style="wireframe", color="#8a5a2b", line_width=2, opacity=0.9,
    )
    deck = pv.Plane(
        center=(1.0, 0.55, 0.0), direction=(0, 0, 1),
        i_size=3.6, j_size=1.4,
    )
    pl.add_mesh(deck, color="#d9c7a2", opacity=0.55)
    pl.show_bounds(
        grid=False,
        location="outer",
        ticks="outside",
        xtitle="x [mm]",
        ytitle="y [mm]",
        ztitle="z [mm]",
        font_size=12,
        color=INK,
        n_xlabels=4,
        n_ylabels=3,
        n_zlabels=4,
        padding=0.12,
    )
    pl.add_text("wire outline r = 0.50 mm", position="upper_edge", font_size=11, color=INK)
    pl.camera_position = [
        (0.7, 11.5, 1.3),
        (0.7, 0.3, 0.85),
        (0.0, 0.0, 1.0),
    ]
    pl.camera.roll = 180
    pl.camera.zoom(1.15)
    pl.screenshot(str(dest))
    pl.close()
    return dest


def neck_title(row):
    if row["z_lo_mm"] is None:
        return "Neck    no film"
    state = "open" if row["open"] else "capped"
    if not row["persists"]:
        state = "not a steady film"
    return (
        f"Neck    depth {row['depth_mm']:.3f} mm"
        f"    width {row['width_mm']:.3f} mm    {state}"
    )


def render_frame(case, tname, frame_path, iso_path, radio, banner, row, x, y, z, a, t0=0.0):
    px, pz, pa = plane_samples(x, y, z, a)
    Xf, Zf, Af = regular_grid(px, pz, pa, FULL, FULL_DX)
    Xz, Zz, Az = regular_grid(px, pz, pa, ZOOM, ZOOM_DX)
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=PAPER)
    # The 3D view is the wide lower band. The three reference panels sit above it.
    gs = fig.add_gridspec(
        2, 3, height_ratios=[1.0, 1.55],
        left=0.04, right=0.985, top=0.86, bottom=0.04,
        hspace=0.28, wspace=0.18,
    )
    ax_r = fig.add_subplot(gs[0, 0])
    ax_f = fig.add_subplot(gs[0, 1])
    ax_z = fig.add_subplot(gs[0, 2])
    ax_3 = fig.add_subplot(gs[1, :])
    ax_r.imshow(radio)
    ax_r.set_title("Radiograph", color=INK, fontsize=15)
    ax_r.axis("off")
    draw_metal(ax_f, Xf, Zf, Af, "Centre plane")
    draw_metal(ax_z, Xz, Zz, Az, neck_title(row))
    mark_slit(ax_z, row)
    iso = metal_surface(x, y, z, a, iso_path)
    ax_3.axis("off")
    ax_3.set_facecolor(PAPER)
    if iso is not None and Path(iso).is_file():
        ax_3.imshow(mpimg.imread(iso), aspect="auto")
        ax_3.set_title("Metal surface", color=INK, fontsize=15)
    else:
        ax_3.set_title("Metal surface (unavailable)", color=INK, fontsize=15)
    t_ms = (float(tname) - t0) * 1e3
    clock = f"t = {t_ms:.1f} ms"
    if t0 > 0:
        clock += " from the settled neck"
    fig.suptitle(
        f"{clock}\n{banner}",
        color=INK, fontsize=16, y=0.98,
    )
    fig.savefig(frame_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    return frame_path


def encode(frames, dest, fps):
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    lst = dest.with_suffix(".frames.txt")
    # One write, one frame. No held stills.
    lines = [f"file '{p}'" for p in frames]
    lst.write_text("\n".join(lines) + "\n")
    cmd = [
        ffmpeg, "-y", "-f", "concat", "-safe", "0", "-r", str(fps),
        "-i", str(lst),
        "-vf", "scale=1920:1080:flags=lanczos,format=yuv420p",
        "-r", str(fps), "-movflags", "+faststart", str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return dest


def duration_s(path):
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    probe = subprocess.run(
        [ffmpeg, "-i", str(path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", probe.stderr)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--preview", default="", help="Render only this time name")
    ap.add_argument("--out", default="")
    ap.add_argument("--t0", type=float, default=0.0, help="Subtract from the clock, seconds")
    ap.add_argument("--banner", default="", help="Replace the physics line")
    args = ap.parse_args()
    case = Path(args.case)
    if not case.is_dir():
        case = ROOT / args.case
    banner = args.banner or physics_line(case)
    print("PHYSICS", banner)
    radio = radio_crop()
    frame_dir = OUT / "frames" / args.tag
    frame_dir.mkdir(parents=True, exist_ok=True)
    if args.preview:
        names = [args.preview]
    else:
        names = []
        for p in (case / "processor0").iterdir():
            if (
                p.is_dir()
                and rv.time_value(p.name) is not None
                and (p / "alpha.metal").is_file()
            ):
                names.append(p.name)
        names.sort(key=float)
    frames = []
    for i, name in enumerate(names):
        x, y, z, a = load_alpha(case, name)
        row = score_plane(x, y, z, a)
        print(f"t={name}: {sm.fmt(row)}")
        frame = frame_dir / f"frame_{i:04d}.png"
        iso = frame_dir / f"iso_{i:04d}.png"
        render_frame(
            case, name, frame, iso, radio, banner, row, x, y, z, a, t0=args.t0,
        )
        frames.append(frame)
        print("wrote", frame)
    if args.preview:
        return
    dest = Path(args.out) if args.out else OUT / f"{args.tag}_slit_demo.mp4"
    encode(frames, dest, args.fps)
    dur = duration_s(dest)
    print(f"VIDEO {dest} frames {len(frames)} fps {args.fps} duration_s {dur}")


if __name__ == "__main__":
    main()
