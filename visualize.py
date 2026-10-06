#!/usr/bin/env python3
"""
visualize.py - renders for laser wire DED cases (laserWireDEDFoam).

Reads decomposed (processor*) or reconstructed results with PyVista's OpenFOAM
reader. For the 3D half-domain the results are mirrored about y = 0 (full-width
cases, e.g. the stranded wire, are shown as computed).

Outputs (in --out):
  frames/frame_XXXX.png   per written time: 3D free surface (alpha=0.5) coloured by T,
                          liquidus contour, beam; plus longitudinal section (y=0)
  animation.mp4 / .gif    from the frames
  latest_3d.png           3D free surface coloured by T (latest time)
  latest_top.png          top view (T on the free surface, melt pool outline)
  latest_section_long.png longitudinal section y=0: T, metal surface, liquidus, velocity
  latest_cross_section.png  cross-section(s) x = const: bead profile + fusion line
  track_profile.png / track_profile.csv   bead height along the track (y=0) and
                          cross-section profile z(y) at the probe position
  timeseries.png          melt-pool length/width/depth, T_max, powers, bead h/w vs time
  wire_closeup.png        stranded wire: 3D close-up of the wire + horizontal alpha sections
                          (strand pattern at several heights) - also --wire-closeup-times
Usage:
  python visualize.py --case case_lwded --out case_lwded/viz [--only-latest] [--times 0.1,0.2]
Requirements: pyvista vtk matplotlib imageio imageio-ffmpeg numpy
"""
import argparse, json, os, re, glob, math, sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import pyvista as pv

pv.OFF_SCREEN = True


def is_time(s):
    try:
        float(s); return True
    except ValueError:
        return False


def time_dirs(path):
    if not os.path.isdir(path):
        return []
    return sorted((d for d in os.listdir(path) if is_time(d) and float(d) > 0
                   and os.path.isdir(os.path.join(path, d))), key=float)


def load_params(case):
    fn = os.path.join(case, "case_params.json")
    return json.load(open(fn)) if os.path.isfile(fn) else {}


class Reader:
    def __init__(self, case):
        self.case = case
        foam = os.path.join(case, "case.foam")
        if not os.path.isfile(foam):
            open(foam, "w").close()
        rec = time_dirs(case)
        dec = time_dirs(os.path.join(case, "processor0"))
        self.decomposed = len(dec) > len(rec)
        self.times = [float(t) for t in (dec if self.decomposed else rec)]
        self.r = pv.POpenFOAMReader(foam) if self.decomposed else pv.OpenFOAMReader(foam)
        if self.decomposed:
            self.r.case_type = "decomposed"
        self.r.enable_all_cell_arrays() if hasattr(self.r, "enable_all_cell_arrays") else None
        try:
            self.r.disable_all_patch_arrays()
            self.r.enable_patch_array("internalMesh")
        except Exception:
            pass

    def read(self, t):
        self.r.set_active_time_value(t)
        d = self.r.read()
        m = d["internalMesh"] if "internalMesh" in d.keys() else d[0]
        if m.n_points == 0 or "alpha.metal" not in m.point_data:
            m = m.cell_data_to_point_data(pass_cell_data=True)
        return m


def half_domain(prm):
    """True for the 3D half domain (symmetry plane y = 0) -> mirror for display."""
    return prm.get("dim", "3d") == "3d" and not prm.get("full_domain", False)


def mirror(surf, sym):
    if not sym or surf.n_points == 0:
        return surf
    return surf.merge(surf.reflect((0, 1, 0), point=(0, 0, 0)))


