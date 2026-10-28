#!/usr/bin/env python3
"""When a coarse screen finishes with the wire line still on the flank, continue it.

Keeps going until every listed tag has been considered once. Refuses to start
a continuation if the slot file already holds 30 or more ranks.
"""
import csv
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/asb6102/laser-wire-ded-project")
OUT = ROOT / "results/calibration/taosun03"
SLOT = Path("/tmp/taosun03-lwded-slots")
# tag -> longer end time. Only screens, not the refined cal31.
EXTEND = {
    "cal32": "0.55",
    "cal33": "0.55",
    "cal34": "0.55",
    "cal35": "0.70",
    "cal36": "0.55",
    "cal37": "0.45",
    "cal38": "0.50",
    "cal39": "0.50",
    "cal40": "0.50",
    "cal41": "0.50",
    "cal42": "0.55",
    "cal43": "0.55",
    "cal44": "0.60",
    "cal45": "0.50",
    "cal46": "0.50",
    "cal47": "0.45",
    "cal48": "0.50",
    "cal49": "0.50",
}


def slots():
    try:
        return int(SLOT.read_text().strip() or "0")
    except (OSError, ValueError):
        return 0


def finished(tag):
    log = OUT / f"{tag}_launch.log"
    if not log.is_file():
        return False
    text = log.read_text(errors="replace")
    return f"{tag.upper()}_DONE" in text


def metrics(tag):
    path = OUT / f"{tag}_metrics.csv"
    if not path.is_file():
        return {}
    out = {}
    with path.open() as fh:
        for row in csv.reader(fh):
            if len(row) >= 2 and row[0] != "quantity":
                out[row[0]] = row[1]
    return out


def promising(m):
    def f(key):
        try:
            return float(m[key])
        except (KeyError, ValueError, TypeError):
            return None
    zmax = f("z_wire_max_mm")
    trail = f("trail_z_max_mm")
    # Flank, not the top of the domain. A missing crest still continues
    # if the line is in the right band: 0.28 s is often before the bulb.
    if zmax is None:
        return False
    if not (0.6 <= zmax <= 2.3):
        return False
    if trail is not None and trail < 0.3:
        return False
    return True


def main():
    pending = set(EXTEND)
    while pending:
        used = slots()
        for tag in list(pending):
            mark = OUT / f"{tag}_continue.log"
            if mark.is_file() and f"CONTINUE_{tag}_DONE" in mark.read_text(errors="replace"):
                pending.discard(tag)
                continue
            if mark.is_file() and "CONTINUE " in mark.read_text(errors="replace"):
                # already launched
                pending.discard(tag)
                continue
            if not finished(tag):
                continue
            if not (OUT / f"{tag}_metrics.csv").is_file():
                continue
            m = metrics(tag)
            if not promising(m):
                print(f"skip {tag}: {m.get('z_wire_max_mm')} {m.get('trail_z_max_mm')}", flush=True)
                pending.discard(tag)
                continue
            if slots() >= 30:
                print(f"wait for a free rank before continuing {tag}", flush=True)
                break
            print(f"continue {tag} to {EXTEND[tag]}", flush=True)
            subprocess.Popen(
                ["bash", str(OUT / "continue_case.sh"), tag, EXTEND[tag]],
                start_new_session=True,
            )
            pending.discard(tag)
            time.sleep(2)
        if not pending:
            break
        time.sleep(30)
    print("WATCH_DONE", flush=True)


if __name__ == "__main__":
    main()
