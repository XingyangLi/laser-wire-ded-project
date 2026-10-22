#!/usr/bin/env python3
"""Score finished TaoSun-03 screens against the side-view radiograph.

The radiograph is a rounded dome about 1.5–2 mm tall, higher on the trailing
side, with the three-phase line pinned on the wire at that neck, and a gas
cavity in the wake. This script turns those checks into a 0–10 score from the
solver tables and from ``<tag>_metrics.csv`` when ``plot_calibration.py`` has
run. It does not start a solver.

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
}


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
    events = rows(case / "postProcessing" / "wireCavity" / "events.dat")
    m = metrics_csv(tag)
    cl = contact[-1] if contact else []
    cv = cavity[-1] if cavity else []
    po = pores[-1] if pores else []
    n_close = sum(1 for e in events if len(e) > 1 and e[1] == "closure")
    n_pinch = sum(1 for e in events if len(e) > 1 and e[1] == "pinchoff")
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
    """0–10. Height 2, trailing-over-leading 2, neck 3, wake 2, closure 1."""
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
    if trail is not None and lead is not None:
        gap = trail - lead
        if gap >= 0.35:
            pts += 2
        elif gap >= 0.10:
            pts += 1
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
            pts += 3
        elif near:
            pts += 2
            notes.append("line at the crest but not mostly pinned")
        else:
            pts += 1
            notes.append("line not level with the crest")
    elif zmax is not None and zmax >= 0.90:
        pts += 1
        notes.append("wire line only partly up the flank")
    else:
        notes.append("no neck")
    cx, cy, vol, cz = r["cx_mm"], r["cy_mm"], r["vol_mm3"], r["cz_mm"]
    wake = (
        r["status"] not in ("", "none", None)
        and cx is not None and cx > 0.2
        and vol is not None and vol > 0.5
        and cz is not None and cz > 0.4
    )
    if wake:
        pts += 1
        center = (cy is not None and cy < 0.60) or r["status"] in ("closed", "mixed")
        if center:
            pts += 1
        else:
            notes.append("cavity off the center plane")
    else:
        notes.append("no wake cavity")
    if (r["closures"] or 0) > 0 or r["status"] in ("closed", "mixed"):
        pts += 1
    elif (r["n_locked"] or 0) > 0 or (r["pinchoffs"] or 0) > 0:
        notes.append("pinch-off recorded, cavity still open")
    else:
        notes.append("no closure")
    return pts, "; ".join(notes)


def main(argv):
    tags = argv[1:] or [f"cal{i}" for i in range(31, 59)]
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
        "has_figures", "question", "notes",
    ]
    with dest.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in ranked:
            w.writerow(r)
    print(f"{'tag':6} {'st':7} {'sc':4} {'t':6} {'trail':6} {'lead':6} {'zWire':13} {'cav':6} {'cy':5} {'cl':3} notes")
    for r in ranked:
        zw = "-"
        if r["z_min_mm"] is not None and r["z_max_mm"] is not None:
            zw = f"{r['z_min_mm']:.2f}-{r['z_max_mm']:.2f}"
        def n(v):
            return "-" if v is None else f"{v:.2f}"
        print(
            f"{r['tag']:6} {r['state']:7} {r['score']:4.0f} {n(r['t_s']):6} "
            f"{n(r['trail_mm']):6} {n(r['lead_mm']):6} {zw:13} {str(r['status']):6} "
            f"{n(r['cy_mm']):5} {r['closures']:3} {r['notes']}"
        )
    print("wrote", dest)


if __name__ == "__main__":
    main(sys.argv)
