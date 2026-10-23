#!/usr/bin/env python3
"""Score finished TaoSun-03 screens against the side-view radiograph.

The radiograph is a rounded dome, higher on the trailing side, with a small
notch where the melt pins on the wire. Gas in that pool should be small closed
bubbles (about 0.05–0.3 mm), not a large open wake. A gas sheet under the bead
is a non-wetted film: on the runs scored here the molten plate line sits near
50–60° and every molten plate cell is receding, and the substrate under the
bead stays below the solidus. This script turns those checks into a 0–10 score
from the solver tables, the center-plane cut (``sidePlane``, y = 20 µm) and
``<tag>_metrics.csv`` when ``plot_calibration.py`` has run. It does not start
a solver.

    python3 results/calibration/taosun03/score_screens.py
    python3 results/calibration/taosun03/score_screens.py cal34 cal37
"""
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CASES = ROOT / "cases"

# One line each, matching the launch scripts.
QUESTIONS = {
    "cal31": "cal08 at wire-refine 2",
    "cal32": "trail window 45/120",
    "cal33": "trail window 75/160",
    "cal34": "trail window 60/140",
    "cal35": "slow scan, rear-heavy power",
    "cal36": "700 W on the wire",
    "cal37": "plate window 150/170",
    "cal38": "trail window 30/100",
    "cal39": "trail window 90/170",
    "cal40": "trail window 20/90",
    "cal41": "trail window 100/165",
    "cal42": "feed 28 mm/s",
    "cal43": "powers 50/50/650",
    "cal44": "scan 1.5 mm/s",
    "cal45": "flank aim z 0.95 mm",
    "cal46": "foot aim z 0.30 mm",
    "cal47": "plate window 90/140",
    "cal48": "Marangoni on",
    "cal49": "wire window 15/50",
    "cal50": "trail sector 45 deg",
    "cal51": "0.18 mm spots",
    "cal52": "wire gap 0.02 mm",
    "cal53": "feed 32 mm/s",
    "cal54": "scan 2.5 mm/s",
    "cal55": "rear inclination -48 deg",
    "cal56": "force factor 2",
    "cal57": "wire window 45/110",
    "cal58": "front spots 80 W",
    "cal59": "60/140 window with cal35 section",
    "cal61": "60/140 window with cal36 power",
    "cal62": "cal36 powers at scan 2 mm/s",
    "cal63": "cal36 at wire-refine 2",
    "cal64": "cal36 with a 0.40 mm rear spot",
    "cal65": "700 W, 60/140 window, scan 2 mm/s",
    "cal66": "700 W with 30/100 trail window",
    "cal67": "700 W, rear aim z 0.35 mm",
    "cal68": "700 W with feed 32 mm/s",
    "cal69": "650 W rear spot with feed 28 mm/s",
    "cal70": "650 W rear spot with 60/140 window",
    "cal71": "700 W on a full-width mesh",
    "cal72": "650 W rear spot at scan 2 mm/s",
    "cal73": "powers 25/25/700",
    "cal74": "700 W with a 0.18 mm rear spot",
    "cal75": "700 W, rear aim z 0.70 mm",
    "cal76": "650 W rear spot with 30/100 window",
    "cal77": "700 W, rear inclination -28 deg",
    "cal78": "700 W with wire window 15/50",
    "cal79": "80/80/500 W with 60/140 window",
    "cal80": "80/80/500 W with feed 22 mm/s",
    "cal81": "powers 40/40/560 at scan 2 mm/s",
    "cal82": "650 W rear spot with 45/120 window",
    "cal83": "700 W with 45/120 window",
    "cal84": "700 W at scan 5 mm/s",
    "cal85": "600 W rear spot",
    "cal86": "700 W with wire gap 0.02 mm",
    "cal87": "powers 80/80/700",
    "cal88": "powers 50/50/700",
    "cal89": "700 W at scan 3.5 mm/s",
    "cal90": "700 W with force factor 10",
    "cal91": "powers 40/40/650 at scan 3 mm/s",
    "cal92": "powers 60/60/700",
    "cal94": "powers 60/60/560 at scan 2 mm/s",
    "cal95": "650 W rear spot at scan 2.5 mm/s",
    "cal96": "650 W rear spot with feed 16 mm/s",
    "cal97": "powers 50/50/600 at scan 2 mm/s",
    "cal98": "powers 70/70/650 at scan 2 mm/s",
    "cal99": "plate 10/40 on the 700 W notch",
    "cal100": "plate 20/55 on the 700 W notch",
    "cal101": "plate 5/25 on the 700 W notch",
    "cal102": "plate 30/80 on the 700 W notch",
    "cal103": "plate 10/40 with substrate absorptivity 0.55",
    "cal104": "plate 10/40 with preheat 900 K",
    "cal105": "plate 10/40, hotter fronts, preheat 800 K",
    "cal106": "plate 15/45, slow scan, absorptivity 0.60",
    "cal107": "plate 20/55 with substrate absorptivity 0.55",
    "cal108": "plate 20/55, absorptivity 0.55, preheat 900 K",
    "cal109": "plate 20/55, hotter fronts, preheat 800 K",
    "cal110": "pinned trail 15/50 on the heated 20/55 plate",
    "cal111": "narrow trail pin 20/45 on the heated 20/55 plate",
    "cal112": "pinned trail 15/50 with hotter fronts",
}

