#!/usr/bin/env python3
"""
visualize_multicomp.py - renders for multi-component (Fe/Ni strand) laserWireDEDFoam cases.

Colours: substrate (Invar) grey, Fe red, Ni blue (rule-of-mixtures blend in mixed cells);
never-melted wire: Fe yellow outline / iso-surface, Ni cyan.

Outputs (--out):
  latest_3d_composition.png   free surface coloured by composition + translucent "x-ray" view
                              with the never-melted Fe / Ni iso-surfaces
  latest_3d_T.png             free surface coloured by T (visualize.render_3d)
  latest_top_composition.png  top view of the track coloured by surface composition
  latest_section_long.png     y = 0 section: composition, never-melted wire, T + liquidus
  domain_cross_sections.png   x = const sections of the final field (lab positions)
  build_cross_sections.png    cross-sections at several positions ALONG THE BUILD from the recording
                              plane (fine mesh, solid track) - unmelted Fe/Ni outlined
  build_long_section.png      y = 0 long section + top-view projection of the reconstructed build
  wire_closeup_composition.png  3D close-up of the strands + horizontal sections at 5 heights
  unmelted_timeseries.png     never-melted Fe / Ni fractions vs time (components.dat)
  frames/, animation.mp4/.gif 3D composition + long section per written time
  summary_multicomp.json      never-melted fractions, fragment count/sizes, composition of the build
Usage:
  python visualize_multicomp.py --case CASE --out OUTDIR [--only-latest] [--build-xs 0.5,1,2,3,4]
"""
import argparse, glob, json, math, os, subprocess, sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pyvista as pv
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import visualize as V  # noqa: E402

pv.OFF_SCREEN = True
GREY = np.array([0.62, 0.62, 0.62]); RED = np.array([0.85, 0.15, 0.10]); BLUE = np.array([0.15, 0.35, 0.90])
GAS = np.array([1.0, 1.0, 1.0])


def rgb_from(alpha, cFe, cNi):
    a = np.clip(alpha, 0, 1)[..., None]
    cFe = np.clip(cFe, 0, 1)[..., None]; cNi = np.clip(cNi, 0, 1)[..., None]
    cs = np.clip(1 - cFe - cNi, 0, 1)
    metal = cs * GREY + cFe * RED + cNi * BLUE
    return np.clip(a * metal + (1 - a) * GAS, 0, 1)


def legend_handles():
    return [Patch(color=GREY, label="Invar substrate"), Patch(color=RED, label="Fe (wire)"),
            Patch(color=BLUE, label="Ni (wire)"), Patch(facecolor="none", edgecolor="yellow", lw=2,
            label="never-melted Fe"), Patch(facecolor="none", edgecolor="cyan", lw=2, label="never-melted Ni")]


def sample_plane(mesh, normal_axis, value, a_rng, b_rng, h):
    """sample cell data on a regular grid in the plane axis=value; returns dict of 2D arrays [b, a]."""
    na = int(round((a_rng[1] - a_rng[0]) / h)) + 1
    nb = int(round((b_rng[1] - b_rng[0]) / h)) + 1
    A, B = np.meshgrid(np.linspace(*a_rng, na), np.linspace(*b_rng, nb))
    pts = np.zeros((A.size, 3))
    ax = {"x": 0, "y": 1, "z": 2}[normal_axis]
    others = [i for i in range(3) if i != ax]
    pts[:, ax] = value; pts[:, others[0]] = A.ravel(); pts[:, others[1]] = B.ravel()
    cloud = pv.PolyData(pts)
    cm = mesh.copy(); cm.point_data.clear()
    s = cloud.sample(cm)
    out = {}
    for k in s.point_data.keys():
        arr = np.asarray(s.point_data[k])
        if arr.ndim == 1:
            out[k] = arr.reshape(nb, na)
    out["_A"], out["_B"] = A, B
    return out


