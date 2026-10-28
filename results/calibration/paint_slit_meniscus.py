#!/usr/bin/env python3
"""Paint a fused bead with a curved gas slit on the trailing wire face.

The square slot used for cal34–cal37 left no metal wall on the center plane
after 4 ms. This initial field is two ellipsoids (a pool on the plate, a
taller dome on the trailing side) with a groove cut along the wire. The
groove mouth is `--gap-mm` (default 0.06 mm) at z = 1.20 mm and tapers to a
point at z = 0.75 mm. It is only 0.28 mm wide in y so the center plane cuts
through it. `--film-mm` replaces that taper with a uniform gas layer of that
thickness on the trailing half of the wire, from z = 0.30 mm to 1.50 mm.

Runs on the serial mesh, after 0/ has been copied from 0.orig and before
decomposePar. Wire cells stay unmelted and at rest.
"""
import argparse
import math
from pathlib import Path

import numpy as np

WIRE_R = 0.50e-3
Z_TIP = 0.75e-3
Z_MOUTH = 1.20e-3
W_MOUTH = 0.060e-3
Y_GROOVE = 0.28e-3
# Uniform trailing-face film. 0 keeps the tapered groove.
FILM = 0.0
Z_FILM_LO = 0.30e-3
Z_FILM_HI = 1.50e-3
# Pool on the plate, top near the slit tip. Dome is taller and trailing.
POOL_C = (0.0, 0.0, 0.20e-3)
POOL_R = (1.15e-3, 0.95e-3, 0.55e-3)
DOME_C = (0.90e-3, 0.0, 0.78e-3)
DOME_R = (0.55e-3, 0.45e-3, 0.62e-3)


def after_header(path):
    data = Path(path).read_bytes()
    i = data.find(b"object")
    j = data.find(b"\n//", i)
    k = data.find(b"\n", j + 1)
    p = k + 1
    while data[p:p + 1] in (b"\n", b"\r"):
        p += 1
    return data, p


def read_count_paren(data, p):
    nl = data.find(b"\n", p)
    count = int(data[p:nl])
    q = nl + 1
    if data[q:q + 1] != b"(":
        raise SystemExit(f"{path_hint(data)} missing '(' at {q}")
    return count, q + 1


def path_hint(data):
    return "mesh list"


def read_points(path):
    data, p = after_header(path)
    n, q = read_count_paren(data, p)
    raw = np.frombuffer(data, dtype="<f8", count=n * 3, offset=q)
    return raw.reshape(n, 3).copy()


def read_labels(path):
    data, p = after_header(path)
    n, q = read_count_paren(data, p)
    return np.frombuffer(data, dtype="<i4", count=n, offset=q).copy()


def read_faces(path):
    data, p = after_header(path)
    nstart, q = read_count_paren(data, p)
    offsets = np.frombuffer(data, dtype="<i4", count=nstart, offset=q).copy()
    q2 = q + nstart * 4
    if data[q2:q2 + 1] != b")":
        raise SystemExit(f"faces: expected ')' , got {data[q2:q2 + 8]!r}")
    q2 += 1
    while data[q2:q2 + 1] in (b"\n", b"\r", b" "):
        q2 += 1
    ne, q3 = read_count_paren(data, q2)
    labels = np.frombuffer(data, dtype="<i4", count=ne, offset=q3).copy()
    return offsets, labels


def cell_centres(case):
    mesh = Path(case) / "constant/polyMesh"
    pts = read_points(mesh / "points")
    offsets, flabels = read_faces(mesh / "faces")
    owner = read_labels(mesh / "owner")
    neigh = read_labels(mesh / "neighbour")
    nfaces = offsets.size - 1
    if nfaces != len(owner):
        raise SystemExit(f"faces {nfaces} != owner {len(owner)}")
    if len(neigh) > nfaces:
        raise SystemExit(f"neighbour {len(neigh)} > faces {nfaces}")
    fc = np.zeros((nfaces, 3))
    for i in range(nfaces):
        fc[i] = pts[flabels[offsets[i]:offsets[i + 1]]].mean(axis=0)
    ncells = int(max(owner.max(), neigh.max())) + 1
    cc = np.zeros((ncells, 3))
    cnt = np.zeros(ncells)
    np.add.at(cc, owner, fc)
    np.add.at(cnt, owner, 1)
    np.add.at(cc, neigh, fc[:len(neigh)])
    np.add.at(cnt, neigh, 1)
    if np.any(cnt == 0):
        raise SystemExit(f"{int(np.sum(cnt == 0))} cells have no faces")
    cc /= cnt[:, None]
    return cc


