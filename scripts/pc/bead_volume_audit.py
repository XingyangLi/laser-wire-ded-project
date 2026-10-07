#!/usr/bin/env python3
"""Bead-volume audit: where does the fed wire metal go?

Usage:  ~/vizenv/bin/python bead_volume_audit.py <case> [t1,t2,...|all|last] [--csv out.csv]

Per written time (reconstructed or decomposed case) it reports [mm3 / mm2]:
  fed      = metal fed through the wireInlet since the first listed time, A_metal * WFS * (t - tFeed - ramp/2)
  dVm      = metal-volume gain since t=0 (sum alpha V)  -> 'does metal track the feed'
  dVsub    = substrate-tracer gain (alpha (1 - sum c_i)); should be ~0 before the bead leaves the outlet
  dVwire   = wire-tracer gain (alpha sum c_i)             -> 'tracer-tracked wire volume'
  above / below plate: metal above z=0 (minus the initial plate) and holes/excess below z=0
  wirecol  = undeposited never-molten wire column (r < 0.6 mm about the wire axis, z > 0.25 mm, u > 0.3)
  dep      = deposit above the plate outside the wire column
  diffuse  = metal held in diffuse cells 0.01 < alpha < 0.5 above the plate (lost by an alpha>0.5 threshold)
  A(x)     = bead cross-section above z=0 per x-slab (alpha-weighted and alpha>0.5), mm2, at a few x stations
  steady target A* = A_metal * WFS / v_scan
"""
import sys, os, json, glob, argparse
import numpy as np
import pyvista as pv

ap = argparse.ArgumentParser()
ap.add_argument("case")
ap.add_argument("times", nargs="?", default="all")
ap.add_argument("--csv", default=None)
ap.add_argument("--stations", default=None, help="comma x [mm] for A(x) (default -1..track end)")
args = ap.parse_args()
case = os.path.abspath(args.case)
P = json.load(open(os.path.join(case, "case_params.json")))
A_m = P["strands"]["area"] if P.get("strands") else np.pi * P["wire_diameter"] ** 2 / 4
wfs = P["wire_feed_speed"]; v = P["scan_speed"]
tfs = P.get("feed_start", 0.0) or 0.0
ramp = 0.002
A_star = A_m * wfs / v
foam = os.path.join(case, "case.foam")
if not os.path.exists(foam):
    open(foam, "a").close()
r = pv.POpenFOAMReader(foam)
dec = os.path.isdir(os.path.join(case, "processor0"))
# prefer reconstructed if it has more times
r.case_type = "reconstructed"
tv_rec = list(r.time_values)
if dec:
    r.case_type = "decomposed"
    tv_dec = list(r.time_values)
    if len(tv_rec) >= len(tv_dec):
        r.case_type = "reconstructed"
r.enable_all_cell_arrays()
tv = [t for t in r.time_values]
if args.times == "all":
    times = tv
elif args.times == "last":
    times = [tv[0], tv[-1]] if tv[0] == 0 else [tv[-1]]
else:
    times = [float(x) for x in args.times.split(",")]
comps = P.get("components") or []

def fed_vol(t):
    s = max(t - tfs, 0.0)
    s_eff = (s * s / (2 * ramp)) if s < ramp else (s - ramp / 2)
    return A_m * wfs * s_eff

base = None
rows = []
print(f"# case {case}\n# A_metal {A_m*1e6:.4f} mm2, WFS {wfs*1e3:.2f} mm/s, v {v*1e3:.3f} mm/s, "
      f"feed {A_m*wfs*1e9:.3f} mm3/s, steady bead A* = {A_star*1e6:.3f} mm2 ({r.case_type})")