def draw_comp(ax, d, extent, title, T=None, Tliq=None):
    img = rgb_from(d["alpha.metal"], d["cFe"], d["cNi"])
    ax.imshow(img, origin="lower", extent=extent, interpolation="nearest", aspect="equal")
    for key, col in (("uFe", "yellow"), ("uNi", "cyan")):
        if key in d:
            m = (d[key] > 0.5) & (d["alpha.metal"] > 0.3)
            if m.any():
                ax.contour(d["_A"] * 1e3, d["_B"] * 1e3, m.astype(float), levels=[0.5], colors=col, linewidths=1.6)
    if T is not None and Tliq is not None:
        ax.contour(d["_A"] * 1e3, d["_B"] * 1e3, T, levels=[Tliq], colors="k", linewidths=0.8, linestyles="--")
    ax.set_title(title, fontsize=9)


# ---------------------------------------------------------------------------
def point_mesh(mesh):
    keys = ["alpha.metal", "cFe", "cNi", "uFe", "uNi", "T"]
    if all(k in mesh.point_data for k in keys):
        return mesh
    return mesh.cell_data_to_point_data(pass_cell_data=True)


def render_3d_comp(mesh, prm, fname, t):
    pm = point_mesh(mesh)
    surf = pm.contour([0.5], scalars="alpha.metal")
    if surf.n_points == 0:
        return False
    surf = surf.sample(pm) if "cFe" not in surf.point_data else surf
    rgb = rgb_from(np.ones(surf.n_points), surf.point_data["cFe"], surf.point_data["cNi"])
    surf.point_data["rgb"] = (rgb * 255).astype(np.uint8)
    pl = pv.Plotter(off_screen=True, window_size=(1800, 800), shape=(1, 2))
    pl.set_background("white")
    cam = [(-7e-3, -9e-3, 7e-3), (1.0e-3, 0, 0), (0, 0, 1)]
    pl.subplot(0, 0)
    pl.add_mesh(surf, scalars="rgb", rgb=True, smooth_shading=True, specular=0.2)
    pl.add_text(f"composition   t = {t*1e3:.0f} ms   (grey Invar, red Fe, blue Ni)", font_size=11, color="black")
    pl.camera_position = cam; pl.camera.zoom(1.3)
    pl.subplot(0, 1)
    pl.add_mesh(surf, color="lightgrey", opacity=0.18)
    for key, col, lab in (("uFe", "gold", "never-melted Fe"), ("uNi", "cyan", "never-melted Ni")):
        try:
            pm[key + "_metal"] = np.asarray(pm.point_data["alpha.metal"]) * np.asarray(pm.point_data[key])
            iso = pm.contour([0.5], scalars=key + "_metal")
        except Exception:
            iso = None
        if iso is not None and iso.n_points:
            pl.add_mesh(iso, color=col, smooth_shading=True, label=lab)
    pl.add_text("x-ray: never-melted wire (gold Fe, cyan Ni)", font_size=11, color="black")
    pl.camera_position = cam; pl.camera.zoom(1.3)
    pl.screenshot(fname); pl.close()
    return True


def render_top_comp(mesh, prm, fname, t):
    pm = point_mesh(mesh)
    surf = pm.contour([0.5], scalars="alpha.metal")
    if surf.n_points == 0:
        return
    rgb = rgb_from(np.ones(surf.n_points), surf.point_data["cFe"], surf.point_data["cNi"])
    surf.point_data["rgb"] = (rgb * 255).astype(np.uint8)
    pl = pv.Plotter(off_screen=True, window_size=(1600, 700))
    pl.set_background("white")
    pl.add_mesh(surf, scalars="rgb", rgb=True, smooth_shading=True)
    pl.camera_position = "xy"; pl.enable_parallel_projection(); pl.camera.zoom(1.5)
    pl.add_text(f"top view, surface composition, t = {t*1e3:.0f} ms (substrate moves +x; track = x > 0)",
                font_size=11, color="black")
    pl.screenshot(fname); pl.close()