def in_ellipsoid(x, y, z, c, r):
    return (
        ((x - c[0]) / r[0]) ** 2
        + ((y - c[1]) / r[1]) ** 2
        + ((z - c[2]) / r[2]) ** 2
    ) <= 1.0


def gap_width(z):
    if z <= Z_TIP:
        return 0.0
    if z >= Z_MOUTH:
        return W_MOUTH
    return W_MOUTH * (z - Z_TIP) / (Z_MOUTH - Z_TIP)


def in_groove(x, y, z):
    if y > Y_GROOVE or y >= WIRE_R or z <= Z_TIP:
        return False
    xs = math.sqrt(WIRE_R * WIRE_R - y * y)
    if x <= xs:
        return False
    return x < xs + gap_width(z)


def in_film(x, y, z):
    """Uniform gas layer on the trailing half, not only the groove mouth."""
    if FILM <= 0 or z < Z_FILM_LO or z > Z_FILM_HI or x <= 0:
        return False
    r = math.hypot(x, y)
    return WIRE_R < r < WIRE_R + FILM


def classify(x, y, z):
    """wire, slit, dome, pool, plate, substrate, gas."""
    if (x * x + y * y) < WIRE_R * WIRE_R and z > 0.08e-3:
        return "wire"
    if in_film(x, y, z):
        return "slit"
    if FILM <= 0 and in_groove(x, y, z):
        return "slit"
    if z > 0.0 and in_ellipsoid(x, y, z, DOME_C, DOME_R):
        return "dome"
    if z > 0.0 and in_ellipsoid(x, y, z, POOL_C, POOL_R):
        return "pool"
    if -0.45e-3 <= z <= 0.0 and -1.2e-3 <= x <= 1.6e-3 and y <= 1.1e-3:
        return "plate"
    if z <= 0.0:
        return "substrate"
    return "gas"


def replace_internal(path, declaration):
    data = Path(path).read_bytes()
    i = data.find(b"internalField")
    j = data.rfind(b"boundaryField")
    if i < 0 or j < 0 or j < i:
        raise SystemExit(f"no internalField/boundaryField in {path}")
    out = data[:i] + declaration.encode() + b"\n\n" + data[j:]
    out = out.replace(b"format      binary;", b"format      ascii;")
    out = out.replace(b"format          binary;", b"format          ascii;")
    Path(path).write_bytes(out)


def write_scalar(path, values):
    lines = "\n".join(f"{v:.8g}" for v in values)
    decl = (
        f"internalField   nonuniform List<scalar>\n{len(values)}\n(\n{lines}\n);"
    )
    replace_internal(path, decl)


def write_vector(path, values):
    lines = "\n".join(f"({v[0]:.8g} {v[1]:.8g} {v[2]:.8g})" for v in values)
    decl = (
        f"internalField   nonuniform List<vector>\n{len(values)}\n(\n{lines}\n);"
    )
    replace_internal(path, decl)


def scan_velocity(path):
    """Substrate velocity from 0/U. setFields writes that field in binary."""
    data = Path(path).read_bytes()
    key = data.find(b"internalField")
    if key < 0:
        return (0.004, 0.0, 0.0)
    head = data[key:key + 120]
    if b"nonuniform" in head:
        head = b""
    if b"uniform" in head and b"(" in head:
        body = head[head.find(b"(") + 1:head.find(b")")].decode("ascii", "replace")
        u, v, w = (float(p) for p in body.split())
        return (u, v, w)
    paren = data.find(b"(", key)
    if paren < 0 or paren + 1 + 24 > len(data):
        return (0.004, 0.0, 0.0)
    raw = np.frombuffer(data, dtype="<f8", count=3, offset=paren + 1)
    return (float(raw[0]), float(raw[1]), float(raw[2]))