# ----------------------------------------------------------------------------
def render_3d(mesh, prm, fname, t, view="iso", size=(1400, 900)):
    sym = half_domain(prm)
    m = prm.get("material_props", {})
    Tliq, Tb = m.get("Tliq", 1723.0), m.get("Tboil", 3090.0)
    surf = mesh.contour([0.5], scalars="alpha.metal")
    if surf.n_points == 0:
        return False
    surf = surf.compute_normals(auto_orient_normals=False) if False else surf
    if "T" not in surf.point_data:
        surf = surf.sample(mesh)
    surf = mirror(surf, sym)
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    pl.add_mesh(surf, scalars="T", cmap="turbo", clim=(300, min(Tb, 3200)),
                scalar_bar_args=dict(title="T [K]", vertical=True, position_x=0.88, position_y=0.15,
                                     height=0.7, color="black", fmt="%.0f"),
                smooth_shading=True, specular=0.3)
    try:
        liq = surf.contour([Tliq], scalars="T")
        if liq.n_points:
            pl.add_mesh(liq, color="cyan", line_width=3, label="liquidus")
    except Exception:
        pass
    # beams (drawn from the focus upwards, length 2 mm)
    if view == "iso":
        for bm in prm.get("beams", []):
            d = np.array(bm["direction"], float); d /= np.linalg.norm(d)
            F = np.array(bm["focus"], float); F[1] = 0.0
            L = 2.0e-3
            c = F - d * L / 2
            cyl = pv.Cylinder(center=c, direction=-d, radius=bm["radius"], height=L, resolution=32)
            pl.add_mesh(cyl, color="limegreen", opacity=0.15)
    b = surf.bounds
    if view == "iso":
        xl0 = prm.get("laser_x", 0.0)
        pl.camera_position = [(xl0 - 7e-3, -9e-3, 7e-3), (xl0 + 1.0e-3, 0, 0), (0, 0, 1)]
        pl.camera.zoom(1.3)
    elif view == "top":
        pl.camera_position = "xy"
        pl.enable_parallel_projection()
        pl.camera.zoom(1.4)
    pl.add_text(f"t = {t*1e3:.1f} ms", position="upper_left", font_size=14, color="black")
    pl.screenshot(fname)
    pl.close()
    return True


def slice_xy(mesh, normal, origin):
    s = mesh.slice(normal=normal, origin=origin)
    return s