# 316L solidus. A column counts as fused only when the plate surface exceeds this.
TSOL_K = 1658.0


def rows(path):
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line.split())
    return out


def fnum(row, i):
    try:
        return float(row[i])
    except (IndexError, ValueError, TypeError):
        return None


def metrics_csv(tag):
    path = OUT / f"{tag}_metrics.csv"
    if not path.is_file():
        return {}
    out = {}
    with path.open() as fh:
        for rec in csv.DictReader(fh):
            # plot_calibration writes quantity,value
            if "quantity" in rec:
                out[rec["quantity"]] = rec["value"]
            elif rec:
                k = next(iter(rec))
                out[k] = rec[k]
    return out


def as_float(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def nearest_row(table, t):
    if not table:
        return []
    if t is None:
        return table[-1]
    best = table[-1]
    bestd = 1e9
    for row in table:
        tv = fnum(row, 0)
        if tv is None:
            continue
        d = abs(tv - t)
        if d < bestd:
            bestd = d
            best = row
    return best


def load_raw(path):
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            out.append((float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])))
        except ValueError:
            continue
    return out


def center_plane(case, t_target):
    """Gas gap and substrate melting on the y = 20 µm cut through the wire."""
    root = case / "postProcessing" / "sidePlane"
    if not root.is_dir():
        return {}
    times = []
    for d in root.iterdir():
        if not d.is_dir():
            continue
        try:
            times.append((float(d.name), d))
        except ValueError:
            continue
    if not times:
        return {}
    times.sort()
    t, directory = times[-1] if t_target is None else min(times, key=lambda td: abs(td[0] - t_target))
    alpha = load_raw(directory / "alpha.metal_xz.raw")
    temp = load_raw(directory / "T_xz.raw")
    if not alpha:
        return {"t_plane_s": t}
    temps = temp if len(temp) == len(alpha) else []
    cols = {}
    for i, (x, _y, z, al) in enumerate(alpha):
        if x < 0.6e-3 or x > 4.0e-3:
            continue
        key = round(x / 0.15e-3)
        cols.setdefault(key, []).append((z, al, temps[i][3] if temps else None))
    n_cols = n_gap = n_melt = 0
    for pts in cols.values():
        roof = [z for z, al, _t in pts if al > 0.5 and z > 0.45e-3]
        if not roof:
            continue
        n_cols += 1
        z_roof = min(roof)
        gas_under = any(al < 0.5 and 0.0 < z < z_roof - 0.05e-3 for z, al, _t in pts)
        metal_under = any(al > 0.5 and -0.05e-3 < z < z_roof for z, al, _t in pts)
        if gas_under and not metal_under:
            n_gap += 1
        if any(tk is not None and tk > TSOL_K and -0.25e-3 < z < 0.05e-3 for z, _al, tk in pts):
            n_melt += 1
    return {"t_plane_s": t, "n_cols": n_cols, "n_gap": n_gap, "n_melt": n_melt}


