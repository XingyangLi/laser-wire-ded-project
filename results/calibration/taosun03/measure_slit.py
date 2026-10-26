#!/usr/bin/env python3
"""Slit depth and width from postProcessing/wireSlit/wireSlit.dat.

The film is gas on the trailing face of the wire, within 0.10 mm of the
surface and 0.15 mm of the centre plane. Depth is centre-to-centre.
Target: about 0.40 mm deep, about 0.05 mm wide, open, and still there
at the last sample.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "cases"


def series(path):
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        if not line or line[0] == "#":
            continue
        p = line.split()
        if len(p) < 7:
            continue
        rows.append(
            (
                float(p[0]),
                int(float(p[1])),
                float(p[2]) * 1e3,
                float(p[3]) * 1e3,
                float(p[4]) * 1e3,
                float(p[5]) * 1e3,
                int(float(p[6])),
            )
        )
    return rows


def summarise(tag):
    path = CASES / f"wire_cavity_{tag}" / "postProcessing" / "wireSlit" / "wireSlit.dat"
    if not path.is_file():
        return None
    rows = [r for r in series(path) if r[0] >= 0.05]
    if not rows:
        rows = series(path)
    if not rows:
        return None
    last = rows[-1]
    deep = max(rows, key=lambda r: r[4])
    # Persist: the last 40 ms (or the last three samples) stay open and
    # at least 0.15 mm deep.
    tail = [r for r in rows if r[0] >= last[0] - 0.04]
    if len(tail) < 3:
        tail = rows[-3:]
    persists = all(r[4] >= 0.15 and r[6] == 1 for r in tail) and len(tail) >= 2
    return {
        "tag": tag,
        "t": last[0],
        "n": last[1],
        "z0": last[2],
        "z1": last[3],
        "depth": last[4],
        "width": last[5],
        "open": last[6],
        "max_depth": deep[4],
        "max_t": deep[0],
        "persists": persists,
    }


def main():
    tags = sys.argv[1:]
    if not tags:
        tags = [p.name.replace("wire_cavity_", "") for p in sorted(CASES.glob("wire_cavity_cal1*"))]
    found = []
    for tag in tags:
        row = summarise(tag)
        if row:
            found.append(row)
    print(
        f"{'tag':<8} {'t':>6} {'depth':>7} {'width':>7} {'z0':>6} {'z1':>6} "
        f"{'n':>5} {'open':>4} {'maxD':>7} {'persist':>7}"
    )
    for r in found:
        print(
            f"{r['tag']:<8} {r['t']:6.3f} {r['depth']:7.3f} {r['width']:7.3f} "
            f"{r['z0']:6.2f} {r['z1']:6.2f} {r['n']:5d} {r['open']:4d} "
            f"{r['max_depth']:7.3f} {'yes' if r['persists'] else 'no':>7}"
        )
    if not found:
        print("no wireSlit.dat yet")


if __name__ == "__main__":
    main()
