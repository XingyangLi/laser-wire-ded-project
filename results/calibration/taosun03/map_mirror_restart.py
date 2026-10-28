#!/usr/bin/env python3
"""Mirror a half-domain (y >= 0) restart onto a full-domain mesh.

Cell values are taken from the nearest source cell at (x, |y|, z). A
negative-y target flips the y-component of a vector. The boundary
conditions come from the destination 0.orig templates, so the symmetry
patch of the half mesh is not copied.
"""
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import neck_state as ns
from paint_slit_meniscus import write_scalar, write_vector

SCALARS = (
    "alpha.metal",
    "T",
    "p_rgh",
    "liquidFraction",
    "meltHistory",
    "cWire",
)
VECTORS = ("U",)


def template(case, name):
    orig = case / "0.orig"
    for cand in (orig / name, orig / f"{name}.orig"):
        if cand.is_file():
            return cand
    return None


def main(argv):
    if len(argv) != 4:
        print(
            "usage: map_mirror_restart.py SRC_CASE SRC_TIME DST_CASE DST_TIME",
            file=sys.stderr,
        )
        return 2
    src, tsrc, dst, tdst = Path(argv[0]), argv[1], Path(argv[2]), argv[3]
    src_cc = ns.cell_centres(src / "constant" / "polyMesh")
    dst_cc = ns.cell_centres(dst / "constant" / "polyMesh")
    if src_cc[:, 1].min() < -1e-8:
        raise SystemExit(f"{src} is not a y >= 0 half mesh")
    tree = cKDTree(src_cc)
    query = np.column_stack([dst_cc[:, 0], np.abs(dst_cc[:, 1]), dst_cc[:, 2]])
    dist, idx = tree.query(query, k=1)
    print(
        f"map {len(dst_cc)} cells from {len(src_cc)}  "
        f"nearest mm median {np.median(dist)*1e3:.4f}  "
        f"p95 {np.percentile(dist, 95)*1e3:.4f}  "
        f"max {dist.max()*1e3:.4f}"
    )
    if np.median(dist) > 1.5e-4:
        raise SystemExit("median map distance is above 0.15 mm; meshes do not match")
    out = dst / tdst
    out.mkdir(parents=True, exist_ok=True)
    neg = dst_cc[:, 1] < 0
    for name in SCALARS:
        templ = template(dst, name)
        src_f = src / tsrc / name
        if templ is None or not src_f.is_file():
            print(f"skip {name}")
            continue
        vals = ns.read_internal(src_f, "scalar")
        if vals is None:
            raise SystemExit(f"cannot read {src_f}")
        dest = out / name
        dest.write_bytes(templ.read_bytes())
        write_scalar(dest, vals[idx])
        print(f"wrote {name} {vals[idx].min():.4g}..{vals[idx].max():.4g}")
    for name in VECTORS:
        templ = template(dst, name)
        src_f = src / tsrc / name
        if templ is None or not src_f.is_file():
            print(f"skip {name}")
            continue
        vals = ns.read_internal(src_f, "vector")
        if vals is None:
            vals = ns.read_uniform(src_f, "vector", len(src_cc))
        if vals is None:
            raise SystemExit(f"cannot read {src_f}")
        mapped = vals[idx].copy()
        mapped[neg, 1] *= -1
        dest = out / name
        dest.write_bytes(templ.read_bytes())
        write_vector(dest, mapped)
        print(f"wrote {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