def bubble_report(pores):
    """Closed gas bubbles inside the pool. A one-cell mobile pore does not count."""
    parsed = []
    for e in pores:
        if len(e) < 11:
            continue
        try:
            parsed.append({
                "t": float(e[0]),
                "typ": int(float(e[2])),
                "locked": int(float(e[3])),
                "d": float(e[5]) * 1e3,
                "cx": float(e[6]) * 1e3,
                "cy": float(e[7]) * 1e3,
                "cz": float(e[8]) * 1e3,
                "shell": float(e[10]),
            })
        except ValueError:
            continue
    notes = []
    if not parsed:
        return 0, False, notes
    tlast = max(p["t"] for p in parsed)
    last = [p for p in parsed if abs(p["t"] - tlast) < 1e-6]
    if any(p["typ"] == 2 and p["locked"] and p["cz"] < 0.6 for p in last):
        notes.append("lack-of-fusion at the foot, not a pool bubble")
    if any(p["typ"] == 1 and p["d"] > 0.30 for p in last):
        notes.append("gas region larger than 0.3 mm")
    cands = [
        p for p in last
        if p["typ"] == 1 and 0.05 <= p["d"] <= 0.30 and 0.35 <= p["cz"] <= 2.4
    ]
    n = 0
    locked = False
    for p in cands:
        if p["locked"] == 0 and p["shell"] >= 0.5:
            continue
        span_times = []
        for q in parsed:
            if q["typ"] != 1 or not (0.05 <= q["d"] <= 0.30):
                continue
            if abs(q["cx"] - p["cx"]) < 0.25 and abs(q["cy"] - p["cy"]) < 0.25 and abs(q["cz"] - p["cz"]) < 0.25:
                span_times.append(q["t"])
        span = (max(span_times) - min(span_times)) if len(span_times) >= 2 else 0.0
        if p["locked"] == 1 or (p["shell"] < 0.5 and span >= 0.01):
            n += 1
            locked = locked or p["locked"] == 1
    return n, locked, notes


def finished(tag):
    case = CASES / f"wire_cavity_{tag}"
    cont = case / "log.laserWireDEDFoam.continue"
    log = case / "log.laserWireDEDFoam"
    if cont.is_file():
        text = cont.read_text(errors="replace")
        if "FOAM FATAL" in text:
            return "fatal"
        if text.rstrip().endswith("End"):
            return "done"
        return "continuing"
    if not log.is_file():
        return ""
    text = log.read_text(errors="replace")
    if "FOAM FATAL" in text:
        return "fatal"
    if text.rstrip().endswith("End"):
        return "done"
    return ""


