#!/usr/bin/env python3
"""Status of a long single-track run (default: track10mm_fe_ni), plain python3 (no numpy).

  sim time, speed, ETA (CT); pool size; bead height/width/area at the probe (behind the pool) vs the
  steady mass-balance target A* = A_metal*WFS/v and the experiment; metal-volume balance (fed vs gained
  vs carried out through the outlet); wire-tracer accounting (tracer-tracked wire volume vs fed; where
  the wire metal is: undeposited wire / deposit+pool / solid track; never-melted fractions).

Usage: python3 status_track10mm.py [caseName|/abs/case/path]
"""
import sys, os, json, time, datetime, glob, subprocess

name = sys.argv[1] if len(sys.argv) > 1 else "track10mm_fe_ni"
C = name if name.startswith("/") else os.path.expanduser(f"~/laser_wire_ded_stranded/{name}")
L = os.path.join(C, "log.laserWireDEDFoam")
EXP = dict(pool_L=(3.33, 0.18), H_xray=(1.32, 0.20), H_eds=(0.94, 0.10), W_assumed=2.6, unmelted_Fe=(0.05, 0.12))

def ctl(key):
    try:
        for line in open(os.path.join(C, "system", "controlDict")):
            if line.split() and line.split()[0] == key:
                return float(line.split()[1].rstrip(";"))
    except Exception:
        pass
    return float("nan")

def read_table(fn):
    """rows as dicts; a new '# time' header starts a new segment (solver restart)."""
    segs, hdr = [], None
    try:
        with open(fn) as fh:
            for line in fh:
                if line.startswith("#"):
                    toks = line.lstrip("#").split()
                    if toks and toks[0].startswith("time"):
                        hdr = [t.split("[")[0] for t in toks]
                        segs.append([])
                    continue
                if hdr and line.strip():
                    v = line.split()
                    if len(v) == len(hdr):
                        if not segs:
                            segs.append([])
                        segs[-1].append(dict(zip(hdr, map(float, v))))
    except FileNotFoundError:
        pass
    return [s for s in segs if s]

P = {}
try:
    P = json.load(open(os.path.join(C, "case_params.json")))
except Exception:
    pass
A_m = (P.get("strands") or {}).get("area", 3.5343e-7)
wfs = P.get("wire_feed_speed", 0.01818); v = P.get("scan_speed", 0.002667)
feed = A_m * wfs                        # m3/s
A_star = feed / v
end = ctl("endTime")
print(f"case {C}")
nproc = 0
try:
    nproc = int(subprocess.run(["pgrep", "-c", "-f", "laserWireDEDFoam -parallel"], capture_output=True, text=True).stdout.strip() or 0)
except Exception:
    pass
# --- progress / ETA
ts, es = [], []
t = None
try:
    with open(L, errors="ignore") as fh:
        for line in fh:
            if line.startswith("Time = "):
                t = float(line.split()[2])
            elif line.startswith("ExecutionTime") and t is not None:
                ts.append(t); es.append(float(line.split()[2]))
except FileNotFoundError:
    print("  (no solver log yet)")
for s in open(os.path.join(C, "run.status")).read().splitlines()[-3:] if os.path.exists(os.path.join(C, "run.status")) else []:
    print("  status:", s)
if ts:
    t1, e1 = ts[-1], es[-1]
    # restarts reset ExecutionTime: use the last monotonic segment
    k = len(es) - 1
    while k > 0 and es[k - 1] <= es[k]:
        k -= 1
    j = max(k, next((i for i in range(k, len(es)) if es[i] >= es[-1] - 3600), k))   # last ~1 h of wall
    rr = (e1 - es[j]) / max(t1 - ts[j], 1e-12) if t1 > ts[j] else float("nan")
    age = time.time() - os.path.getmtime(L)
    rem = (end - t1) * rr
    eta = datetime.datetime.now() + datetime.timedelta(seconds=max(rem - age, 0))
    print(f"  sim t = {t1:.4f} / {end:g} s ({100*t1/end:.1f} %)   solver processes {nproc}   log updated {age:.0f} s ago")
    print(f"  speed {rr/3600:.2f} h wall per sim-s (last hour)  ->  remaining ~{rem/3600:.1f} h, ETA {eta:%a %b %d %I:%M %p} CT"
          f"   (track so far {t1*v*1e3:.2f} mm of 10)")
    if nproc == 0 and t1 < end - 1e-3:
        print("  WARNING: no solver process running and the end time is not reached (stopped? restart with Track10mm_Start.bat)")