def section_long(mesh, prm, ax, t, xlim=None):
    """y = 0 section: T, alpha=0.5 surface, liquidus contour, velocity vectors in liquid."""
    m = prm.get("material_props", {})
    Tliq, Tb = m.get("Tliq", 1723.0), m.get("Tboil", 3090.0)
    yc = 0.5 * prm.get("core_dx", 1e-4) if prm.get("dim") == "2d" else 1e-9
    s = mesh.slice(normal="y", origin=(0, yc, 0))
    if s.n_points == 0:
        return
    s = s.triangulate()
    x, z = s.points[:, 0] * 1e3, s.points[:, 2] * 1e3
    faces = s.faces.reshape(-1, 4)[:, 1:]
    tri = mtri.Triangulation(x, z, faces)
    T = s.point_data["T"]
    a = s.point_data["alpha.metal"]
    Tm = np.where(a > 0.5, T, np.nan)
    cmap = plt.get_cmap("turbo").copy(); cmap.set_bad("0.85")
    trim = mtri.Triangulation(x, z, faces, mask=a[faces].mean(axis=1) < 0.5)
    ax.set_facecolor("0.85")
    cf = ax.tripcolor(trim, np.clip(T, 300, Tb), cmap=cmap, shading="gouraud", vmin=300, vmax=min(Tb, 3200))
    ax.tricontour(tri, a, levels=[0.5], colors="k", linewidths=1.2)
    fl = s.point_data.get("liquidFraction")
    if fl is not None:
        ax.tricontour(tri, a * fl, levels=[0.5], colors="white", linewidths=1.2)
    if "meltHistory" in s.point_data:
        ax.tricontour(tri, s.point_data["meltHistory"] * a, levels=[0.5], colors="magenta",
                      linewidths=1.0, linestyles="--")
    U = s.point_data["U"]
    sel = (a > 0.5) & (fl > 0.5) if fl is not None else a > 0.5
    if sel.sum() > 3:
        idx = np.where(sel)[0]
        if len(idx) > 400:
            idx = idx[:: max(1, len(idx) // 400)]
        ax.quiver(x[idx], z[idx], U[idx, 0] - prm.get("scan_speed", 0), U[idx, 2], color="k",
                  scale=None, width=0.002, alpha=0.8)
    ax.set_aspect("equal")
    if xlim:
        ax.set_xlim(*xlim)
    ax.set_ylim(-1.5, 2.0)
    ax.set_xlabel("x [mm] (substrate moves +x; laser travel direction -x)")
    ax.set_ylabel("z [mm]")
    ax.set_title(f"y = 0 section, t = {t*1e3:.1f} ms  (black: metal surface, white: melt pool (fl=0.5), "
                 "magenta dashed: fusion zone; arrows: melt velocity rel. to substrate)", fontsize=8)
    return cf


def cross_sections(mesh, prm, fname, t, xs):
    m = prm.get("material_props", {})
    Tb = m.get("Tboil", 3090.0)
    if prm.get("dim", "3d") != "3d":
        return None
    sym = half_domain(prm)
    fig, axs = plt.subplots(len(xs), 1, figsize=(7, 2.6 * len(xs)), squeeze=False)
    prof = None
    for ax, xq in zip(axs[:, 0], xs):
        s = mesh.slice(normal="x", origin=(xq, 0, 0))
        if s.n_points == 0:
            continue
        s = s.triangulate()
        y, z = s.points[:, 1], s.points[:, 2]
        faces = s.faces.reshape(-1, 4)[:, 1:]
        if sym:
            Y = np.concatenate([y, -y]) * 1e3
            Z = np.concatenate([z, z]) * 1e3
            F = np.vstack([faces, faces + len(y)])
            dup = lambda v: np.concatenate([v, v])
        else:
            Y, Z, F = y * 1e3, z * 1e3, faces
            dup = lambda v: np.asarray(v)
        tri = mtri.Triangulation(Y, Z, F)
        a = dup(s.point_data["alpha.metal"])
        T = dup(s.point_data["T"])
        cmap = plt.get_cmap("turbo").copy(); cmap.set_bad("0.85")
        ax.set_facecolor("0.85")
        trim = mtri.Triangulation(Y, Z, F, mask=a[F].mean(axis=1) < 0.5)
        ax.tripcolor(trim, np.clip(T, 300, Tb), cmap=cmap, shading="gouraud", vmin=300, vmax=min(Tb, 3200))
        ax.tricontour(tri, a, levels=[0.5], colors="k", linewidths=1.5)
        if "meltHistory" in s.point_data:
            ax.tricontour(tri, dup(s.point_data["meltHistory"]) * a, levels=[0.5], colors="magenta",
                          linewidths=1.2, linestyles="--")
        fl = s.point_data.get("liquidFraction")
        if fl is not None:
            ax.tricontour(tri, a * dup(fl), levels=[0.5], colors="white", linewidths=1.2)
        if "cWire" in s.point_data:
            ax.tricontour(tri, dup(s.point_data["cWire"]) * a, levels=[0.5], colors="cyan",
                          linewidths=1.0, linestyles=":")
        ax.set_aspect("equal"); ax.set_xlim(-3.0, 3.0); ax.set_ylim(-1.2, 1.8)
        ax.set_title(f"cross-section x = {xq*1e3:.1f} mm (t = {t*1e3:.1f} ms): black = surface, "
                     "magenta = fusion line, white = liquid, cyan dotted = 50% wire alloy", fontsize=8)
        ax.set_xlabel("y [mm]"); ax.set_ylabel("z [mm]")
    fig.tight_layout(); fig.savefig(fname, dpi=130); plt.close(fig)


def track_profile(mesh, prm, outdir, t):
    """bead height along the track (y ~ 0) and z(y) at the probe x from zSurface."""
    if "zSurface" not in mesh.cell_data:
        return
    c = mesh.cell_centers().points
    zs = mesh.cell_data["zSurface"]
    dx = prm.get("core_dx", 1e-4)
    ymin = np.abs(c[:, 1]).min()
    sel = np.abs(np.abs(c[:, 1]) - ymin) < 1e-9
    if not half_domain(prm):
        sel &= c[:, 1] > 0
    xs, idx = np.unique(np.round(c[sel, 0], 9), return_index=True)
    hx = zs[sel][idx]
    xp = prm.get("bead_probe_x", 4e-3)
    xcol = np.unique(np.round(c[:, 0], 9))
    xq = xcol[np.argmin(np.abs(xcol - xp))]
    sel2 = np.abs(c[:, 0] - xq) < 1e-9
    ys, idy = np.unique(np.round(c[sel2, 1], 9), return_index=True)
    hy = zs[sel2][idy]
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.5))
    ax[0].plot(xs * 1e3, hx * 1e3, "k-")
    ax[0].axvline(prm.get("laser_x", 0) * 1e3, color="g", ls=":", label="laser axis")
    ax[0].set_xlabel("x [mm]"); ax[0].set_ylabel("surface height z [mm]")
    ax[0].set_title(f"track centreline profile, t = {t*1e3:.1f} ms"); ax[0].legend(); ax[0].grid(alpha=.3)
    if half_domain(prm):
        Y = np.concatenate([-ys[::-1], ys]); H = np.concatenate([hy[::-1], hy])
    else:
        Y, H = ys, hy
    ax[1].plot(Y * 1e3, H * 1e3, "k-")
    ax[1].set_aspect("equal"); ax[1].grid(alpha=.3)
    ax[1].set_xlabel("y [mm]"); ax[1].set_ylabel("z [mm]")
    ax[1].set_title(f"bead cross-section profile at x = {xq*1e3:.2f} mm")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "track_profile.png"), dpi=130); plt.close(fig)
    with open(os.path.join(outdir, "track_profile.csv"), "w") as fh:
        fh.write("# centreline: x[m], z_surface[m]\n")
        for a_, b_ in zip(xs, hx):
            fh.write(f"{a_:.6e},{b_:.6e}\n")
        fh.write(f"# cross-section at x={xq:.6e}: y[m], z_surface[m]\n")
        for a_, b_ in zip(Y, H):
            fh.write(f"{a_:.6e},{b_:.6e}\n")