def collect(tag):
    case = CASES / f"wire_cavity_{tag}"
    contact = rows(case / "postProcessing" / "contactLine" / "contactLine.dat")
    cavity = rows(case / "postProcessing" / "wireCavity" / "wireCavity.dat")
    pores = rows(case / "postProcessing" / "porosity" / "porosity.dat")
    pore_rows = rows(case / "postProcessing" / "porosity" / "pores.dat")
    events = rows(case / "postProcessing" / "wireCavity" / "events.dat")
    m = metrics_csv(tag)
    t_slice = as_float(m.get("t_slice_s"))
    cl = nearest_row(contact, t_slice) if (OUT / f"{tag}_vs_radiograph.png").is_file() else (contact[-1] if contact else [])
    cv = cavity[-1] if cavity else []
    po = pores[-1] if pores else []
    n_close = sum(1 for e in events if len(e) > 1 and e[1] == "closure")
    n_pinch = sum(1 for e in events if len(e) > 1 and e[1] == "pinchoff")
    n_bubbles, bubble_locked, bubble_notes = bubble_report(pore_rows)
    plane = center_plane(case, t_slice)
    status = { "0": "none", "1": "open", "2": "closed", "3": "mixed" }.get(
        cv[1] if len(cv) > 1 else "", cv[1] if len(cv) > 1 else ""
    )
    rec = {
        "tag": tag,
        "question": QUESTIONS.get(tag, ""),
        "state": finished(tag) or "running",
        "t_s": fnum(cl, 0),
        "n_wire": fnum(cl, 15),
        "n_pin": fnum(cl, 16),
        "n_adv": fnum(cl, 17),
        "n_rec": fnum(cl, 18),
        "z_max_mm": None if fnum(cl, 19) is None or fnum(cl, 19) < -0.4 else fnum(cl, 19) * 1e3,
        "z_min_mm": None if fnum(cl, 20) is None or fnum(cl, 20) < -0.4 else fnum(cl, 20) * 1e3,
        "trail_mm": as_float(m.get("trail_z_max_mm")),
        "lead_mm": as_float(m.get("lead_z_max_mm")),
        "bead_mm": as_float(m.get("bead_z_max_mm")),
        "t_slice_s": as_float(m.get("t_slice_s")),
        "status": m.get("cavity_status") or status,
        "vol_mm3": as_float(m.get("cavity_volume_mm3")),
        "cx_mm": as_float(m.get("cavity_cx_mm")),
        "cy_mm": as_float(m.get("cavity_cy_mm")),
        "cz_mm": as_float(m.get("cavity_cz_mm")),
        "n_pores": fnum(po, 1),
        "n_locked": fnum(po, 2),
        "n_entrap": fnum(po, 3),
        "n_lof": fnum(po, 4),
        "closures": n_close,
        "pinchoffs": n_pinch,
        "n_plate": fnum(cl, 1),
        "n_plate_pin": fnum(cl, 2),
        "n_plate_adv": fnum(cl, 3),
        "n_plate_rec": fnum(cl, 4),
        "theta_plate": fnum(cl, 6),
        "n_cols": plane.get("n_cols"),
        "n_gap": plane.get("n_gap"),
        "n_melt": plane.get("n_melt"),
        "n_bubbles": n_bubbles,
        "bubble_locked": bubble_locked,
        "bubble_notes": bubble_notes,
        "has_figures": (OUT / f"{tag}_vs_radiograph.png").is_file(),
    }
    if rec["vol_mm3"] is None and fnum(cv, 4) is not None:
        rec["vol_mm3"] = fnum(cv, 4) * 1e9
    if rec["cx_mm"] is None and fnum(cv, 9) is not None:
        rec["cx_mm"] = fnum(cv, 9) * 1e3
    if rec["cy_mm"] is None and fnum(cv, 10) is not None:
        rec["cy_mm"] = fnum(cv, 10) * 1e3
    if rec["cz_mm"] is None and fnum(cv, 11) is not None:
        rec["cz_mm"] = fnum(cv, 11) * 1e3
    # A continuation keeps writing the contact table. The score stays on the
    # posted slice so it matches the comparison figure.
    if rec["has_figures"]:
        for src, dst in (
            ("t_contact_s", "t_s"),
            ("z_wire_max_mm", "z_max_mm"),
            ("z_wire_min_mm", "z_min_mm"),
            ("n_wire", "n_wire"),
            ("n_wire_pinned", "n_pin"),
            ("n_wire_advancing", "n_adv"),
            ("n_wire_receding", "n_rec"),
        ):
            val = as_float(m.get(src))
            if val is not None:
                rec[dst] = val
    rec["score"], rec["notes"] = score(rec)
    return rec


