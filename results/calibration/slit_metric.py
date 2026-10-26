#!/usr/bin/env python3
"""Slit on the trailing wire face, measured on the center-plane side sample.

The gap is the gas between the wire surface (x = 0.50 mm) and the first metal
outside it. Depth is the contiguous run of that gap that reaches highest, in
millimetres along z. Width is the median of the gap in that run. Open means
the run reaches gas with no metal above it. A run is counted as still there
when the depth is at least 0.10 mm.
"""
import argparse
from pathlib import Path

import numpy as np

ROOT = Path("/home/xingyang/laser-wire-ded-project")
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
    """Millimetres from the wire surface to the metal wall. 0 if shut."""
    gas = alpha < 0.5
    metal = ~gas
    near = gas & (x > WIRE_R_MM - 0.04) & (x < WIRE_R_MM + 0.12)
    if not np.any(near):
        return 0.0
    wall = metal & (x > WIRE_R_MM)
    if not np.any(wall):
        far = x[gas & (x > WIRE_R_MM)]
        if far.size == 0:
            return 0.0
        return float(min(far.max() - WIRE_R_MM, 0.40))
    x_wall = float(x[wall].min())
    between = gas & (x >= WIRE_R_MM - 0.02) & (x <= x_wall + 0.01)
    if not np.any(between) or x_wall <= WIRE_R_MM:
        return 0.0
    return float(x_wall - WIRE_R_MM)


def measure(x, z, alpha):
    edges = np.arange(Z_LO, Z_HI + DZ_MM, DZ_MM)
    mids = 0.5 * (edges[:-1] + edges[1:])
    widths = np.zeros(mids.size)
    for i, (z0, z1) in enumerate(zip(edges[:-1], edges[1:])):
        m = (z >= z0) & (z < z1) & (x > 0.40) & (x < 1.30)
        if np.any(m):
            widths[i] = _gap_width(x[m], alpha[m])
    open_gap = widths >= GAP_MIN_MM
    best = None
    i = 0
    n = open_gap.size
    while i < n:
        if not open_gap[i]:
            i += 1
            continue
        j = i
        while j < n and open_gap[j]:
            j += 1
        # Prefer the run that climbs highest. Ties: the deeper one.
        span = (float(mids[i] - 0.5 * DZ_MM), float(mids[j - 1] + 0.5 * DZ_MM))
        depth = span[1] - span[0]
        if best is None or span[1] > best[0][1] + 1e-6 or (
            abs(span[1] - best[0][1]) <= 1e-6 and depth > best[1]
        ):
            w = widths[i:j]
            w = w[w >= GAP_MIN_MM]
            best = (span, depth, float(np.median(w)), float(w.max()), int(w.size))
        i = j
    if best is None:
        return dict(
            depth_mm=0.0, width_mm=0.0, width_max_mm=0.0,
            z_lo_mm=None, z_hi_mm=None, open=False, persists=False, n_slices=0,
        )
    span, depth, width, width_max, n_slices = best
    # Open when the run's top slice is gas with no metal sitting above the gap.
    top = span[1]
    above = (z > top) & (z < top + 0.15) & (x > WIRE_R_MM) & (x < WIRE_R_MM + max(width, 0.05) + 0.04)
    metal_above = np.any(above & (alpha >= 0.5))
    gas_above = np.any(above & (alpha < 0.5))
    is_open = (not metal_above) or gas_above and not metal_above
    # A gap that simply runs out of samples at the top of the window is open
    # if metal does not cap it.
    if not np.any(above):
        is_open = True
    return dict(
        depth_mm=depth,
        width_mm=width,
        width_max_mm=width_max,
        z_lo_mm=span[0],
        z_hi_mm=span[1],
        open=bool(is_open),
        persists=bool(depth >= 0.10 and is_open),
        n_slices=n_slices,
    )


def fmt(row):
    zlo = "—" if row["z_lo_mm"] is None else f"{row['z_lo_mm']:.2f}"
    zhi = "—" if row["z_hi_mm"] is None else f"{row['z_hi_mm']:.2f}"
    state = "open" if row["open"] else "capped"
    stay = "persists" if row["persists"] else "gone"
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
        for t in times:
            try:
                x, z, alpha = load_alpha(case, t)
            except FileNotFoundError:
                print(f"{tag} t={t}: missing side plane")
                continue
            row = measure(x, z, alpha)
            print(f"{tag} t={t}: {fmt(row)}")


if __name__ == "__main__":
    main()
