#!/usr/bin/env python3
"""Neck velocity, interface smear, and the real trailing-face gap.

The solver's WireSlit width is capped at 0.10 mm. This reads the volume
field and reports the centre-plane gap, so a 0.45 mm opening is not
called a 0.05 mm film.

    neck_state.py CASE [TIME]
    neck_state.py CASE --latest --calm-max 8
"""
import sys
from pathlib import Path

import numpy as np

WIRE_R = 0.5e-3


def after_banner(data):
    marker = b"// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n"
    i = data.find(marker)
    if i < 0:
        raise RuntimeError("OpenFOAM banner missing")
    return data[i + len(marker):].lstrip()


def read_labels(path):
    rest = after_banner(path.read_bytes())
    n_str, _, rest = rest.partition(b"\n")
    n = int(n_str.strip())
    if not rest.startswith(b"("):
        raise RuntimeError(f"{path} is not a binary label list")
    return np.frombuffer(rest[1:1 + n * 4], dtype="<i4").copy()


def read_points(path):
    rest = after_banner(path.read_bytes())
    n_str, _, rest = rest.partition(b"\n")
    n = int(n_str.strip(b"() "))
    if rest.startswith(b"("):
        rest = rest[1:]
    return np.frombuffer(rest[:n * 24], dtype="<f8").reshape(n, 3).copy()


def read_faces(path):
    rest = after_banner(path.read_bytes())
    n_str, _, rest = rest.partition(b"\n")
    n_off = int(n_str.strip())
    if not rest.startswith(b"("):
        raise RuntimeError(f"{path} is not a binary face list")
    offs = np.frombuffer(rest[1:1 + n_off * 4], dtype="<i4").copy()
    rest = rest[1 + n_off * 4:]
    end = rest.find(b"(")
    nlab = int(rest[:end].strip(b")\n "))
    labels = np.frombuffer(rest[end + 1:end + 1 + nlab * 4], dtype="<i4").copy()
    return offs, labels


def read_internal(path, kind):
    data = path.read_bytes()
    key = f"internalField   nonuniform List<{kind}>".encode()
    i = data.find(key)
    if i < 0:
        return None
    rest = data[i + len(key):].lstrip()
    n_str, _, rest = rest.partition(b"\n")
    n = int(n_str.strip())
    if rest.startswith(b"("):
        rest = rest[1:]
    width = 8 if kind == "scalar" else 24
    if len(rest) < n * width:
        return None
    if kind == "scalar":
        return np.frombuffer(rest[:n * 8], dtype="<f8").copy()
    return np.frombuffer(rest[:n * 24], dtype="<f8").reshape(n, 3).copy()


def read_uniform(path, kind, n):
    """A uniform internalField, expanded to one value per cell.

    decomposePar writes an all-zero velocity as ``uniform (0 0 0)``.
    """
    data = Path(path).read_bytes()
    key = b"internalField   uniform"
    i = data.find(key)
    if i < 0 or n < 1:
        return None
    rest = data[i + len(key):].lstrip()
    if kind == "vector":
        if not rest.startswith(b"("):
            return None
        end = rest.find(b")")
        parts = rest[1:end].split()
        if len(parts) != 3:
            return None
        v = np.array([float(x) for x in parts], dtype=float)
        return np.tile(v, (n, 1))
    token = rest.split()[0].rstrip(b";")
    return np.full(n, float(token))


MESHES = {}


