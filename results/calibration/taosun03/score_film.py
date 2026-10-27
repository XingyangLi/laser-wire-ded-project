#!/usr/bin/env python3
"""Score the painted trailing film the way cal56 was scored.

Width is the gas from the wire surface (x = 0.50 mm) to the next sustained
metal wall, on the centre plane. An open mouth is a thin run whose next
slice is not metal on the wire. A face that stays gas out to 0.40 mm is
bare, not a slit.

One time holds when it is open, at least 0.25 mm deep, and 0.02–0.12 mm
wide. A window is steady when every sample in it is open, 0.03–0.08 mm
wide and at least 0.25 mm deep, the samples span at least 4 ms, and the
depth and width move by at most 0.08 mm and 0.03 mm.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import neck_state as ns
import slit_metric as sm


def centre_plane(case, tname):
    cc, alpha, _vel = ns.load(case, tname)
    band = np.abs(cc[:, 1]) < 4.0e-5
    if int(band.sum()) < 10:
        raise RuntimeError(f"{tname}: centre plane has {int(band.sum())} cells")
    x = cc[band, 0] * 1e3
    z = cc[band, 2] * 1e3
    return sm.measure(x, z, alpha[band])


def times_in(case, t0, t1):
    names = []
    for name in ns.time_dirs(case):
        try:
            t = float(name)
        except ValueError:
            continue
        if t0 - 1e-9 <= t <= t1 + 1e-9 and t > 1e-6:
            names.append((t, name))
    names.sort()
    return names


def main(argv):
    if len(argv) < 2:
        print(
            "usage: score_film.py CASE TIME | score_film.py CASE --window T0 T1",
            file=sys.stderr,
        )
        return 2
    case = argv[1]
    if len(argv) >= 5 and argv[2] == "--window":
        t0, t1 = float(argv[3]), float(argv[4])
        samples = []
        for t, name in times_in(case, t0, t1):
            row = centre_plane(case, name)
            print(f"t={name}: {sm.fmt(row)}")
            samples.append((t, row))
        if len(samples) < 2:
            print("FILM window has fewer than 2 samples")
            return 1
        text = sm.stability(samples)
        print(f"stability: {text}")
        return 0 if text.endswith("steady") else 1
    tname = argv[2]
    row = centre_plane(case, tname)
    print(f"t={tname}: {sm.fmt(row)}")
    hold = (
        row["open"]
        and row["depth_mm"] >= 0.25
        and 0.02 <= row["width_mm"] <= 0.12
    )
    print("FILM hold" if hold else "FILM lost")
    return 0 if hold else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