def score(r):
    """0–10. Dome 3, wire notch 2, plate wetting and fusion 3, closed bubbles 2.

    An open wake does not score. A one-cell mobile gas pore does not score.
    Bubble points are withheld while the molten plate line is all receding or
    a gas sheet sits under the bead on the center plane.
    """
    notes = []
    pts = 0.0
    trail, lead = r["trail_mm"], r["lead_mm"]
    if trail is None:
        notes.append("no side slice yet")
    elif 1.45 <= trail <= 2.30:
        pts += 2
    elif trail >= 1.15:
        pts += 1
        notes.append("crest under 1.45 mm")
    else:
        notes.append("crest low")
    if trail is not None and trail > 2.30:
        notes.append("crest above 2.30 mm")
    if trail is not None and lead is not None:
        gap = trail - lead
        if gap >= 0.35:
            pts += 1
        elif gap >= 0.10:
            notes.append("trailing side only slightly higher")
        else:
            notes.append("leading side as high as the trail")
    zmax, zmin = r["z_max_mm"], r["z_min_mm"]
    nwire = r["n_wire"] or 0
    npin = r["n_pin"] or 0
    if zmin is not None and zmin < 0.45:
        notes.append("wire line slipped toward the foot")
    elif zmax is not None and zmin is not None and zmax >= 1.20 and zmin >= 0.80 and nwire >= 4:
        near = trail is None or abs(zmax - trail) <= 0.45
        if near and nwire > 0 and npin / nwire >= 0.5:
            pts += 2
        elif near:
            pts += 1
            notes.append("line at the crest but not mostly pinned")
        else:
            notes.append("line not level with the crest")
    elif zmax is not None and zmax >= 0.90:
        pts += 1
        notes.append("wire line only partly up the flank")
    else:
        notes.append("no neck")
    molten = r.get("n_plate") or 0
    ppin = r.get("n_plate_pin") or 0
    padv = r.get("n_plate_adv") or 0
    prec = r.get("n_plate_rec") or 0
    n_cols = r.get("n_cols") or 0
    n_gap = r.get("n_gap") or 0
    n_melt = r.get("n_melt") or 0
    gap_frac = (n_gap / n_cols) if n_cols else None
    melt_frac = (n_melt / n_cols) if n_cols else None
    all_rec = molten >= 4 and prec / molten > 0.85
    gas_film = gap_frac is not None and gap_frac > 0.20
    wet_pts = 0
    if gas_film:
        notes.append("gas layer under the bead on the center plane")
    elif all_rec:
        th = r.get("theta_plate")
        if th is not None and th > 0:
            notes.append(f"plate line all receding at {th:.0f} deg")
        else:
            notes.append("plate line all receding")
    line_wet = molten >= 4 and (ppin + padv) / molten >= 0.5 and prec / molten <= 0.5
    if line_wet and not gas_film:
        wet_pts += 1
    if n_cols and melt_frac is not None and melt_frac >= 0.50 and not gas_film and not all_rec:
        wet_pts += 2
    elif n_cols and melt_frac is not None and melt_frac >= 0.25 and not gas_film and not all_rec:
        wet_pts += 1
        notes.append("substrate only partly melted")
    elif n_cols and (melt_frac is None or melt_frac < 0.25):
        notes.append("substrate under the bead stays solid")
    elif not n_cols:
        notes.append("no trailing bead on the center plane yet")
    pts += wet_pts
    notes.extend(r.get("bubble_notes") or [])
    nb = r.get("n_bubbles") or 0
    if gas_film or all_rec or wet_pts < 1:
        notes.append("no scored bubble while the plate is unwetted")
    elif nb >= 2 or (nb >= 1 and r.get("bubble_locked")):
        pts += 2
    elif nb == 1:
        pts += 1
        notes.append("one closed bubble in the pool")
    else:
        notes.append("no closed bubble of 0.05-0.3 mm")
    if r["status"] == "open" and (r["vol_mm3"] or 0) > 0.5:
        notes.append("open wake is not scored")
    return pts, "; ".join(notes)


def main(argv):
    tags = argv[1:] or [f"cal{i}" for i in range(31, 120)]
    recs = []
    for tag in tags:
        case = CASES / f"wire_cavity_{tag}"
        if not case.is_dir():
            continue
        recs.append(collect(tag))
    ranked = sorted(
        recs,
        key=lambda r: (r["state"] in ("done", "continuing"), r["score"], r["t_s"] or 0),
        reverse=True,
    )
    dest = OUT / "ranking.csv"
    fields = [
        "tag", "state", "score", "t_s", "t_slice_s", "bead_mm", "trail_mm", "lead_mm",
        "z_min_mm", "z_max_mm", "n_wire", "n_pin", "status", "vol_mm3", "cx_mm",
        "cy_mm", "cz_mm", "closures", "pinchoffs", "n_pores", "n_locked",
        "n_plate", "n_plate_pin", "n_plate_adv", "n_plate_rec", "theta_plate",
        "n_cols", "n_gap", "n_melt", "n_bubbles",
        "has_figures", "question", "notes",
    ]
    with dest.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in ranked:
            w.writerow(r)
    print(f"{'tag':6} {'st':7} {'sc':4} {'t':6} {'trail':6} {'lead':6} {'plate':12} {'melt':6} {'bub':3} notes")
    for r in ranked:
        plate = "-"
        if r.get("n_plate"):
            plate = f"{int(r['n_plate_rec'] or 0)}/{int(r['n_plate'])}r"
        melt = "-"
        if r.get("n_cols"):
            melt = f"{int(r.get('n_melt') or 0)}/{int(r['n_cols'])}"
        def n(v):
            return "-" if v is None else f"{v:.2f}"
        print(
            f"{r['tag']:6} {r['state']:7} {r['score']:4.0f} {n(r['t_s']):6} "
            f"{n(r['trail_mm']):6} {n(r['lead_mm']):6} {plate:12} {melt:6} "
            f"{int(r.get('n_bubbles') or 0):3} {r['notes']}"
        )
    print("wrote", dest)


if __name__ == "__main__":
    main(sys.argv)
