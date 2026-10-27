#!/usr/bin/env python3
"""Column-preserving decomposition.

The ray-traced laser needs each vertical (x, y) column on one rank, so the
split is only in x. Ranks take contiguous x-slabs sized for equal cell
counts, which puts several ranks through a refined neck instead of one
geometric slice owning all of it.

    python column_decomp.py CASE NPROC
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_slit_video as rv


def assign(cc, nproc):
    cols = defaultdict(list)
    x_of = {}
    for i, (x, y, _z) in enumerate(cc):
        key = (int(round(x / 1e-8)), int(round(y / 1e-8)))
        cols[key].append(i)
        x_of[key] = x
    order = sorted(cols, key=lambda k: (x_of[k], k[1]))
    total = len(cc)
    labels = np.empty(total, dtype=np.int32)
    acc = 0
    rank = 0
    for key in order:
        ids = cols[key]
        # A fat column can jump more than one rank boundary. Catch up so
        # later slabs still fill the high ranks, and never split a column.
        while rank < nproc - 1 and acc >= int(round((rank + 1) * total / nproc)):
            rank += 1
        labels[ids] = rank
        acc += len(ids)
    counts = np.bincount(labels, minlength=nproc)
    if counts.min() < 1 or int(counts.size) != nproc:
        raise RuntimeError(
            f"empty rank in 0..{nproc - 1}: min {counts.min()} max {counts.max()}"
        )
    return labels, counts


def write_labels(path, labels):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write(
            "FoamFile\n{\n"
            "    version     2.0;\n"
            "    format      ascii;\n"
            "    class       labelList;\n"
            "    location    \"constant\";\n"
            "    object      cellDist;\n"
            "}\n"
            f"{len(labels)}\n(\n"
        )
        for v in labels:
            f.write(f"{int(v)}\n")
        f.write(")\n")


def main():
    if len(sys.argv) != 3:
        print("usage: column_decomp.py CASE NPROC", file=sys.stderr)
        return 2
    case = Path(sys.argv[1])
    nproc = int(sys.argv[2])
    mesh = case / "constant" / "polyMesh"
    cc = rv.cell_centres(mesh)
    labels, counts = assign(cc, nproc)
    # manualDecomp reads constant/cellDist (facesInstance on the time db).
    dest = case / "constant" / "cellDist"
    write_labels(dest, labels)
    stale = mesh / "cellDist"
    if stale.is_file():
        stale.unlink()
    print(
        f"cells {len(cc)}  ranks {nproc}  "
        f"per rank {counts.min()}..{counts.max()}  "
        f"mean {counts.mean():.0f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