def paint(case, wire_t, dry_run, gap_mm, film_mm):
    global W_MOUTH, FILM
    if gap_mm <= 0 or gap_mm > 0.40:
        raise SystemExit("--gap-mm must be in (0, 0.40]")
    if film_mm < 0 or film_mm > 0.40:
        raise SystemExit("--film-mm must be in [0, 0.40]")
    W_MOUTH = gap_mm * 1e-3
    FILM = film_mm * 1e-3
    if FILM > 0:
        print(
            f"trailing film {film_mm:.3f} mm from z = {Z_FILM_LO * 1e3:.2f}"
            f" to {Z_FILM_HI * 1e3:.2f} mm"
        )
    else:
        print(f"groove mouth {gap_mm:.3f} mm at z = {Z_MOUTH * 1e3:.2f} mm")
    cc = cell_centres(case)
    n = len(cc)
    alpha = np.zeros(n)
    temp = np.full(n, 300.0)
    cwire = np.zeros(n)
    hist = np.zeros(n)
    counts = {}
    for i, (x, y, z) in enumerate(cc):
        kind = classify(float(x), float(y), float(z))
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "wire":
            alpha[i] = 1.0
            temp[i] = wire_t
            cwire[i] = 1.0
            hist[i] = 0.0
        elif kind == "slit":
            alpha[i] = 0.0
            temp[i] = 500.0
        elif kind in ("dome", "pool"):
            alpha[i] = 1.0
            temp[i] = 2000.0 if kind == "pool" else 1950.0
            cwire[i] = 1.0
            hist[i] = 1.0
        elif kind == "plate":
            alpha[i] = 1.0
            temp[i] = 1900.0
            hist[i] = 1.0
        elif kind == "substrate":
            alpha[i] = 1.0
            temp[i] = 1100.0
            hist[i] = 1.0
    # Center-plane profile of the groove, for the launch log.
    print(f"cells {n}")
    for kind in ("substrate", "plate", "pool", "dome", "slit", "wire", "gas"):
        print(f"  {kind:10s} {counts.get(kind, 0)}")
    print("center-plane wall (y < 0.04 mm), x of first metal outside the wire")
    y = cc[:, 1]
    x = cc[:, 0]
    z = cc[:, 2]
    for z0 in np.arange(0.70e-3, 1.45e-3, 0.05e-3):
        m = (y < 0.04e-3) & (np.abs(z - z0) < 0.025e-3) & (x > WIRE_R + 0.005e-3)
        metal = m & (alpha > 0.5)
        gas = m & (alpha < 0.5) & (x < WIRE_R + W_MOUTH + 0.04e-3)
        if not np.any(metal):
            wall = "none"
            width = "bare" if np.any(gas) else "no samples"
        else:
            xw = float(x[metal].min())
            wall = f"{xw * 1e3:.3f} mm"
            width = f"{(xw - WIRE_R) * 1e3:.3f} mm"
        print(f"  z={z0 * 1e3:.2f}  wall {wall}  width {width}  gas {int(gas.sum())}")
    if dry_run:
        print("dry-run, fields not written")
        return
    case = Path(case)
    u0 = scan_velocity(case / "0/U")
    uu = np.tile(np.array(u0, dtype=float), (n, 1))
    wire = (cc[:, 0] ** 2 + cc[:, 1] ** 2) < WIRE_R ** 2
    wire &= cc[:, 2] > 0.08e-3
    uu[wire] = 0.0
    write_scalar(case / "0/alpha.metal", alpha)
    write_scalar(case / "0/T", temp)
    write_scalar(case / "0/cWire", cwire)
    write_scalar(case / "0/meltHistory", hist)
    write_vector(case / "0/U", uu)
    print("painted curved slit in", case / "0")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--wire-t", type=float, default=300.0)
    ap.add_argument("--gap-mm", type=float, default=0.06,
                    help="groove width at z = 1.20 mm (0.06 narrow, 0.12 wide)")
    ap.add_argument("--film-mm", type=float, default=0.0,
                    help="uniform trailing-face gas film [mm]; 0 keeps the tapered groove")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    paint(args.case, args.wire_t, args.dry_run, args.gap_mm, args.film_mm)


if __name__ == "__main__":
    main()