def long_section(mesh, prm, fname, t):
    x0, x1 = prm["domain"][0][0], prm["domain"][1][0]
    d = sample_plane(mesh, "y", 1e-6, (x0, x1), (-1.2e-3, 2.4e-3), 25e-6)
    Tliq = 1730.0
    ext = [x0 * 1e3, x1 * 1e3, -1.2, 2.4]
    fig, axs = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    draw_comp(axs[0], d, ext, f"y = 0 section, composition + never-melted wire, t = {t*1e3:.0f} ms", d["T"], Tliq)
    axs[0].legend(handles=legend_handles(), fontsize=7, loc="upper right", ncol=5)
    unm = np.where(d["alpha.metal"] > 0.3, d["uFe"] + d["uNi"], np.nan)
    im = axs[1].imshow(unm, origin="lower", extent=ext, cmap="magma", vmin=0, vmax=1, aspect="equal")
    axs[1].set_title("never-melted wire fraction (u_Fe + u_Ni) in the metal", fontsize=9)
    plt.colorbar(im, ax=axs[1], fraction=0.02)
    Tm = np.where(d["alpha.metal"] > 0.3, d["T"], np.nan)
    im = axs[2].imshow(Tm, origin="lower", extent=ext, cmap="turbo", vmin=300, vmax=3000, aspect="equal")
    axs[2].contour(d["_A"] * 1e3, d["_B"] * 1e3, d["T"], levels=[1730], colors="w", linewidths=0.8)
    axs[2].contour(d["_A"] * 1e3, d["_B"] * 1e3, d["alpha.metal"], levels=[0.5], colors="k", linewidths=0.8)
    axs[2].set_title("temperature in the metal [K] (white: 1730 K ~ Invar liquidus, black: surface)", fontsize=9)
    plt.colorbar(im, ax=axs[2], fraction=0.02)
    axs[2].set_xlabel("x [mm] (lab frame; laser/wire at 0, track moves to +x)")
    for a in axs:
        a.set_ylabel("z [mm]")
    fig.tight_layout(); fig.savefig(fname, dpi=130); plt.close(fig)


def domain_cross_sections(mesh, prm, fname, t, xs):
    hw = prm["half_width"]
    fig, axs = plt.subplots(len(xs), 1, figsize=(8, 2.3 * len(xs)))
    for a, x in zip(np.atleast_1d(axs), xs):
        d = sample_plane(mesh, "x", x, (-hw, hw), (-1.2e-3, 2.2e-3), 20e-6)
        draw_comp(a, d, [-hw * 1e3, hw * 1e3, -1.2, 2.2], f"x = {x*1e3:.2f} mm (lab), t = {t*1e3:.0f} ms",
                  d["T"], 1730.0)
        a.set_ylabel("z [mm]")
    np.atleast_1d(axs)[-1].set_xlabel("y [mm]")
    np.atleast_1d(axs)[0].legend(handles=legend_handles(), fontsize=6, loc="upper right", ncol=3)
    fig.tight_layout(); fig.savefig(fname, dpi=130); plt.close(fig)