def cell_centres(mesh_dir):
    key = str(mesh_dir)
    if key in MESHES:
        return MESHES[key]
    pts = read_points(mesh_dir / "points")
    offs, labs = read_faces(mesh_dir / "faces")
    owner = read_labels(mesh_dir / "owner")
    neigh = read_labels(mesh_dir / "neighbour")
    n_faces = len(owner)
    n_cells = int(max(int(owner.max()), int(neigh.max()))) + 1
    if len(offs) == n_faces + 1 and np.all(np.diff(offs) == 4):
        fc = pts[labs.reshape(-1, 4)].mean(axis=1)
    else:
        fc = np.zeros((n_faces, 3))
        for i in range(n_faces):
            fc[i] = pts[labs[offs[i]:offs[i + 1]]].mean(axis=0)
    cc = np.zeros((n_cells, 3))
    cnt = np.zeros(n_cells)
    np.add.at(cc, owner, fc)
    np.add.at(cnt, owner, 1)
    np.add.at(cc, neigh, fc[:len(neigh)])
    np.add.at(cnt, neigh, 1)
    cc /= np.maximum(cnt, 1)[:, None]
    MESHES[key] = cc
    return cc


def time_dirs(case):
    case = Path(case)
    root = case / "processor0" if (case / "processor0").is_dir() else case
    names = []
    for p in root.iterdir():
        if not p.is_dir():
            continue
        try:
            float(p.name)
        except ValueError:
            continue
        names.append(p.name)
    return sorted(names, key=float)


def load(case, tname):
    case = Path(case)
    procs = sorted(case.glob("processor*"))
    if procs and (procs[0] / tname / "alpha.metal").is_file():
        parts = []
        for proc in procs:
            cc = cell_centres(proc / "constant" / "polyMesh")
            alpha = read_internal(proc / tname / "alpha.metal", "scalar")
            vel = read_internal(proc / tname / "U", "vector")
            if vel is None and alpha is not None:
                vel = read_uniform(proc / tname / "U", "vector", len(alpha))
            if alpha is None or vel is None or len(alpha) != len(cc):
                raise RuntimeError(f"{proc.name}/{tname}: field size does not match the mesh")
            parts.append((cc, alpha, vel))
        return (
            np.vstack([p[0] for p in parts]),
            np.concatenate([p[1] for p in parts]),
            np.vstack([p[2] for p in parts]),
        )
    cc = cell_centres(case / "constant" / "polyMesh")
    alpha = read_internal(case / tname / "alpha.metal", "scalar")
    vel = read_internal(case / tname / "U", "vector")
    if vel is None and alpha is not None:
        vel = read_uniform(case / tname / "U", "vector", len(alpha))
    if alpha is None or vel is None or len(alpha) != len(cc):
        raise RuntimeError(f"{tname}: field size does not match the mesh")
    return cc, alpha, vel


def film_rows(cc, alpha, z0=0.50e-3, z1=1.45e-3, dz=0.04e-3):
    """Gap between the wire surface and the next metal on the trailing side.

    Width is the centre-to-centre distance from the last wire metal to the
    first bead metal. A single gas cell is a real gap, not a zero width.
    """
    x, y, z = cc[:, 0], cc[:, 1], cc[:, 2]
    radius = np.sqrt(x * x + y * y)
    plane = (np.abs(y) < 4.0e-5) & (z >= z0) & (z < z1) & (x > 0.2e-3) & (x < 1.4e-3)
    rows = []
    zc = z0
    while zc < z1 - 0.5 * dz:
        sl = plane & (z >= zc) & (z < zc + dz)
        zm = zc
        zc += dz
        if sl.sum() < 3:
            continue
        wire = sl & (alpha >= 0.5) & (radius > WIRE_R - 4.0e-5) & (radius < WIRE_R + 3.0e-5)
        if not wire.any():
            gas = sl & (alpha < 0.5)
            if not gas.any():
                rows.append((zm, None, None, False))
            else:
                rows.append((zm, float(x[gas].min()), float(x[gas].max() - x[gas].min()), False))
            continue
        x_wire = float(x[wire].max())
        outward = sl & (x > x_wire + 5.0e-6)
        if not outward.any():
            rows.append((zm, None, None, False))
            continue
        order = np.argsort(x[outward])
        xs = x[outward][order]
        aa = alpha[outward][order]
        i = 0
        while i < len(aa) and aa[i] >= 0.5 and xs[i] < x_wire + 4.0e-5:
            i += 1
        if i >= len(aa) or aa[i] >= 0.5:
            rows.append((zm, None, None, False))
            continue
        i0 = i
        while i < len(aa) and aa[i] < 0.5:
            i += 1
        closed = i < len(aa) and aa[i] >= 0.5
        if closed:
            width = float(xs[i] - x_wire)
        else:
            width = float(xs[-1] - x_wire)
        rows.append((zm, float(xs[i0]), width, closed))
    return rows


