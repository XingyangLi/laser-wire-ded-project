#!/usr/bin/env python3
"""Experiment comparison for the 10 mm validation track (track10mm_fe_ni).

Reads meltPool.dat / components.dat / tracerBudget.dat of the case and the renders of visualize_multicomp.py,
writes <viz>/comparison/track10mm_vs_experiment.png and track10mm_metrics.json/.md:
  X-ray: pool length, bead height (steady window t >= --steady, default 2.0 s)
  EDS:   bead height, penetration, unmelted Fe (fraction, fragment size, along-track distribution)
  mass:  bead area vs the steady target A* = A_metal*WFS/v, metal balance, wire-tracer balance
Usage: ~/vizenv/bin/python compare_track10mm.py --case <case> --viz <vizdir> --validation <repo>/validation
"""
import os, sys, json, argparse
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread

ap = argparse.ArgumentParser()
ap.add_argument("--case", required=True); ap.add_argument("--viz", required=True)
ap.add_argument("--validation", required=True); ap.add_argument("--steady", type=float, default=2.0)
a = ap.parse_args()
C, VZ, VA = a.case, a.viz, a.validation
P = json.load(open(os.path.join(C, "case_params.json")))
A_m = P["strands"]["area"]; wfs = P["wire_feed_speed"]; v = P["scan_speed"]
A_star = A_m * wfs / v

def table(fn):
    hdr, rows = None, []
    for line in open(fn):
        if line.startswith("#"):
            t = line.lstrip("#").split()
            if t and t[0].startswith("time"):
                hdr = [x.split("[")[0] for x in t]
            continue
        if hdr and line.strip() and len(line.split()) == len(hdr):
            rows.append(dict(zip(hdr, map(float, line.split()))))
    return rows

mp = table(os.path.join(C, "postProcessing", "meltPool", "meltPool.dat"))
tend = mp[-1]["time"]
ts = min(a.steady, 0.6 * tend)
st = [r for r in mp if r["time"] >= ts]
m = lambda k, f=1e3: (float(np.mean([r[k] for r in st])) * f, float(np.std([r[k] for r in st])) * f)
M = dict(steady_window_s=[ts, tend], pool_L_mm=m("poolLength"), pool_W_mm=m("poolWidth"),
         pool_D_mm=m("poolDepth"), bead_H_mm=m("beadHeight"), bead_W_mm=m("beadWidth"),
         bead_area_mm2=m("beadArea", 1e6), penetration_mm=m("penetration"),
         dilution=m("dilutionComp", 1.0), A_star_mm2=A_star * 1e6)
try:
    cr = table(os.path.join(C, "postProcessing", "meltPool", "components.dat"))[-1]
    vt = cr["VFe_track"] + cr["VNi_track"]
    M["never_melted_Fe_of_track_wire_metal"] = cr["UFe_track"] / vt if vt > 0 else float("nan")
    M["never_melted_Ni_of_track_wire_metal"] = cr["UNi_track"] / vt if vt > 0 else float("nan")
except Exception as e:
    print("components:", e)
try:
    tb = table(os.path.join(C, "postProcessing", "meltPool", "tracerBudget.dat"))
    r = tb[-1]
    fed_w = r["bnd_Fe"] + r["bnd_Ni"]; gain_w = r["S_Fe"] - r["S0_Fe"] + r["S_Ni"] - r["S0_Ni"]
    M["wire_tracer_gain_over_fed_last_segment"] = gain_w / fed_w if fed_w > 0 else float("nan")
    M["metal_fed_mm3_last_segment"] = -r.get("out_wireInlet", 0) * 1e9
except Exception as e:
    print("tracerBudget:", e)
try:
    sm = json.load(open(os.path.join(VZ, "summary_multicomp.json")))
    M["build_Fe_never_melted_fraction_of_Fe"] = sm.get("Fe_never_melted_fraction_build")
    M["build_Fe_fragments"] = sm.get("Fe_unmelted_fragments")
    M["build_Fe_fragment_d_mm_top10"] = sm.get("Fe_fragment_equiv_diam_mm_top10")
    M["build_length_mm"] = sm.get("build_length_reconstructed_mm")
except Exception as e:
    print("summary_multicomp:", e)
X = json.load(open(os.path.join(VA, "xray_measurements.json")))
E = json.load(open(os.path.join(VA, "eds_measurements.json")))
od = os.path.join(VZ, "comparison"); os.makedirs(od, exist_ok=True)
json.dump(M, open(os.path.join(od, "track10mm_metrics.json"), "w"), indent=2)