def wire_closeup(mesh, prm, fname, t):
    pm = point_mesh(mesh)
    R = prm["wire_radius_model"]
    box = pm.clip_box([-1.2e-3, 1.2e-3, -1.2e-3, 1.2e-3, 0.0, prm["gas_height"]], invert=False)
    fig = plt.figure(figsize=(15, 6))
    surf = box.contour([0.5], scalars="alpha.metal") if box.n_points else None
    if surf is not None and surf.n_points:
        rgb = rgb_from(np.ones(surf.n_points), surf.point_data["cFe"], surf.point_data["cNi"])
        surf.point_data["rgb"] = (rgb * 255).astype(np.uint8)
        pl = pv.Plotter(off_screen=True, window_size=(700, 900))
        pl.set_background("white")
        pl.add_mesh(surf, scalars="rgb", rgb=True, smooth_shading=True)
        pl.camera_position = [(-4e-3, -5e-3, 2.5e-3), (0, 0, 1.0e-3), (0, 0, 1)]
        img = pl.screenshot(None, return_img=True); pl.close()
        ax = fig.add_axes([0.0, 0.0, 0.3, 1.0]); ax.imshow(img); ax.axis("off")
        ax.set_title(f"strands, t = {t*1e3:.0f} ms (red Fe, blue Ni)", fontsize=10)
    hs = [2.3e-3, 1.9e-3, 1.5e-3, 1.1e-3, 0.7e-3]
    for i, z in enumerate(hs):
        d = sample_plane(mesh, "z", z, (-0.7e-3, 0.7e-3), (-0.7e-3, 0.7e-3), 10e-6)
        ax = fig.add_axes([0.31 + i * 0.138, 0.15, 0.13, 0.7])
        draw_comp(ax, d, [-0.7, 0.7, -0.7, 0.7], f"z = {z*1e3:.1f} mm", d["T"], 1730.0)
        ax.set_xlabel("x [mm]")
        if i == 0:
            ax.set_ylabel("y [mm]")
    fig.savefig(fname, dpi=130); plt.close(fig)


# ---------------------------------------------------------------------------
def read_record_planes(case, plane):
    """stack the raw cutting-plane samples of one plane: list of (t, dict field -> (pts, values))."""
    base = os.path.join(case, "postProcessing", "recordPlanes")
    out = []
    for td in sorted(glob.glob(os.path.join(base, "*")), key=lambda p: float(os.path.basename(p))
                     if V.is_time(os.path.basename(p)) else -1):
        if not V.is_time(os.path.basename(td)):
            continue
        t = float(os.path.basename(td))
        flds = {}
        for fn in glob.glob(os.path.join(td, f"*{plane}*.raw")) + glob.glob(os.path.join(td, plane, "*.raw")):
            name = os.path.basename(fn)[:-4]
            fld = name.replace(f"_{plane}", "").replace(f"{plane}_", "")
            try:
                arr = np.loadtxt(fn, comments="#")
            except Exception:
                continue
            if arr.ndim == 2 and arr.shape[1] >= 4:
                flds[fld] = arr
        if flds:
            out.append((t, flds))
    return out


def build_volume(case, prm, plane, h=25e-6):
    """reconstruct the build: part coordinate xi = v t - x_plane; returns xi, y, z grids and fields."""
    recs = read_record_planes(case, plane)
    if not recs:
        return None
    v = prm["scan_speed"]
    xp = prm["record_planes_x"][int(plane[1:])]
    hw = prm["half_width"]
    ys = np.arange(-hw, hw + 1e-12, h); zs = np.arange(-1.2e-3, 2.2e-3 + 1e-12, h)
    Y, Z = np.meshgrid(ys, zs)
    q = np.c_[Y.ravel(), Z.ravel()]
    names = ["alpha.metal", "cFe", "cNi", "uFe", "uNi", "T", "meltHistory", "liquidFraction"]
    vol = {k: [] for k in names}
    xis = []
    tree = None
    for t, flds in recs:
        if "alpha.metal" not in flds:
            continue
        pts = flds["alpha.metal"][:, 1:3]
        tree = cKDTree(pts)
        _, idx = tree.query(q)
        for k in names:
            if k in flds:
                vol[k].append(flds[k][idx, 3].reshape(Z.shape))
            else:
                vol[k].append(np.zeros(Z.shape))
        xis.append(v * t - xp)
    xis = np.array(xis)
    keep = xis > 0
    return dict(xi=xis[keep], y=ys, z=zs, **{k: np.array(vol[k])[keep] for k in names}, plane_x=xp)


