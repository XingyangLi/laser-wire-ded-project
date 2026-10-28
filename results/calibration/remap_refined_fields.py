#!/usr/bin/env python3
"""Copy volume fields onto a mesh that refineMesh just refined.

OpenFOAM.com v2406 refineMesh writes constant/polyMesh and a new-to-old
cellMap, and leaves the fields at the parent size. Child cells inherit the
parent value. The symmetry patch is the only boundary whose face count
changes; its nonuniform lists become uniform 0, which the pressure equation
replaces. Every other patch is outside the neck box and is left as stored.
"""
import sys
from pathlib import Path

import numpy as np


def read_labels(path):
    data = Path(path).read_bytes()
    k = data.find(b"\n(")
    n = int(data[:k].split()[-1])
    return np.frombuffer(data, dtype="<i4", count=n, offset=k + 2).copy()


def _list_span(data, j):
    """Byte span [j, end) of a nonuniform List starting at j, end just after ')'."""
    gt = data.find(b">", j)
    kind = data[j:gt].decode()
    width = 3 if "vector" in kind else 1
    nl = data.find(b"\n", gt)
    nl2 = data.find(b"\n", nl + 1)
    n = int(data[nl + 1:nl2])
    paren = data.find(b"(", nl2)
    end = paren + 1 + n * width * 8
    if data[end:end + 1] != b")":
        raise SystemExit(f"list closer at {end} is {data[end:end+8]!r}")
    return n, width, nl, end


def remap_internal(data, cell_map):
    i = data.find(b"internalField")
    if i < 0:
        return data
    j = data.find(b"nonuniform List<", i)
    if j < 0 or j - i > 80:
        return data
    n, width, nl, end = _list_span(data, j)
    if n == cell_map.size:
        return data
    if int(cell_map.max()) >= n:
        raise SystemExit(f"cellMap {cell_map.max()} outside field length {n}")
    old = np.frombuffer(data, dtype="<f8", count=n * width, offset=data.find(b"(", nl) + 1)
    old = old.reshape(n, width).copy()
    blob = np.ascontiguousarray(old[cell_map]).astype("<f8", copy=False).tobytes()
    count = str(cell_map.size).encode()
    return data[: nl + 1] + count + b"\n(" + blob + data[end:]


def scrub_symmetry(data):
    """Replace nonuniform lists on the symmetry patch with uniform 0."""
    start = data.find(b"\n    symmetry\n")
    if start < 0:
        return data
    pos = start
    while True:
        j = data.find(b"nonuniform List<", pos)
        nxt = data.find(b"\n    side\n", pos)
        if j < 0 or (nxt >= 0 and j > nxt):
            break
        n, width, nl, end = _list_span(data, j)
        repl = b"uniform (0 0 0)" if width == 3 else b"uniform 0"
        data = data[:j] + repl + data[end:]
        pos = j + len(repl)
    return data


def main():
    time_dir = Path(sys.argv[1])
    cell_map = read_labels(time_dir / "polyMesh" / "cellMap")
    n_new = int(cell_map.size)
    for path in sorted(time_dir.iterdir()):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"internalField" not in data and b"class" not in data[:800]:
            continue
        updated = scrub_symmetry(remap_internal(data, cell_map))
        if updated != data:
            path.write_bytes(updated)
    # The map is not a field. Leave the time directory with fields only.
    mesh_dir = time_dir / "polyMesh"
    for child in mesh_dir.iterdir():
        child.unlink()
    mesh_dir.rmdir()
    print(f"remapped fields in {time_dir} onto {n_new} cells")


if __name__ == "__main__":
    main()
