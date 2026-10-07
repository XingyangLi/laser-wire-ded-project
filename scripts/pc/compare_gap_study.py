#!/usr/bin/env python3
"""Side-by-side comparison of the wire-substrate gap study (gap_study_1mm/2mm/3mm, + baseline v2 if present).

    ~/vizenv/bin/python scripts/pc/compare_gap_study.py                     # defaults below
    ~/vizenv/bin/python scripts/pc/compare_gap_study.py --gaps "1 2 3" --out /mnt/c/.../viz/gap_study_compare

Reads per case: postProcessing/wireTransfer/wireTransfer.dat (stubbing / transfer diagnostics),
postProcessing/meltPool/meltPool.dat, postProcessing/meltPool/components.dat and, if rendered,
<viz>/gap_study_<n>mm/standard/track_profile.csv. Works on unfinished runs (uses what exists).
Writes gap_study_compare.png, gap_study_table.csv/.md and gap_study_summary.json into --out.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HOME = os.path.expanduser("~")


def read_dat(fn):
    """whitespace table with a '# name[unit] ...' header -> dict of arrays (time-sorted, restart duplicates removed)."""
    if not os.path.isfile(fn):
        return None
    hdr, rows = None, []
    with open(fn, errors="ignore") as fh:
        for line in fh:
            if line.startswith("#"):
                hdr = [h.split("[")[0] for h in line[1:].split()]
                continue
            p = line.split()
            if hdr and len(p) == len(hdr):
                try:
                    rows.append([float(x) for x in p])
                except ValueError:
                    pass
    if not rows:
        return None
    a = np.array(rows)
    # keep the last occurrence of each time (a restart re-writes the tail), sorted by time
    t = a[:, 0]
    _, idx = np.unique(t[::-1], return_index=True)
    a = a[::-1][idx]
    return {h: a[:, i] for i, h in enumerate(hdr)}


def read_profile(fn):
    if not os.path.isfile(fn):
        return None, None
    cl, xs, cur = [], [], None
    for line in open(fn):
        if line.startswith("# centreline"):
            cur = cl; continue
        if line.startswith("# cross-section"):
            cur = xs; continue
        if line.startswith("#") or not line.strip():
            continue
        cur.append([float(v) for v in line.split(",")])
    return (np.array(cl) if cl else None), (np.array(xs) if xs else None)


def droplet_events(w, vmin=1e-11, drop=0.4, sep=2e-3):
    """detachment/transfer events: hanging liquid volume falls by > drop (fraction) between two samples
    while the wire was not bridged before the fall (a ball that left the tip and landed)."""
    if w is None or "ballVolume" not in w:
        return []
    t, v, b = w["time"], w["ballVolume"], w.get("bridged", np.zeros_like(w["time"]))
    ev, last = [], -1.0
    for i in range(1, len(t)):
        if v[i - 1] > vmin and v[i] < (1 - drop) * v[i - 1] and b[i - 1] < 0.5 and t[i] - last > sep:
            ev.append(float(t[i])); last = t[i]
    return ev


def first(t, mask):
    i = np.argmax(mask) if np.any(mask) else None
    return float(t[i]) if i is not None else None


def summarize(name, gap, w, mp, cm, prm):
    s = dict(case=name, gap_mm=gap, cells=prm.get("cells"), t_last=None)
    if mp is not None:
        t = mp["time"]
        s["t_last"] = float(t[-1])
        late = t > max(0.3, 0.5 * t[-1])
        bh, bw = mp["beadHeight"] * 1e3, mp["beadWidth"] * 1e3
        s["bead_h_mean_mm"] = float(np.mean(bh[late])) if late.any() else None
        s["bead_h_std_mm"] = float(np.std(bh[late])) if late.any() else None
        s["bead_w_mean_mm"] = float(np.mean(bw[late])) if late.any() else None
        s["bead_continuity"] = float(np.mean(bh[late] > 0.05)) if late.any() else None
        s["penetration_max_mm"] = float(np.max(mp["penetration"]) * 1e3)
        s["pool_len_last_mm"] = float(mp["poolLength"][-1] * 1e3)
        s["metal_added_mm3"] = float((mp["metalVolume"][-1] - mp["metalVolume"][0]) * 1e9)
        s["tmax_K_max"] = float(np.max(mp["Tmax"]))
    if cm is not None:
        for c in ("Fe", "Ni"):
            V, U = cm.get(f"V{c}_dep"), cm.get(f"U{c}_dep")
            Vt, Ut = cm.get(f"V{c}_track"), cm.get(f"U{c}_track")
            if V is not None and V[-1] > 0:
                s[f"unmelted_{c}_deposit"] = float(U[-1] / V[-1])
            if Vt is not None and Vt[-1] > 0:
                s[f"unmelted_{c}_track"] = float(Ut[-1] / Vt[-1])
    if w is not None:
        t = w["time"]
        s["first_stub_s"] = float(w["firstStubTime"][-1]) if w["firstStubTime"][-1] >= 0 else None
        s["stub_events"] = int(w["nStubEvents"][-1])
        s["stub_contact_time_s"] = float(w["contactTime"][-1])
        s["stalled_volume_mm3"] = float(w["stalledVolume"][-1] * 1e9)
        s["stalled_length_mm"] = float(w["stalledLength"][-1] * 1e3)
        fed = w["fedVolume"][-1] + w["stalledVolume"][-1]
        s["stalled_fraction_of_feed"] = float(w["stalledVolume"][-1] / fed) if fed > 0 else 0.0
        s["first_contact_s"] = first(t, w["bridged"] > 0.5)
        tz = np.where(w["tipZ"] > -0.5, w["tipZ"], np.nan)
        s["tip_z_start_mm"] = float(tz[0] * 1e3) if np.isfinite(tz[0]) else None
        s["tip_z_min_mm"] = float(np.nanmin(tz) * 1e3) if np.isfinite(tz).any() else None
        s["tip_reaches_0.15mm_s"] = first(t, np.nan_to_num(tz, nan=9) < 1.5e-4)
        pre = (t < s["first_contact_s"]) if s["first_contact_s"] else np.ones_like(t, bool)
        s["ball_V_max_mm3"] = float(np.max(w["ballVolume"]) * 1e9)
        s["ball_V_max_before_contact_mm3"] = float(np.max(w["ballVolume"][pre]) * 1e9) if pre.any() else 0.0
        s["ball_d_eq_max_mm"] = float(np.max(w["ballDiamEq"]) * 1e3)
        s["ball_d_eq_max_before_contact_mm"] = float(np.max(w["ballDiamEq"][pre]) * 1e3) if pre.any() else 0.0
        s["ball_width_max_mm"] = float(np.max(np.maximum(w["ballWidthX"], w["ballWidthY"])) * 1e3)
        s["ball_height_max_mm"] = float(np.max(w["ballHeight"]) * 1e3)
        ev = droplet_events(w)
        s["droplet_events"] = len(ev)
        s["droplet_event_times_s"] = ev[:20]
        s["bridged_fraction"] = float(np.mean(w["bridged"] > 0.5))
        s["transfer_mode"] = ("stubbing" if s["stub_contact_time_s"] > 0.05 * (t[-1] - t[0] + 1e-12)
                              else "droplet" if len(ev) >= 2 and s["bridged_fraction"] < 0.5
                              else "bridging" if s["bridged_fraction"] >= 0.5 else "balling/mixed")
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.path.join(HOME, "laser_wire_ded_stranded"))
    ap.add_argument("--gaps", default="1 2 3")
    ap.add_argument("--prefix", default="gap_study_")
    ap.add_argument("--viz", default="/mnt/c/Users/dukyo/laser_wire_ded/viz")
    ap.add_argument("--baseline", default="val3mm_fe_ni_v2", help="baseline case (gap ~0) or '' to skip")
    ap.add_argument("--out", default="/mnt/c/Users/dukyo/laser_wire_ded/viz/gap_study_compare")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    cases = []
    if a.baseline:
        cases.append((a.baseline, 0.0, os.path.join(a.root, a.baseline), os.path.join(a.viz, a.baseline)))
    for g in a.gaps.replace(",", " ").split():
        n = f"{float(g):g}"
        cases.append((f"{a.prefix}{n}mm", float(g), os.path.join(a.root, f"{a.prefix}{n}mm"),
                      os.path.join(a.viz, f"{a.prefix}{n}mm")))

    data, summ = [], []
    for name, gap, c, vz in cases:
        pp = os.path.join(c, "postProcessing")
        w = read_dat(os.path.join(pp, "wireTransfer", "wireTransfer.dat"))
        mp = read_dat(os.path.join(pp, "meltPool", "meltPool.dat"))
        cm = read_dat(os.path.join(pp, "meltPool", "components.dat"))
        try:
            prm = json.load(open(os.path.join(c, "case_params.json")))
        except Exception:
            prm = {}
        cl, xs = read_profile(os.path.join(vz, "standard", "track_profile.csv"))
        if mp is None and w is None:
            print(f"[compare] {name}: no data yet"); continue
        data.append((name, gap, w, mp, cm, prm, cl, xs))
        summ.append(summarize(name, gap, w, mp, cm, prm))
        print(f"[compare] {name}: t_last = {summ[-1]['t_last']}")
    if not data:
        print("[compare] nothing to compare"); return 1

    colors = {0.0: "0.4"}
    cyc = ["tab:blue", "tab:orange", "tab:red", "tab:green", "tab:purple"]
    for i, d in enumerate(x for x in data if x[1] > 0):
        colors[d[1]] = cyc[i % len(cyc)]
    lab = lambda d: (f"gap {d[1]:g} mm" if d[1] > 0 else "baseline v2 (tip on plate)")

    fig, ax = plt.subplots(3, 3, figsize=(18, 13))
    ax = ax.ravel()
    for d in data:
        name, gap, w, mp, cm, prm, cl, xs = d
        col, L = colors[gap], lab(d)
        if w is not None:
            t = w["time"] * 1e3
            tz = np.where(w["tipZ"] > -0.5, w["tipZ"] * 1e3, np.nan)
            hz = np.where(w["hangMinZ"] > -0.5, w["hangMinZ"] * 1e3, np.nan)
            ax[0].plot(t, tz, color=col, label=f"{L}: solid tip")
            ax[0].plot(t, hz, color=col, ls=":", label=f"{L}: lowest hanging metal")
            g_ = np.where(w["gapMin"] > -0.5, w["gapMin"] * 1e3, np.nan)
            ax[1].plot(t, g_, color=col, label=L)
            ax[1].fill_between(t, 0, w["bridged"] * 0.1, color=col, alpha=0.25, step="post")
            ax[2].plot(t, w["ballVolume"] * 1e9, color=col, label=L)
            ax[3].plot(t, w["ballDiamEq"] * 1e3, color=col, label=f"{L}: d_eq")
            ax[3].plot(t, np.maximum(w["ballWidthX"], w["ballWidthY"]) * 1e3, color=col, ls="--", lw=0.8)
            for te in droplet_events(w):
                ax[2].axvline(te * 1e3, color=col, ls=":", lw=0.8)
            ax[4].plot(t, w["stallFactor"], color=col, label=f"{L}: stall factor")
            ax[4].plot(t, w["stalledVolume"] * 1e9, color=col, ls="--", label=f"{L}: stalled feed [mm3]")
        elif mp is not None:
            tz = np.where(mp["wireTipZ"] > -0.5, mp["wireTipZ"] * 1e3, np.nan)
            ax[0].plot(mp["time"] * 1e3, tz, color=col, label=f"{L}: wireTipZ (meltPool)")
        if mp is not None:
            t = mp["time"] * 1e3
            ax[5].plot(t, mp["beadHeight"] * 1e3, color=col, label=f"{L}: height")
            ax[5].plot(t, mp["beadWidth"] * 1e3, color=col, ls="--", lw=0.8, label=f"{L}: width")
            ax[6].plot(t, mp["penetration"] * 1e3, color=col, label=f"{L}: penetration")
            ax[6].plot(t, mp["poolDepth"] * 1e3, color=col, ls=":", lw=0.8)
        if cl is not None:
            ax[7].plot(cl[:, 0] * 1e3, cl[:, 1] * 1e3, color=col, label=L)
        if xs is not None:
            ax[8].plot(xs[:, 0] * 1e3, xs[:, 1] * 1e3, color=col, label=L)
    ttl = ["wire tip height (solid tip; dotted: lowest hanging metal = ball bottom) [mm]",
           "wire-substrate gas gap [mm] (shaded: bridged / in contact)",
           "hanging liquid volume (ball) [mm3]  (dotted lines: droplet transfer events)",
           "ball equivalent diameter (solid) / max width (dashed) [mm]",
           "stubbing: stall factor (1 free, 0 stalled) and stalled feed [mm3]",
           "bead height / width at the bead probe [mm]",
           "penetration (solid) / pool depth (dotted) [mm]",
           "final track centreline surface z(x) [mm]",
           "final bead cross-section z(y) at the probe [mm]"]
    for i, A in enumerate(ax):
        A.set_title(ttl[i], fontsize=9)
        A.grid(alpha=0.3)
        A.set_xlabel("x [mm]" if i == 7 else "y [mm]" if i == 8 else "t [ms]")
        if A.has_data():
            A.legend(fontsize=6.5)
    ax[0].axhline(0, color="k", lw=0.8)
    fig.suptitle("Laser wire DED: initial wire-substrate gap study (600 W, 160 mm/min, WFS 18.2 mm/s, "
                 "Fe/Ni 5-strand on Invar, focus -1.5 mm)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(os.path.join(a.out, "gap_study_compare.png"), dpi=120)
    plt.close(fig)

    keys = ["case", "gap_mm", "cells", "t_last", "transfer_mode", "tip_reaches_0.15mm_s", "first_contact_s",
            "first_stub_s", "stub_events", "stub_contact_time_s", "stalled_volume_mm3", "stalled_fraction_of_feed",
            "ball_V_max_before_contact_mm3", "ball_d_eq_max_before_contact_mm", "ball_d_eq_max_mm",
            "ball_width_max_mm", "ball_height_max_mm", "droplet_events", "bridged_fraction",
            "bead_h_mean_mm", "bead_h_std_mm", "bead_w_mean_mm", "bead_continuity", "penetration_max_mm",
            "metal_added_mm3", "unmelted_Fe_deposit", "unmelted_Ni_deposit", "unmelted_Fe_track",
            "unmelted_Ni_track", "pool_len_last_mm"]

    def fv(v):
        if v is None:
            return "-"
        if isinstance(v, float):
            return f"{v:.4g}"
        return str(v)
    with open(os.path.join(a.out, "gap_study_table.csv"), "w") as fh:
        fh.write(",".join(keys) + "\n")
        for s in summ:
            fh.write(",".join(fv(s.get(k)) for k in keys) + "\n")
    with open(os.path.join(a.out, "gap_study_table.md"), "w") as fh:
        fh.write("| quantity | " + " | ".join(s["case"] for s in summ) + " |\n")
        fh.write("|---|" + "---|" * len(summ) + "\n")
        for k in keys[1:]:
            fh.write(f"| {k} | " + " | ".join(fv(s.get(k)) for s in summ) + " |\n")
        fh.write("\nDefinitions: see cases/gap_study/README.md. bead_* averaged over t > max(0.3 s, t_last/2); "
                 "bead_continuity = fraction of those bead-probe samples with h > 50 um; droplet_events = drops "
                 "of the hanging liquid volume by > 40 % while not bridged; transfer_mode is a rough label.\n")
    json.dump(summ, open(os.path.join(a.out, "gap_study_summary.json"), "w"), indent=2)
    print(open(os.path.join(a.out, "gap_study_table.md")).read())
    print(f"[compare] wrote {a.out}/gap_study_compare.png, gap_study_table.csv/.md, gap_study_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