def build_outputs(bv, prm, outdir, build_xs):
    xi = bv["xi"]; ys, zs = bv["y"], bv["z"]
    alpha = bv["alpha.metal"]
    hw = prm["half_width"]
    res = {}
    # never-melted fractions in the reconstructed (solid) build
    dxi = np.gradient(xi) if len(xi) > 1 else np.ones_like(xi)
    w = dxi[:, None, None]
    for c in ("Fe", "Ni"):
        tot = float(np.sum(alpha * bv["c" + c] * w)); un = float(np.sum(alpha * bv["u" + c] * w))
        res[f"{c}_never_melted_fraction_build"] = un / tot if tot > 0 else 0.0
        res[f"{c}_volume_in_build_mm3"] = tot * (ys[1] - ys[0]) * (zs[1] - zs[0]) * 1e9
    # fragments: connected never-melted Fe (and Ni) regions
    for c in ("Fe", "Ni"):
        mask = (alpha > 0.5) & (bv["u" + c] > 0.5)
        lab, n = ndimage.label(mask)
        sizes = []
        if n:
            dv = np.mean(dxi) * (ys[1] - ys[0]) * (zs[1] - zs[0])
            cnt = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
            sizes = sorted([float((6 * k * dv / math.pi) ** (1 / 3) * 1e3) for k in cnt], reverse=True)
        res[f"{c}_unmelted_fragments"] = n
        res[f"{c}_fragment_equiv_diam_mm_top10"] = sizes[:10]
    # mean build composition above the substrate
    above = (zs > 0)[None, :, None]
    m = alpha * above
    tot = float(m.sum()) or 1.0
    res["build_mean_cFe_above_z0"] = float((m * bv["cFe"]).sum() / tot)
    res["build_mean_cNi_above_z0"] = float((m * bv["cNi"]).sum() / tot)
    res["build_length_reconstructed_mm"] = float(xi.max() * 1e3) if len(xi) else 0.0
    res["recording_plane_x_mm"] = bv["plane_x"] * 1e3
    # cross-sections along the build
    xs = [x for x in build_xs if x <= xi.max()] or [xi.max() / 2]
    fig, axs = plt.subplots(len(xs), 1, figsize=(8, 2.3 * len(xs)))
    for a, x in zip(np.atleast_1d(axs), xs):
        k = int(np.argmin(np.abs(xi - x)))
        Y, Z = np.meshgrid(ys, zs)
        d = {key: bv[key][k] for key in ("alpha.metal", "cFe", "cNi", "uFe", "uNi")}
        d["_A"], d["_B"] = Y, Z
        draw_comp(a, d, [ys[0] * 1e3, ys[-1] * 1e3, zs[0] * 1e3, zs[-1] * 1e3],
                  f"build cross-section at {xi[k]*1e3:.2f} mm from the track start (solid, recorded at "
                  f"x = {bv['plane_x']*1e3:.2f} mm)")
        a.set_ylabel("z [mm]")
    np.atleast_1d(axs)[-1].set_xlabel("y [mm]")
    np.atleast_1d(axs)[0].legend(handles=legend_handles(), fontsize=6, loc="upper right", ncol=3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "build_cross_sections.png"), dpi=140); plt.close(fig)
    # long section at y = 0 and top projection of never-melted wire
    j = int(np.argmin(np.abs(ys)))
    fig, axs = plt.subplots(2, 1, figsize=(12, 6.5))
    Xg, Zg = np.meshgrid(xi, zs)
    d = {key: bv[key][:, :, j].T for key in ("alpha.metal", "cFe", "cNi", "uFe", "uNi")}
    d["_A"], d["_B"] = Xg, Zg
    draw_comp(axs[0], d, [xi[0] * 1e3, xi[-1] * 1e3, zs[0] * 1e3, zs[-1] * 1e3],
              "reconstructed build, long section y = 0 (distance from the track start)")
    axs[0].set_aspect("auto"); axs[0].set_ylabel("z [mm]")
    axs[0].legend(handles=legend_handles(), fontsize=6, loc="upper right", ncol=5)
    unFe = (alpha * bv["uFe"]).sum(axis=1) * (zs[1] - zs[0]) * 1e3   # mm of never-melted Fe through z
    unNi = (alpha * bv["uNi"]).sum(axis=1) * (zs[1] - zs[0]) * 1e3
    img = np.zeros(unFe.shape + (3,)) + 1.0
    img -= np.clip(unFe / 0.3, 0, 1)[..., None] * (1 - np.array([0.85, 0.65, 0.0]))
    img -= np.clip(unNi / 0.3, 0, 1)[..., None] * (1 - np.array([0.0, 0.7, 0.8]))
    axs[1].imshow(np.clip(img.transpose(1, 0, 2), 0, 1), origin="lower", aspect="auto",
                  extent=[xi[0] * 1e3, xi[-1] * 1e3, ys[0] * 1e3, ys[-1] * 1e3])
    axs[1].set_title("top-view projection of never-melted wire (gold Fe, cyan Ni; darker = thicker)", fontsize=9)
    axs[1].set_xlabel("distance along the track [mm]"); axs[1].set_ylabel("y [mm]")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "build_long_section.png"), dpi=140); plt.close(fig)
    return res