def pm(x): return f"{x[0]:.2f} ± {x[1]:.2f}"
def verdict(sim, lo, hi): return "match" if lo <= sim <= hi else ("too high" if sim > hi else "too low")
frag = M.get("build_Fe_fragment_d_mm_top10") or []
rows = [("metric", "Experiment", f"Sim track10mm_fe_ni (t {ts:.1f}-{tend:.2f} s)", "verdict"),
        ("pool length [mm]", f"{X['pool_L_mm']} ± {X['pool_L_mm_std']:.2f} (X-ray)", pm(M["pool_L_mm"]),
         verdict(M["pool_L_mm"][0], X["pool_L_mm"] - 2 * X["pool_L_mm_std"], X["pool_L_mm"] + 2 * X["pool_L_mm_std"])),
        ("bead height [mm]", f"{X['H_bead_mm']} ± {X['H_bead_mm_std']:.2f} (X-ray); {E['H_bead_mm_eds']} (EDS)", pm(M["bead_H_mm"]),
         verdict(M["bead_H_mm"][0], E["H_bead_mm_eds"] - 0.1, X["H_bead_mm"] + X["H_bead_mm_std"])),
        ("bead width [mm]", "~2.6 (assumed in the volume match)", pm(M["bead_W_mm"]), "-"),
        ("bead area [mm²]", f"~2.3-2.4 (H x W); A* = {A_star*1e6:.2f} mass balance", pm(M["bead_area_mm2"]),
         verdict(M["bead_area_mm2"][0], 0.9 * A_star * 1e6, 1.1 * A_star * 1e6)),
        ("penetration [mm]", f"{X['pen_mm']:.2f} (X-ray auto); EDS ~0; guide 0.25-0.45", pm(M["penetration_mm"]), "-"),
        ("unmelted Fe", f"{100*E['unmelted_fraction']:.1f} % (5-12 %) of the section; d ~{E['unmelted_d_eq_um_median']/1e3:.2f} mm",
         f"{100*M.get('never_melted_Fe_of_track_wire_metal', float('nan')):.1f} % of track wire metal; "
         f"{M.get('build_Fe_fragments')} pieces, d {', '.join(f'{d:.2f}' for d in frag[:4])} mm", "-"),
        ("wire tracer kept", "-", f"{100*M.get('wire_tracer_gain_over_fed_last_segment', float('nan')):.1f} % of the fed wire metal", "-")]
with open(os.path.join(od, "track10mm_metrics.md"), "w") as fh:
    fh.write("| " + " | ".join(rows[0]) + " |\n|" + "---|" * 4 + "\n")
    for r in rows[1:]:
        fh.write("| " + " | ".join(r) + " |\n")
plt.rcParams.update({"text.color": "#ddd", "axes.edgecolor": "#555"})
fig = plt.figure(figsize=(16, 13), facecolor="#16161a")
fig.suptitle("10 mm validation: experiment vs 'track10mm_fe_ni' (600 W, 2.67 mm/s, WFS 18.2 mm/s metal, focus -1.5 mm, "
             "A_wire 0.25 / A_sub 0.35, conservative tracers)", color="#f5c542", fontsize=12.5, x=0.01, ha="left", y=0.985)
gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 0.85], hspace=0.12, wspace=0.04, left=0.01, right=0.99, top=0.95, bottom=0.01)
panels = [(os.path.join(VA, "annotated", "annot2_f_0021.png"), "Exp X-ray (steady frame)"),
          (os.path.join(VZ, "latest_section_long.png"), f"Sim long section at t = {tend:.2f} s"),
          (os.path.join(VA, "annotated", "eds_measured.png") if os.path.isfile(os.path.join(VA, "annotated", "eds_measured.png")) else os.path.join(VA, "eds_cross_section.png"), "Exp EDS section (unmelted Fe marked)"),
          (os.path.join(VZ, "build_long_section.png"), "Sim reconstructed build (recording plane) + never-melted wire")]
for i, (f, t) in enumerate(panels):
    ax = fig.add_subplot(gs[i // 2, i % 2]); ax.set_xticks([]); ax.set_yticks([]); ax.set_facecolor("#16161a")
    if os.path.isfile(f):
        ax.imshow(imread(f))
    else:
        ax.text(0.5, 0.5, f"(missing {os.path.basename(f)})", ha="center", color="#888")
    ax.set_title(t, fontsize=9.5, color="#ddd", loc="left")
ax = fig.add_subplot(gs[2, :]); ax.axis("off")
tab = ax.table(cellText=rows, loc="upper left", cellLoc="left", colWidths=[0.14, 0.33, 0.37, 0.12])
tab.auto_set_font_size(False); tab.set_fontsize(10); tab.scale(1, 1.6)
for (r, c), cell in tab.get_celld().items():
    cell.set_edgecolor("#333"); cell.set_facecolor("#1e1e24" if r else "#2a2a33")
    txt = rows[r][c]
    cell.get_text().set_color("#f5c542" if r == 0 else ("#9fe39f" if c == 3 and txt == "match" else ("#ff9f80" if c == 3 and txt.startswith("too") else "#ddd")))
out = os.path.join(od, "track10mm_vs_experiment.png")
fig.savefig(out, dpi=110, facecolor=fig.get_facecolor()); print(out)
print(json.dumps(M, indent=2))