def render_wire_closeup(mesh, prm, fname, t, heights=None):
    """stranded wire: 3D close-up of the metal surface around the wire and horizontal
    alpha.metal sections (strand pattern) at several heights."""
    st = prm.get("strands") or {}
    R = prm.get("wire_diameter", 0.9e-3) / 2
    org = prm.get("wire_origin", [0, 0, 0])
    zt = prm.get("domain", [[0, 0, 0], [0, 0, 2.5e-3]])[1][2]
    if heights is None:
        heights = [0.25e-3, 0.75e-3, 1.25e-3, 1.75e-3, zt - 0.1e-3]
    hb = R + 0.35e-3
    box = (org[0] - hb, org[0] + hb, org[1] - hb, org[1] + hb, 0.02e-3, zt - 0.06e-3)
    sub = mesh.clip_box(box, invert=False)
    fig = plt.figure(figsize=(16, 8.5))
    ok3d = False
    try:
        surf = sub.contour([0.5], scalars="alpha.metal")
        if surf.n_points:
            if "T" not in surf.point_data:
                surf = surf.sample(mesh)
            pl = pv.Plotter(off_screen=True, window_size=(900, 1000))
            pl.set_background("white")
            # grey (metal colour) below 700 K, turbo above: strands stay visible when cold
            from matplotlib.colors import ListedColormap
            n_lo = int(256 * (700 - 300) / (2500 - 300))
            cols = np.vstack([np.tile([0.72, 0.72, 0.74, 1.0], (n_lo, 1)),
                              plt.get_cmap("turbo")(np.linspace(0, 1, 256 - n_lo))])
            pl.add_mesh(surf, scalars="T", cmap=ListedColormap(cols), clim=(300, 2500), smooth_shading=True,
                        specular=0.5, specular_power=20,
                        scalar_bar_args=dict(title="T [K] (grey < 700 K)", color="black", fmt="%.0f"))
            pl.camera_position = [(org[0] - 4.2e-3, org[1] - 4.8e-3, 3.2e-3), (org[0], org[1], 1.1e-3), (0, 0, 1)]
            pl.add_text(f"t = {t*1e3:.1f} ms", position="upper_left", font_size=12, color="black")
            tmp = fname + ".3d.png"
            pl.screenshot(tmp); pl.close()
            ax = fig.add_axes([0.0, 0.0, 0.42, 0.95])
            ax.imshow(plt.imread(tmp)); ax.axis("off")
            ax.set_title("metal surface (alpha = 0.5) around the wire (grey < 700 K, colour = T)", fontsize=10)
            os.remove(tmp)
            ok3d = True
    except Exception as e:
        print("wire close-up 3D failed:", e)
    n = len(heights)
    ncol = 3
    nrow = int(math.ceil(n / ncol))
    x0 = 0.43 if ok3d else 0.02
    w = (0.98 - x0) / ncol
    hgt = 0.86 / nrow
    th = np.linspace(0, 2 * np.pi, 200)
    for i, zq in enumerate(heights):
        r_, c_ = divmod(i, ncol)
        ax = fig.add_axes([x0 + c_ * w + 0.03, 0.06 + (nrow - 1 - r_) * hgt + 0.04, w - 0.05, hgt - 0.09])
        sl = sub.slice(normal="z", origin=(org[0], org[1], zq))
        if sl.n_points == 0:
            ax.axis("off"); continue
        sl = sl.triangulate()
        xy = sl.points[:, :2] * 1e3
        faces = sl.faces.reshape(-1, 4)[:, 1:]
        a = sl.point_data["alpha.metal"]
        tri = mtri.Triangulation(xy[:, 0], xy[:, 1], faces)
        if "alpha.metal" in sl.cell_data:     # cell values as computed (no smoothing)
            ac = np.asarray(sl.cell_data["alpha.metal"])
            fl = sl.cell_data.get("liquidFraction")
            ax.tripcolor(tri, facecolors=ac, cmap="Greys", vmin=0, vmax=1, edgecolors="none")
            if fl is not None and np.any(np.asarray(fl) * ac > 0.5):
                ax.tricontour(tri, sl.point_data["liquidFraction"] * a, levels=[0.5], colors="orange", linewidths=1.0)
        else:
            ax.tripcolor(tri, a, cmap="Greys", vmin=0, vmax=1, shading="gouraud")
        ax.tricontour(tri, a, levels=[0.5], colors="r", linewidths=0.6)
        ax.plot(org[0] * 1e3 + R * 1e3 * np.cos(th), org[1] * 1e3 + R * 1e3 * np.sin(th), "b--", lw=0.7)
        ax.set_aspect("equal")
        ax.set_xlim((org[0] - R - 0.15e-3) * 1e3, (org[0] + R + 0.15e-3) * 1e3)
        ax.set_ylim((org[1] - R - 0.15e-3) * 1e3, (org[1] + R + 0.15e-3) * 1e3)
        ax.set_title(f"z = {zq*1e3:.2f} mm", fontsize=9)
        ax.tick_params(labelsize=7)
        if c_ == 0:
            ax.set_ylabel("y [mm]", fontsize=8)
        ax.set_xlabel("x [mm]", fontsize=8)
    info = ""
    if st:
        info = (f"{st.get('n_strands')} strands, d = {st.get('strand_diameter', 0)*1e3:.3f} mm, gap "
                f"{st.get('gap', 0)*1e3:.2f} mm, lay {st.get('lay_length', 0)*1e3:.1f} mm "
                f"({st.get('lay_direction')}), dx_min = {prm.get('dx_min', 0)*1e6:.0f} um "
                f"({st.get('cells_per_strand_diameter', 0):.1f} cells/strand)")
    fig.suptitle(f"Wire region, t = {t*1e3:.1f} ms: horizontal sections of the metal fraction "
                 f"(black = metal, red = alpha 0.5, blue dashed = 0.9 mm envelope)\n{info}", fontsize=10)
    fig.savefig(fname, dpi=110); plt.close(fig)
    return True