def unmelted_timeseries(case, outdir, prm):
    fn = os.path.join(case, "postProcessing", "meltPool", "components.dat")
    if not os.path.isfile(fn):
        return {}
    try:
        d = np.loadtxt(fn)
    except Exception:
        return {}
    if d.ndim == 1 or len(d) < 2:
        return {}
    t = d[:, 0]
    names = prm.get("components") or ["Fe", "Ni"]
    fig, ax = plt.subplots(figsize=(8, 4))
    out = {}
    for i, c in enumerate(names):
        base = 2 + 6 * i
        Vdep, Udep, Vtr, Utr = d[:, base + 2], d[:, base + 3], d[:, base + 4], d[:, base + 5]
        ax.plot(t, np.where(Vdep > 0, Udep / np.maximum(Vdep, 1e-30), np.nan), label=f"{c}: deposit + pool")
        ax.plot(t, np.where(Vtr > 0, Utr / np.maximum(Vtr, 1e-30), np.nan), "--", label=f"{c}: solid track in domain")
        out[f"{c}_never_melted_fraction_domain_track_last"] = float(Utr[-1] / Vtr[-1]) if Vtr[-1] > 0 else 0.0
        out[f"{c}_never_melted_fraction_deposit_last"] = float(Udep[-1] / Vdep[-1]) if Vdep[-1] > 0 else 0.0
    ax.set_xlabel("t [s]"); ax.set_ylabel("never-melted fraction of the wire metal")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "unmelted_timeseries.png"), dpi=120); plt.close(fig)
    return out


