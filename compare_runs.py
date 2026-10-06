#!/usr/bin/env python3
"""
compare_runs.py - side-by-side comparison of two rendered laser wire DED runs
(e.g. Transitional-R with the solid wire vs the 7-strand wire).

    python compare_runs.py --a viz/full_transitional_r --a-label "solid wire" \
        --b viz/full_transitional_r_stranded --b-label "7-strand wire" \
        --times 0.2,0.4,0.6,0.86 --out viz/compare_solid_vs_stranded

Inputs are visualize.py output folders (frames/frame_XXXX.png, summary.json,
latest_cross_section.png, track_profile.png, latest_top.png). Frame i is the
(i+1)-th written time; both runs write every --write-interval (default 0.01 s).
Writes: frames_side_by_side.png, final_side_by_side.png, metrics_table.md/.csv/.png
"""
import argparse, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

METRICS = [  # key, label, scale, fmt
    ("bead_height_mm", "bead height [mm]", 1, "{:.2f}"),
    ("bead_width_mm", "bead width [mm]", 1, "{:.2f}"),
    ("bead_area_mm2", "bead area above plate [mm^2]", 1, "{:.2f}"),
    ("penetration_mm", "penetration [mm]", 1, "{:.2f}"),
    ("dilution_geom", "dilution, geometric [-]", 1, "{:.3f}"),
    ("dilution_comp", "dilution, composition [-]", 1, "{:.3f}"),
    ("pool_length_mm", "melt pool length [mm]", 1, "{:.2f}"),
    ("pool_width_mm", "melt pool width [mm]", 1, "{:.2f}"),
    ("Tmax", "T max [K]", 1, "{:.0f}"),
]


def load(d):
    fn = os.path.join(d, "summary.json")
    return json.load(open(fn)) if os.path.isfile(fn) else {}


def frame(d, t, dt):
    i = int(round(t / dt)) - 1
    fn = os.path.join(d, "frames", f"frame_{i:04d}.png")
    return fn if os.path.isfile(fn) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True); ap.add_argument("--a-label", default="A")
    ap.add_argument("--b", required=True); ap.add_argument("--b-label", default="B")
    ap.add_argument("--times", default="0.2,0.4,0.6,0.86")
    ap.add_argument("--write-interval", type=float, default=0.01)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    times = [float(v) for v in a.times.split(",")]
    pairs = [(t, frame(a.a, t, a.write_interval), frame(a.b, t, a.write_interval)) for t in times]
    pairs = [p for p in pairs if p[1] or p[2]]
    if pairs:
        fig, axs = plt.subplots(len(pairs), 2, figsize=(20, 6.6 * len(pairs)), squeeze=False)
        for r, (t, fa, fb) in enumerate(pairs):
            for c, (fn, lab) in enumerate([(fa, a.a_label), (fb, a.b_label)]):
                ax = axs[r, c]; ax.axis("off")
                if fn:
                    ax.imshow(plt.imread(fn))
                else:
                    ax.text(0.5, 0.5, "not reached yet", ha="center", va="center", fontsize=20)
                ax.set_title(f"{lab}  -  t = {t*1e3:.0f} ms", fontsize=15)
        fig.tight_layout(); fig.savefig(os.path.join(a.out, "frames_side_by_side.png"), dpi=70); plt.close(fig)
    # final images
    imgs = ["latest_3d.png", "latest_cross_section.png", "track_profile.png", "latest_top.png"]
    rows = [im for im in imgs if os.path.isfile(os.path.join(a.a, im)) or os.path.isfile(os.path.join(a.b, im))]
    if rows:
        sa, sb = load(a.a), load(a.b)
        fig, axs = plt.subplots(len(rows), 2, figsize=(20, 6 * len(rows)), squeeze=False)
        for r, im in enumerate(rows):
            for c, (d, lab, s) in enumerate([(a.a, a.a_label, sa), (a.b, a.b_label, sb)]):
                ax = axs[r, c]; ax.axis("off")
                fn = os.path.join(d, im)
                if os.path.isfile(fn):
                    ax.imshow(plt.imread(fn))
                ax.set_title(f"{lab} - {im[:-4]} (t = {s.get('latest_time', float('nan'))*1e3:.0f} ms)", fontsize=14)
        fig.tight_layout(); fig.savefig(os.path.join(a.out, "final_side_by_side.png"), dpi=70); plt.close(fig)
    # metrics table
    sa, sb = load(a.a), load(a.b)
    hdr = ["metric", f"{a.a_label} (end, t={sa.get('time', 0)*1e3:.0f} ms)", f"{a.b_label} (end, t={sb.get('time', 0)*1e3:.0f} ms)",
           f"{a.a_label} (avg last 20%)", f"{a.b_label} (avg last 20%)", "change of avg [%]"]
    rows = []
    for k, lab, sc, fmt in METRICS:
        va, vb = sa.get(k), sb.get(k)
        aa, ab = sa.get("avg_last20pct", {}).get(k), sb.get("avg_last20pct", {}).get(k)
        ch = (100 * (ab - aa) / aa) if (aa not in (None, 0) and ab is not None) else None
        g = lambda v: fmt.format(v * sc) if v is not None else "-"
        rows.append([lab, g(va), g(vb), g(aa), g(ab), f"{ch:+.0f}" if ch is not None else "-"])
    with open(os.path.join(a.out, "metrics_table.csv"), "w") as fh:
        fh.write(",".join(hdr) + "\n")
        for r in rows:
            fh.write(",".join(r) + "\n")
    with open(os.path.join(a.out, "metrics_table.md"), "w") as fh:
        fh.write("| " + " | ".join(hdr) + " |\n|" + "---|" * len(hdr) + "\n")
        for r in rows:
            fh.write("| " + " | ".join(r) + " |\n")
    fig, ax = plt.subplots(figsize=(15, 0.45 * (len(rows) + 2)))
    ax.axis("off")
    tb = ax.table(cellText=rows, colLabels=hdr, loc="center", cellLoc="center")
    tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 1.4)
    fig.tight_layout(); fig.savefig(os.path.join(a.out, "metrics_table.png"), dpi=130); plt.close(fig)
    print(open(os.path.join(a.out, "metrics_table.md")).read())


if __name__ == "__main__":
    main()
