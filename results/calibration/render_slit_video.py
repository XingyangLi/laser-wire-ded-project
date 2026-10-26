#!/usr/bin/env python3
"""Video of the center plane beside the radiograph, plus a zoomed neck.

Metal is dark, gas is white, trailing side on the left. Each frame is labelled
with the simulated time. Frames are written next to the video so a run can be
re-encoded as more side-plane samples appear.

    python3 results/calibration/render_slit_video.py \
        --case cases/wire_cavity_cal38 --tag cal38 \
        --out results/calibration/slit_demo.mp4
"""
import argparse
import shutil
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.tri import Triangulation

from plot_slit_neck import CROP, draw_neck
from slit_metric import fmt, load_alpha, measure, side_times

ROOT = Path("/home/xingyang/laser-wire-ded-project")
WIRE_R = 0.5


def draw_side(ax, x, z, alpha, title):
    """x, z in millimetres, lab frame. Trailing (+x) is drawn on the left."""
    plot_x = -x
    m = (x > -3.4) & (x < 3.6) & (z > -0.7) & (z < 2.35)
    px, pz, pa = plot_x[m], z[m], alpha[m]
    tri = Triangulation(px, pz)
    xt, zt = px[tri.triangles], pz[tri.triangles]
    tri.set_mask((np.ptp(xt, axis=1) > 0.45) | (np.ptp(zt, axis=1) > 0.45))
    levels = np.linspace(0.0, 1.0, 17)
    levels[0] = -1e-3
    levels[-1] = 1.0 + 1e-3
    ax.tricontourf(tri, pa, levels=levels, cmap="gray_r", vmin=0, vmax=1)
    ax.tricontour(tri, pa, levels=[0.5], colors=["#d94801"], linewidths=0.8)
    ax.axhline(0.0, color="#1f4e79", lw=0.8)
    ax.plot([-WIRE_R, -WIRE_R], [0.0, 2.2], color="#2ca02c", lw=0.7, ls="--")
    ax.plot([WIRE_R, WIRE_R], [0.0, 2.2], color="#2ca02c", lw=0.7, ls="--")
    ax.set_aspect("equal")
    ax.set_xlim(-3.3, 3.2)
    ax.set_ylim(-0.55, 2.25)
    ax.set_xlabel("trailing  ←  x [mm]  →  leading")
    ax.set_ylabel("z [mm]")
    ax.set_title(title, fontsize=9)


def render_frame(case, time_name, tag, radio, out_png):
    x, z, alpha = load_alpha(case, time_name)
    row = measure(x, z, alpha)
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 4.5))
    l, t, r, b = CROP
    crop = radio[t:b, l:r]
    axes[0].imshow(crop, cmap="gray", vmin=0, vmax=1 if crop.dtype.kind == "f" else 255)
    axes[0].set_title("Radiograph", fontsize=9)
    axes[0].axis("off")
    t_ms = float(time_name) * 1e3
    draw_side(axes[1], x, z, alpha, "Center plane")
    draw_neck(
        axes[2], x, z, alpha,
        f"Neck  {row['depth_mm']:.2f} mm × {row['width_mm']:.3f} mm",
    )
    state = "open" if row["open"] else "capped"
    fig.suptitle(
        f"{tag}    t = {t_ms:.0f} ms    slit {state}, depth {row['depth_mm']:.2f} mm, "
        f"width {row['width_mm']:.3f} mm\n"
        "Dark is metal, white is gas. Trailing side is on the left.",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    print(f"{tag} t={time_name}: {fmt(row)}")
    return row


def encode(frame_dir, out, fps):
    pngs = sorted(frame_dir.glob("frame_*.png"))
    if len(pngs) < 1:
        raise SystemExit(f"no frames in {frame_dir}")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        exe = shutil.which("ffmpeg")
    if not exe:
        gif = out.with_suffix(".gif")
        frames = [plt.imread(p) for p in pngs]
        import PIL.Image
        ims = [PIL.Image.fromarray((f * 255).astype(np.uint8) if f.dtype.kind == "f" else f) for f in frames]
        ims[0].save(gif, save_all=True, append_images=ims[1:], duration=int(1000 / fps), loop=0)
        print("wrote", gif)
        return gif
    # libx264 wants even width and height. The pngs are already even enough
    # after a scale filter.
    cmd = [
        exe, "-y", "-framerate", str(fps),
        "-i", str(frame_dir / "frame_%04d.png"),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        str(out),
    ]
    subprocess.check_call(cmd)
    print("wrote", out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=4)
    ap.add_argument("--times", nargs="*", default=[])
    args = ap.parse_args()
    case = Path(args.case)
    tag = args.tag or case.name.replace("wire_cavity_", "")
    times = args.times or side_times(case)
    if not times:
        raise SystemExit(f"no side-plane samples in {case}")
    frame_dir = Path(args.out).with_suffix("") 
    # results/calibration/slit_demo.mp4 -> results/calibration/slit_demo_frames
    frame_dir = Path(args.out).parent / (Path(args.out).stem + "_frames")
    if frame_dir.exists():
        shutil.rmtree(frame_dir)
    frame_dir.mkdir(parents=True)
    radio = plt.imread(ROOT / "results/calibration/radiograph.png")
    for i, time_name in enumerate(times):
        render_frame(case, time_name, tag, radio, frame_dir / f"frame_{i:04d}.png")
    encode(frame_dir, args.out, args.fps)


if __name__ == "__main__":
    main()