def frame(mesh, prm, t, fname, tmpdir):
    f3 = os.path.join(tmpdir, "_3d.png"); fl = os.path.join(tmpdir, "_long.png")
    if not render_3d_comp(mesh, prm, f3, t):
        return
    long_section(mesh, prm, fl, t)
    a = plt.imread(f3); b = plt.imread(fl)
    fig = plt.figure(figsize=(14, 13))
    ax1 = fig.add_axes([0, 0.55, 1, 0.45]); ax1.imshow(a); ax1.axis("off")
    ax2 = fig.add_axes([0, 0, 1, 0.55]); ax2.imshow(b); ax2.axis("off")
    fig.savefig(fname, dpi=80); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only-latest", action="store_true")
    ap.add_argument("--frames-every", type=int, default=1)
    ap.add_argument("--build-xs", default=None, help="mm along the build, e.g. 0.5,1,2,3,4")
    ap.add_argument("--plane", default=None, help="recording plane (x0..x3); default: first behind the pool tail")
    a = ap.parse_args()
    case = os.path.abspath(a.case)
    out = a.out or os.path.join(case, "viz_multicomp")
    os.makedirs(out, exist_ok=True)
    prm = V.load_params(case)
    rd = V.Reader(case)
    if not rd.times:
        print("no time directories"); return 1
    tl = rd.times[-1]
    mesh = rd.read(tl)
    summary = dict(case=os.path.basename(case), latest_time=tl)
    render_3d_comp(mesh, prm, os.path.join(out, "latest_3d_composition.png"), tl)
    try:
        V.render_3d(mesh, prm, os.path.join(out, "latest_3d_T.png"), tl)
    except Exception as e:
        print("render_3d T:", e)
    render_top_comp(mesh, prm, os.path.join(out, "latest_top_composition.png"), tl)
    long_section(mesh, prm, os.path.join(out, "latest_section_long.png"), tl)
    domain_cross_sections(mesh, prm, os.path.join(out, "domain_cross_sections.png"), tl,
                          [0.0, 1.0e-3, 2.0e-3, 3.0e-3, 4.5e-3])
    wire_closeup(mesh, prm, os.path.join(out, "wire_closeup_composition.png"), tl)
    summary.update(unmelted_timeseries(case, out, prm))
    # recording-plane build reconstruction
    planes = [f"x{i}" for i in range(len(prm.get("record_planes_x") or []))]
    if planes:
        plane = a.plane
        if plane is None:
            tail = 0.0
            fn = os.path.join(case, "postProcessing", "meltPool", "meltPool.dat")
            if os.path.isfile(fn):
                try:
                    d = np.loadtxt(fn)
                    if d.ndim == 2 and len(d) > 5:
                        tail = float(np.percentile(d[len(d) // 5:, 21], 95))
                except Exception:
                    pass
            plane = planes[-1]
            for i, x in enumerate(prm["record_planes_x"]):
                if x > tail + 0.4e-3:
                    plane = f"x{i}"; break
            summary["pool_tail_x95_mm"] = tail * 1e3
        bv = build_volume(case, prm, plane)
        if (bv is None or len(bv["xi"]) <= 1) and a.plane is None:
            # fallback: the chosen plane was never passed by the laser; use the plane with the longest record
            best = None
            for pl in planes:
                b2 = build_volume(case, prm, pl)
                if b2 is not None and len(b2["xi"]) > 1 and (best is None or b2["xi"].max() > best["xi"].max()):
                    best = b2
            if best is not None:
                bv = best
        if bv is not None and len(bv["xi"]) > 1:
            bxs = [float(v) * 1e-3 for v in a.build_xs.split(",")] if a.build_xs else \
                list(np.linspace(0.1, 1.0, 6) * bv["xi"].max())
            summary.update(build_outputs(bv, prm, out, bxs))
    if not a.only_latest:
        fd = os.path.join(out, "frames"); os.makedirs(fd, exist_ok=True)
        for i, t in enumerate(rd.times[::a.frames_every]):
            fn = os.path.join(fd, f"frame_{i:04d}.png")
            if os.path.isfile(fn):
                continue
            try:
                frame(rd.read(t), prm, t, fn, out)
            except Exception as e:
                print("frame", t, e)
        frames = sorted(glob.glob(os.path.join(fd, "frame_*.png")))
        if len(frames) > 1:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "6", "-i",
                            os.path.join(fd, "frame_%04d.png"), "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                            "-pix_fmt", "yuv420p", os.path.join(out, "animation.mp4")])
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(out, "animation.mp4"),
                            "-vf", "fps=6,scale=800:-1", os.path.join(out, "animation.gif")])
    for k in ("_3d.png", "_long.png"):
        p = os.path.join(out, k)
        if os.path.isfile(p):
            os.remove(p)
    json.dump(summary, open(os.path.join(out, "summary_multicomp.json"), "w"), indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
