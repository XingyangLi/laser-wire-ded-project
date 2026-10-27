#!/usr/bin/env python3
"""Slit on the trailing wire face, measured on the center-plane side sample.

The gap is the gas between the wire surface (x = 0.50 mm) and the metal wall
outside it. A wall is two consecutive 0.02 mm bins that are mostly metal, so
a single cell on the wire surface does not close the gap. Depth is the
contiguous run of a thin gap (at most 0.15 mm) that reaches highest.
Width is the median of that run. Open means the next slice is not metal
against the wire. A run persists when it is open, at least 0.10 mm deep,
and between 0.02 mm and 0.12 mm wide. Wider than that is a bare trailing
face, not the radiograph slit.
"""
import argparse
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WIRE_R_MM = 0.50
# Slices thinner than the target width, thicker than one 19 um cell.
DZ_MM = 0.025
Z_LO = 0.40
Z_HI = 1.75
GAP_MIN_MM = 0.015


def load_alpha(case, time_name):
    path = Path(case) / "postProcessing/sidePlane" / time_name / "alpha.metal_xz.raw"
    rows = []
    with open(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            p = line.split()
            if len(p) >= 4:
                rows.append([float(p[0]), float(p[2]), float(p[3])])
    if not rows:
        raise SystemExit(f"no samples in {path}")
    a = np.asarray(rows)
    return a[:, 0] * 1e3, a[:, 1] * 1e3, a[:, 2]


def side_times(case):
    root = Path(case) / "postProcessing/sidePlane"
    if not root.is_dir():
        return []
    names = []
    for p in root.iterdir():
        if (p / "alpha.metal_xz.raw").is_file():
            try:
                names.append((float(p.name), p.name))
            except ValueError:
                continue
    names.sort()
    return [n for _, n in names]


def _gap_width(x, alpha):
    """Millimetres from the wire surface to a sustained metal wall.

    0 if metal already occupies the face. Bins that stay gas out to the
    search limit return the cap (0.40 mm): the trailing face is bare.
    """
    band = (x > WIRE_R_MM - 0.02) & (x < WIRE_R_MM + 0.55)
    if not np.any(band):
        return 0.0
    xb = x[band]
    ab = alpha[band]
    edges = np.arange(WIRE_R_MM, WIRE_R_MM + 0.56, 0.02)
    metal_bin = []
    gas_bin = []
    for a0, b0 in zip(edges[:-1], edges[1:]):
        m = (xb >= a0) & (xb < b0)
        if not np.any(m):
            metal_bin.append(False)
            gas_bin.append(False)
            continue
        frac = float(np.mean(ab[m] >= 0.5))
        metal_bin.append(frac >= 0.5)
        gas_bin.append(frac < 0.5)
    # The first 0.06 mm has to be gas. Otherwise the melt is on the wire.
    if not any(gas_bin[:3]):
        return 0.0
    for i in range(len(metal_bin) - 1):
        if metal_bin[i] and metal_bin[i + 1]:
            return float(edges[i] - WIRE_R_MM)
    if any(gas_bin):
        last = max(i for i, g in enumerate(gas_bin) if g)
        return float(min(edges[last + 1] - WIRE_R_MM, 0.40))
    return 0.0


def measure(x, z, alpha):
    edges = np.arange(Z_LO, Z_HI + DZ_MM, DZ_MM)
    mids = 0.5 * (edges[:-1] + edges[1:])
    widths = np.zeros(mids.size)
    for i, (z0, z1) in enumerate(zip(edges[:-1], edges[1:])):
        m = (z >= z0) & (z < z1) & (x > 0.40) & (x < 1.30)
        if np.any(m):
            widths[i] = _gap_width(x[m], alpha[m])
    # A thin slit, not the bare face (those slices are near the 0.40 mm cap).
    thin = (widths >= GAP_MIN_MM) & (widths <= 0.15)
    best = None
    i = 0
    n = thin.size
    while i < n:
        if not thin[i]:
            i += 1
            continue
        j = i
        while j < n and thin[j]:
            j += 1
        # Prefer the run that climbs highest. Ties: the deeper one.
        span = (float(mids[i] - 0.5 * DZ_MM), float(mids[j - 1] + 0.5 * DZ_MM))
        depth = span[1] - span[0]
        if best is None or span[1] > best[0][1] + 1e-6 or (
            abs(span[1] - best[0][1]) <= 1e-6 and depth > best[1]
        ):
            w = widths[i:j]
            w = w[(w >= GAP_MIN_MM) & (w <= 0.15)]
            best = (span, depth, float(np.median(w)), float(w.max()), int(w.size), j)
        i = j
    n_wide = int(np.sum(widths >= 0.15))
    if best is None:
        return dict(
            depth_mm=0.0, width_mm=0.0, width_max_mm=0.0,
            z_lo_mm=None, z_hi_mm=None, open=False, persists=False,
            n_slices=0, wide=n_wide >= 4,
        )
    span, depth, width, width_max, n_slices, j = best
    # Capped when the next measured slice is metal on the wire. A wide or
    # missing slice above the run is the mouth opening into the gas.
    if j >= n:
        is_open = True
    else:
        is_open = not (widths[j] < GAP_MIN_MM)
    persists = bool(
        depth >= 0.10 and is_open and 0.02 <= width <= 0.12
    )
    return dict(
        depth_mm=depth,
        width_mm=width,
        width_max_mm=width_max,
        z_lo_mm=span[0],
        z_hi_mm=span[1],
        open=bool(is_open),
        persists=persists,
        n_slices=n_slices,
        wide=False,
    )


def stability(samples):
    """A film is steady when consecutive samples stay thin and deep.

    Width 0.03–0.08 mm, depth at least 0.25 mm, open, for at least 4 ms,
    with the depth moving by at most 0.08 mm and the width by at most 0.03 mm.
    """
    good = []
    for t, row in samples:
        w = row["width_mm"]
        good.append(
            row["open"]
            and row["depth_mm"] >= 0.25
            and 0.03 <= w <= 0.08
        )
    best = (0, 0)
    i = 0
    n = len(good)
    while i < n:
        if not good[i]:
            i += 1
            continue
        j = i
        while j < n and good[j]:
            j += 1
        if j - i > best[1] - best[0]:
            best = (i, j)
        i = j
    i, j = best
    if j - i < 2:
        return "no steady film"
    ts = [samples[k][0] for k in range(i, j)]
    depths = [samples[k][1]["depth_mm"] for k in range(i, j)]
    widths = [samples[k][1]["width_mm"] for k in range(i, j)]
    dur = ts[-1] - ts[0]
    dspan = max(depths) - min(depths)
    wspan = max(widths) - min(widths)
    steady = dur + 1e-9 >= 0.004 and dspan <= 0.08 and wspan <= 0.03
    state = "steady" if steady else "drifting"
    return (
        f"film {dur * 1e3:.1f} ms  depth {min(depths):.3f}–{max(depths):.3f} mm  "
        f"width {min(widths):.3f}–{max(widths):.3f} mm  {state}"
    )


def fmt(row):
    zlo = "—" if row["z_lo_mm"] is None else f"{row['z_lo_mm']:.2f}"
    zhi = "—" if row["z_hi_mm"] is None else f"{row['z_hi_mm']:.2f}"
    state = "open" if row["open"] else "capped"
    if row.get("wide"):
        stay = "bare face"
    elif row["persists"]:
        stay = "persists"
    else:
        stay = "gone"
    return (
        f"depth {row['depth_mm']:.3f} mm  width {row['width_mm']:.3f} mm "
        f"(max {row['width_max_mm']:.3f})  z {zlo}..{zhi} mm  {state}, {stay}"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", action="append", default=[])
    ap.add_argument("--tag", action="append", default=[])
    ap.add_argument("--times", nargs="*", default=[])
    args = ap.parse_args()
    cases = args.case or []
    tags = args.tag or [Path(c).name.replace("wire_cavity_", "") for c in cases]
    if len(tags) < len(cases):
        tags = tags + [Path(c).name for c in cases[len(tags):]]
    for case, tag in zip(cases, tags):
        times = args.times or side_times(case)
        if not times:
            print(f"{tag}: no side plane yet")
            continue
        samples = []
        for t in times:
            try:
                x, z, alpha = load_alpha(case, t)
            except FileNotFoundError:
                print(f"{tag} t={t}: missing side plane")
                continue
            row = measure(x, z, alpha)
            print(f"{tag} t={t}: {fmt(row)}")
            try:
                samples.append((float(t), row))
            except ValueError:
                continue
        if len(samples) >= 2:
            print(f"{tag} stability: {stability(samples)}")


if __name__ == "__main__":
    main()