for t in times:
    r.set_active_time_value(t)
    m = r.read()["internalMesh"].compute_cell_sizes()
    V = np.asarray(m["Volume"]); C = m.cell_centers().points
    x, y, z = C[:, 0], C[:, 1], C[:, 2]
    a = np.clip(np.asarray(m["alpha.metal"]), 0, 1)
    if comps:
        cW = sum(np.asarray(m["c" + n]) for n in comps)
        uW = sum(np.asarray(m["u" + n]) for n in comps)
    else:
        cW = np.asarray(m["cWire"]) if "cWire" in m.array_names else np.zeros_like(a)
        uW = np.zeros_like(a)
    fl = np.asarray(m["liquidFraction"]) if "liquidFraction" in m.array_names else np.zeros_like(a)
    rr = np.hypot(x, y)
    up = z > 0
    Vm = (a * V).sum()
    Vw = (a * cW * V).sum()
    Vs = (a * (1 - cW) * V).sum()
    Vup = (a * V)[up].sum()
    hole = ((1 - a) * V)[~up].sum()          # gas/voids inside the plate (depression below z=0)
    wcol = up & (rr < 0.6e-3) & (z > 0.25e-3) & (uW > 0.3)
    Vwcol = (a * V)[wcol].sum()
    dep = up & ~wcol
    Vdep = (a * V)[dep].sum()
    Vdiff = (a * V)[up & (a > 0.01) & (a < 0.5)].sum()
    Vthr = V[dep & (a >= 0.5)].sum()
    Vwire_below = (a * cW * V)[~up].sum()
    Vmolten = (a * fl * V)[fl > 0.5].sum()
    # wire tracer partition
    Vw_up = (a * cW * V)[up].sum()
    Vw_wcol = (a * cW * V)[wcol].sum()
    # bead profile above plate per x slab (exclude the wire column)
    xs = np.unique(np.round(x, 7))
    if base is None:
        base = dict(Vm=Vm, Vw=Vw, Vs=Vs, Vup=Vup, hole=hole, Vwcol=Vwcol, Vdep=Vdep, Vthr=Vthr, t=t)
    fed = fed_vol(t) - fed_vol(base["t"])     # fed since the first listed time (restart windows)
    d = lambda k, val: (val - base[k]) * 1e9
    row = dict(t=t, fed=fed * 1e9, dVm=d("Vm", Vm), dVwire=d("Vw", Vw), dVsub=d("Vs", Vs),
               dep_above=d("Vdep", Vdep), dep_thr=d("Vthr", Vthr), wirecol=Vwcol * 1e9,
               dwirecol=d("Vwcol", Vwcol), hole_below=d("hole", hole), wire_below=Vwire_below * 1e9,
               diffuse=Vdiff * 1e9, molten=Vmolten * 1e9, wire_in_wirecol=Vw_wcol * 1e9)
    rows.append(row)
    print(f"t={t:6.3f} fed {row['fed']:6.3f} | dVmetal {row['dVm']:6.3f} ({row['dVm']/max(row['fed'],1e-12)*100:5.1f}%)"
          f" dVwireTracer {row['dVwire']:6.3f} ({row['dVwire']/max(row['fed'],1e-12)*100:5.1f}%) dVsubTracer {row['dVsub']:+6.3f}"
          f" | above-plate deposit {row['dep_above']:6.3f} (alpha>=0.5 cells {row['dep_thr']:6.3f}) wirecol {row['wirecol']:5.3f}"
          f" (d {row['dwirecol']:+.3f}) holes-below-plate {row['hole_below']:+6.3f} wire-below {row['wire_below']:5.3f}"
          f" diffuse {row['diffuse']:5.3f} molten {row['molten']:5.3f}", flush=True)
    if t == times[-1] or len(times) <= 3:
        # bead profile: alpha-weighted area above z=0 in each x slab (wire column excluded), and alpha>=0.5 area
        dxs = np.diff(xs).min() if len(xs) > 1 else 1
        bins = np.arange(x.min(), x.max() + 1e-4, 0.25e-3)
        idx = np.digitize(x, bins)
        print("   x[mm]  A_bead(alpha) A_bead(a>=.5)  A_hole_below  [mm2]   (A* steady = %.3f)" % (A_star * 1e6))
        for i in range(1, len(bins)):
            sel = idx == i
            L = bins[i] - bins[i - 1]
            Ab = (a * V)[sel & dep].sum() / L
            Ab5 = V[sel & dep & (a >= 0.5)].sum() / L
            Ah = ((1 - a) * V)[sel & ~up].sum() / L
            if base is not None:
                pass
            print(f"  {0.5*(bins[i]+bins[i-1])*1e3:6.2f}  {Ab*1e6:8.3f}  {Ab5*1e6:8.3f}  {Ah*1e6:8.3f}")
if args.csv:
    import csv
    with open(args.csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