def timeseries(case, outdir):
    fn = os.path.join(case, "postProcessing", "meltPool", "meltPool.dat")
    if not os.path.isfile(fn):
        return None
    d = np.loadtxt(fn, comments="#", ndmin=2)
    if d.shape[0] < 2:
        return None
    d = d[np.argsort(d[:, 0], kind="stable")]
    t = d[:, 0] * 1e3
    fig, ax = plt.subplots(2, 2, figsize=(12, 7))
    ax[0, 0].plot(t, d[:, 1] * 1e3, label="length"); ax[0, 0].plot(t, d[:, 2] * 1e3, label="width")
    ax[0, 0].plot(t, d[:, 3] * 1e3, label="depth (below substrate top)")
    ax[0, 0].set_ylabel("melt pool [mm]"); ax[0, 0].legend(); ax[0, 0].grid(alpha=.3)
    ax[0, 1].plot(t, d[:, 5], "r"); ax[0, 1].set_ylabel("T_max [K]"); ax[0, 1].grid(alpha=.3)
    ax[1, 0].plot(t, d[:, 8], label="incident"); ax[1, 0].plot(t, d[:, 9], label="absorbed")
    ax[1, 0].plot(t, d[:, 10], label="surface losses"); ax[1, 0].set_ylabel("power [W] (full beam)")
    ax[1, 0].legend(); ax[1, 0].grid(alpha=.3)
    ax[1, 1].plot(t, d[:, 12] * 1e3, label="bead height @probe"); ax[1, 1].plot(t, d[:, 13] * 1e3, label="bead width @probe")
    ax[1, 1].plot(t, d[:, 4] * 1e3, label="pool top z", ls=":")
    if d.shape[1] >= 23:
        ax[1, 1].plot(t, d[:, 18] * 1e3, label="penetration @probe", ls="--")
        ax2 = ax[1, 1].twinx()
        ax2.plot(t, d[:, 19], "k:", label="dilution (geom.)")
        ax2.plot(t, d[:, 20], "m:", label="dilution (composition)")
        ax2.set_ylim(0, 1); ax2.set_ylabel("dilution [-]"); ax2.legend(loc="upper right", fontsize=7)
    ax[1, 1].set_ylabel("[mm]"); ax[1, 1].legend(loc="upper left", fontsize=7); ax[1, 1].grid(alpha=.3)
    for a in ax[1]:
        a.set_xlabel("time [ms]")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "timeseries.png"), dpi=120); plt.close(fig)
    last = d[-1]
    last = [float(v) for v in last]
    out = dict(time=last[0], pool_length_mm=last[1] * 1e3, pool_width_mm=last[2] * 1e3,
               pool_depth_mm=last[3] * 1e3, Tmax=last[5], absorbed_W=last[9],
               bead_height_mm=last[12] * 1e3, bead_width_mm=last[13] * 1e3)
    if d.shape[1] >= 23:
        # averages over the last 20 % of the run (quasi-steady)
        sel = d[:, 0] >= d[-1, 0] - 0.2 * (d[-1, 0] - d[0, 0])
        av = d[sel].mean(axis=0)
        out.update(probe_x_mm=last[15] * 1e3, bead_area_mm2=last[16] * 1e6, fused_area_mm2=last[17] * 1e6,
                   penetration_mm=last[18] * 1e3, dilution_geom=last[19], dilution_comp=last[20],
                   avg_last20pct=dict(pool_length_mm=av[1] * 1e3, pool_width_mm=av[2] * 1e3,
                                      pool_depth_mm=av[3] * 1e3, Tmax=av[5],
                                      bead_height_mm=av[12] * 1e3, bead_width_mm=av[13] * 1e3,
                                      bead_area_mm2=av[16] * 1e6, penetration_mm=av[18] * 1e3,
                                      dilution_geom=av[19], dilution_comp=av[20]))
    return out