# --- melt pool / bead
mp = read_table(os.path.join(C, "postProcessing", "meltPool", "meltPool.dat"))
rows = [r for s in mp for r in s]
if rows:
    last = rows[-1]
    tl = last["time"]
    win = [r for r in rows if r["time"] >= tl - 0.25]
    avg = lambda k: sum(r[k] for r in win) / len(win)
    print(f"  pool (avg last 0.25 s): length {avg('poolLength')*1e3:.2f} mm (exp {EXP['pool_L'][0]} +- {EXP['pool_L'][1]}),"
          f" width {avg('poolWidth')*1e3:.2f} mm, depth {avg('poolDepth')*1e3:.3f} mm, Tmax {last['Tmax']:.0f} K")
    print(f"  bead at probe x = {last['probeX']*1e3:.2f} mm (avg last 0.25 s): height {avg('beadHeight')*1e3:.2f} mm"
          f" (exp X-ray {EXP['H_xray'][0]} +- {EXP['H_xray'][1]}, EDS {EXP['H_eds'][0]}),"
          f" width {avg('beadWidth')*1e3:.2f} mm (exp ~{EXP['W_assumed']} assumed)")
    ab = avg("beadArea")
    print(f"  bead area {ab*1e6:.2f} mm2 = {100*ab/A_star:.0f} % of the steady mass-balance target A* = {A_star*1e6:.2f} mm2"
          f"  (penetration {avg('penetration')*1e3:.3f} mm, dilution {avg('dilutionComp'):.2f})")
    if tl < 1.6:
        print("  note: the bead is not steady before t ~ 1.5-2 s (pool ~4 mm long + start transient)")
# --- metal + tracer budget
tb = read_table(os.path.join(C, "postProcessing", "meltPool", "tracerBudget.dat"))
if tb:
    comps = [k[2:] for k in tb[0][0] if k.startswith("S_")]
    gain = {c: 0.0 for c in comps}; bnd = {c: 0.0 for c in comps}; err = {c: 0.0 for c in comps}
    mgain = 0.0; outs = {}
    for s in tb:
        r = s[-1]
        for c in comps:
            gain[c] += r[f"S_{c}"] - r[f"S0_{c}"]; bnd[c] += r[f"bnd_{c}"]
            err[c] += r[f"clip_{c}"] + r[f"skip_{c}"] + r[f"norm_{c}"]
        mgain += r["metal"] - r["metal0"]
        for k in r:
            if k.startswith("out_"):
                outs[k[4:]] = outs.get(k[4:], 0.0) + r[k]
    fed = -outs.get("wireInlet", 0.0)
    nominal = feed * max(tl - 0.001, 0) if rows else float("nan")
    wout = sum(outs.values())
    print(f"  METAL balance [mm3]: fed through wireInlet {fed*1e9:.3f} (nominal A_m*WFS*t {nominal*1e9:.3f}),"
          f" domain gain {mgain*1e9:.3f}, net out other patches {(wout+fed)*1e9:+.3f}"
          f" -> residual {(mgain + wout)*1e9:+.4f}")
    bead_out = outs.get("outlet", 0.0) + outs.get("inletSubstrate", 0.0)
    print(f"    deposit carried out through the outlet so far {bead_out*1e9:.3f} mm3 (substrate in/out cancels);"
          f" top/gas loss {outs.get('top', 0.0)*1e9:+.4f} mm3")
    # outlet bead flux over the last 0.25 s of the last segment = steady deposit rate check
    s = tb[-1]
    a0 = next((r for r in s if r["time"] >= s[-1]["time"] - 0.25), s[0])
    dtw = s[-1]["time"] - a0["time"]
    if dtw > 0.05:
        rate = ((s[-1].get("out_outlet", 0) + s[-1].get("out_inletSubstrate", 0)) -
                (a0.get("out_outlet", 0) + a0.get("out_inletSubstrate", 0))) / dtw
        gr = (s[-1]["metal"] - a0["metal"]) / dtw
        print(f"    last {dtw:.2f} s: deposit leaving the outlet {rate*1e9:.2f} mm3/s = {100*rate/feed:.0f} % of the feed"
              f" {feed*1e9:.2f} mm3/s (-> 100 % at steady state), domain gain {gr*1e9:.2f} mm3/s")
    tg = sum(gain.values()); tbnd = sum(bnd.values())
    print(f"  WIRE TRACERS [mm3]: wire tracer gained {tg*1e9:.3f} vs wire metal fed {tbnd*1e9:.3f}"
          f" ({100*tg/max(tbnd,1e-30):.1f} %); clip/skip/normalise error {sum(err.values())*1e9:+.4f}")
cs = read_table(os.path.join(C, "postProcessing", "meltPool", "components.dat"))
crow = [r for s in cs for r in s]
if crow:
    r = crow[-1]
    comps = sorted({k[1:].split("_")[0] for k in r if k.startswith("V") and k.endswith("_wire")})
    parts = []
    for c in comps:
        vw, vd, vt = r[f"V{c}_wire"], r[f"V{c}_dep"], r[f"V{c}_track"]
        ud, ut = r[f"U{c}_dep"], r[f"U{c}_track"]
        parts.append(f"{c}: wire {vw*1e9:.2f} | deposit+pool {vd*1e9:.2f} (never melted {100*ud/max(vd,1e-30):.1f} %)"
                     f" | solid track {vt*1e9:.2f} (never melted {100*ut/max(vt,1e-30):.1f} %)")
    print("  wire metal by region [mm3]: " + ";  ".join(parts))
    print(f"    (exp: unmelted Fe {EXP['unmelted_Fe'][0]*100:.0f}-{EXP['unmelted_Fe'][1]*100:.0f} % of the bead area, d ~0.19 mm, along the whole track)")
print("  renders after the run: C:\\Users\\dukyo\\laser_wire_ded\\viz\\" + os.path.basename(C.rstrip('/')) + "\\")