def summarise(case, tname):
    cc, alpha, vel = load(case, tname)
    x, y, z = cc[:, 0], cc[:, 1], cc[:, 2]
    neck = (x > 0.2e-3) & (x < 1.2e-3) & (np.abs(y) < 0.4e-3) & (z > 0.3e-3) & (z < 1.6e-3)
    um = np.linalg.norm(vel, axis=1)
    smear = neck & (alpha > 0.05) & (alpha < 0.95)
    rows = film_rows(cc, alpha)
    closed = [(z, w) for z, x0, w, ok in rows if ok and w is not None and w > 0]
    thin = [(z, w) for z, w in closed if 0.03e-3 <= w <= 0.08e-3]
    depth = 0.0
    run = 0.0
    prev = None
    for z, _w in thin:
        if prev is not None and z - prev <= 0.05e-3:
            run = z - run0
        else:
            run0 = z
            run = 0.0
        prev = z
        depth = max(depth, run)
    return {
        "t": tname,
        "umax": float(um[neck].max()) if neck.any() else float(um.max()),
        "umed": float(np.median(um[neck])) if neck.any() else float(np.median(um)),
        "smear": float(smear.sum() / max(int(neck.sum()), 1)),
        "n_closed": len(closed),
        "width_mm": float(np.median([w for _, w in closed]) * 1e3) if closed else None,
        "thin_depth_mm": float(depth * 1e3),
        "n_thin": len(thin),
        "rows": rows,
    }


def report(case, tname):
    s = summarise(case, tname)
    print(
        f"t={s['t']}  neck|U|max={s['umax']:.2f} m/s  median={s['umed']:.3f}"
        f"  smear={s['smear']:.3f}  closed_bins={s['n_closed']}"
        f"  median_width_mm={s['width_mm']}  thin_depth_mm={s['thin_depth_mm']:.3f}"
        f"  thin_bins={s['n_thin']}"
    )
    for z, x0, w, ok in s["rows"]:
        if w is None:
            print(f"  z={z*1e3:5.2f} mm  metal")
        else:
            print(
                f"  z={z*1e3:5.2f} mm  gas_x0={x0*1e3:.3f} mm"
                f"  width={w*1e3:.3f} mm  {'closed' if ok else 'open'}"
            )
    return s


def main():
    args = sys.argv[1:]
    calm = None
    smear_max = 0.25
    if "--calm-max" in args:
        i = args.index("--calm-max")
        calm = float(args[i + 1])
        del args[i:i + 2]
    if "--smear-max" in args:
        i = args.index("--smear-max")
        smear_max = float(args[i + 1])
        del args[i:i + 2]
    if len(args) < 1:
        print("usage: neck_state.py CASE [TIME] [--calm-max U] [--smear-max F]", file=sys.stderr)
        return 2
    case = Path(args[0])
    if len(args) > 1 and args[1] != "--latest":
        tname = args[1]
    else:
        names = time_dirs(case)
        if not names:
            print(f"{case}: no time directory", file=sys.stderr)
            return 2
        tname = names[-1]
    s = report(case, tname)
    if calm is not None and (s["umax"] > calm or s["smear"] > smear_max):
        print(f"VIOLENT umax={s['umax']:.2f} smear={s['smear']:.3f}")
        return 3
    if calm is not None:
        print("CALM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