def compose_frame(img3d, mesh, prm, t, fname):
    fig = plt.figure(figsize=(14, 9))
    ax1 = fig.add_axes([0.0, 0.36, 1.0, 0.64])
    ax1.imshow(plt.imread(img3d)); ax1.axis("off")
    ax1.set_title("Laser wire DED - free surface (alpha = 0.5) coloured by T, cyan = liquidus, green = laser beam",
                  fontsize=10)
    ax2 = fig.add_axes([0.06, 0.05, 0.84, 0.3])
    x0 = prm.get("domain", [[-4.5e-3]])[0][0] * 1e3
    x1 = prm.get("domain", [[0], [7e-3]])[1][0] * 1e3
    cf = section_long(mesh, prm, ax2, t, xlim=(x0, x1))
    if cf is not None:
        fig.colorbar(cf, ax=ax2, label="T [K]", fraction=0.03, pad=0.01)
    fig.savefig(fname, dpi=100); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only-latest", action="store_true")
    ap.add_argument("--times", default=None, help="comma separated list of times")
    ap.add_argument("--no-3d", action="store_true", help="skip OpenGL renders (matplotlib only)")
    ap.add_argument("--fps", type=int, default=8)
    ap.add_argument("--wire-closeup-times", default=None,
                    help="comma separated times for wire_closeup_<ms>.png (0 = initial field); "
                         "stranded cases always get wire_closeup.png at the latest time")
    ap.add_argument("--wire-closeup-only", action="store_true")
    a = ap.parse_args()
    case = os.path.abspath(a.case)
    out = os.path.abspath(a.out or os.path.join(case, "viz"))
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    prm = load_params(case)
    R = Reader(case)
    if a.wire_closeup_times:
        for tq in [float(v) for v in a.wire_closeup_times.split(",")]:
            if tq <= 0:
                r0 = pv.OpenFOAMReader(os.path.join(case, "case.foam"))
                r0.set_active_time_value(0.0)
                try:
                    r0.disable_all_patch_arrays(); r0.enable_patch_array("internalMesh")
                except Exception:
                    pass
                d0 = r0.read()
                m0 = d0["internalMesh"] if "internalMesh" in d0.keys() else d0[0]
                m0 = m0.cell_data_to_point_data(pass_cell_data=True)
                render_wire_closeup(m0, prm, os.path.join(out, "wire_closeup_0ms.png"), 0.0)
            elif R.times:
                tt = min(R.times, key=lambda x: abs(x - tq))
                render_wire_closeup(R.read(tt), prm, os.path.join(out, f"wire_closeup_{tt*1e3:.0f}ms.png"), tt)
            print(f"[viz] wire close-up t = {tq}", flush=True)
        if a.wire_closeup_only:
            return 0
    if not R.times:
        print("no time directories yet"); return 1
    times = R.times
    if a.times:
        want = [float(v) for v in a.times.split(",")]
        times = [min(R.times, key=lambda x: abs(x - w)) for w in want]
    elif a.only_latest:
        times = [R.times[-1]]
    do3d = not a.no_3d
    frames = []
    for i, t in enumerate(times):
        mesh = R.read(t)
        tmp3d = os.path.join(out, "frames", f"_3d_{i:04d}.png")
        ok = False
        if do3d:
            try:
                ok = render_3d(mesh, prm, tmp3d, t)
            except Exception as e:
                print("3D render failed, continuing with 2D plots only:", e); do3d = False
        fr = os.path.join(out, "frames", f"frame_{R.times.index(t):04d}.png")
        if ok:
            compose_frame(tmp3d, mesh, prm, t, fr)
        else:
            fig, ax = plt.subplots(figsize=(14, 4))
            cf = section_long(mesh, prm, ax, t)
            if cf is not None:
                fig.colorbar(cf, ax=ax, label="T [K]")
            fig.tight_layout(); fig.savefig(fr, dpi=100); plt.close(fig)
        frames.append(fr)
        print(f"[viz] t = {t:.4g} s -> {os.path.basename(fr)}", flush=True)
    # latest-time detailed images
    t = times[-1]
    mesh = R.read(t)
    if do3d:
        try:
            render_3d(mesh, prm, os.path.join(out, "latest_3d.png"), t)
            render_3d(mesh, prm, os.path.join(out, "latest_top.png"), t, view="top", size=(1400, 700))
        except Exception as e:
            print("3D render failed:", e)
    fig, ax = plt.subplots(figsize=(14, 4.5))
    cf = section_long(mesh, prm, ax, t)
    if cf is not None:
        fig.colorbar(cf, ax=ax, label="T [K]")
    fig.tight_layout(); fig.savefig(os.path.join(out, "latest_section_long.png"), dpi=130); plt.close(fig)
    xl = prm.get("laser_x", 0.0)
    xp = prm.get("bead_probe_x", 4e-3)
    try:
        dd = np.loadtxt(os.path.join(case, "postProcessing", "meltPool", "meltPool.dat"), comments="#", ndmin=2)
        dd = dd[np.argsort(dd[:, 0], kind="stable")]
        if dd.shape[1] >= 23 and dd[-1, 15] > xl:
            xp = float(dd[-1, 15])
            prm["bead_probe_x"] = xp
    except Exception:
        pass
    cross_sections(mesh, prm, os.path.join(out, "latest_cross_section.png"), t, [xl, xl + 0.5 * (xp - xl), xp])
    if prm.get("wire_type") == "stranded":
        try:
            render_wire_closeup(mesh, prm, os.path.join(out, "wire_closeup.png"), t)
        except Exception as e:
            print("wire close-up failed:", e)
    track_profile(mesh, prm, out, t)
    summ = timeseries(case, out) or {}
    summ["latest_time"] = t
    json.dump(summ, open(os.path.join(out, "summary.json"), "w"), indent=2)
    print("[viz] summary:", summ)
    # animation
    allf = sorted(glob.glob(os.path.join(out, "frames", "frame_*.png")))
    if len(allf) > 1 and not a.only_latest:
        try:
            import imageio.v2 as imageio
            imgs = [imageio.imread(f_) for f_ in allf]
            h = min(im.shape[0] for im in imgs) // 2 * 2
            w = min(im.shape[1] for im in imgs) // 2 * 2
            imgs = [im[:h, :w, :3] for im in imgs]
            imageio.mimsave(os.path.join(out, "animation.mp4"), imgs, fps=a.fps, macro_block_size=2)
            imageio.mimsave(os.path.join(out, "animation.gif"), [im[::2, ::2] for im in imgs], duration=1.0 / a.fps, loop=0)
            print("[viz] animation written")
        except Exception as e:
            print("animation failed:", e)
    for f_ in glob.glob(os.path.join(out, "frames", "_3d_*.png")):
        os.remove(f_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
