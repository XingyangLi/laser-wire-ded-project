#!/usr/bin/env python3
"""Depth and flow of the open neck column.

Reads two times on a decomposed case. Reports whether gas inside the wire
radius used to be metal, and whether that gas is hot recoil, a beam deposit,
or a downward stream.

    column_flow.py CASE EARLIER LATER
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neck_state as ns  # noqa: E402

WIRE_R = 0.5e-3


def gather(case, tname):
    case = Path(case)
    procs = sorted(case.glob("processor*"))
    if not procs:
        raise SystemExit(f"{case}: not decomposed")
    cc, alpha, vel, temp = [], [], [], []
    extra = {"pRecoil": [], "Qheat": [], "cWire": [], "dSigmadTField": []}
    have = {k: True for k in extra}
    for proc in procs:
        c = ns.cell_centres(proc / "constant" / "polyMesh")
        a = ns.read_internal(proc / tname / "alpha.metal", "scalar")
        u = ns.read_internal(proc / tname / "U", "vector")
        T = ns.read_internal(proc / tname / "T", "scalar")
        if a is None or u is None or T is None:
            raise SystemExit(f"{proc.name}/{tname}: alpha, U or T missing")
        cc.append(c)
        alpha.append(a)
        vel.append(u)
        temp.append(T)
        for key in extra:
            v = ns.read_internal(proc / tname / key, "scalar")
            if v is None:
                have[key] = False
            else:
                extra[key].append(v)
    out = {
        "cc": np.vstack(cc),
        "alpha": np.concatenate(alpha),
        "U": np.vstack(vel),
        "T": np.concatenate(temp),
    }
    for key, ok in have.items():
        out[key] = np.concatenate(extra[key]) if ok else None
    return out


def open_depth(rows, min_width=0.15e-3):
    chosen = [(z, w) for z, _x, w, ok in rows if w is not None and w >= min_width and not ok]
    if not chosen:
        return 0.0, None, None
    # Longest consecutive run. Depth is the z span, including a single bin as dz.
    best = 0.0
    best_span = (chosen[0][0], chosen[0][0])
    run0 = chosen[0][0]
    prev = chosen[0][0]
    for z, _w in chosen[1:]:
        if z - prev > 0.05e-3:
            run0 = z
        span = z - run0
        if span >= best:
            best = span
            best_span = (run0, z)
        prev = z
    if best == 0.0:
        best = 0.04e-3
    return best, best_span[0], best_span[1]


def stats(name, mask, U, T, p_recoil, qheat):
    n = int(mask.sum())
    if n == 0:
        print(f"  {name}: none")
        return
    uu = U[mask]
    um = np.linalg.norm(uu, axis=1)
    line = (
        f"  {name}: n={n}  |U| med {np.median(um):.2f} max {um.max():.2f}"
        f"  Umean ({uu[:, 0].mean():+.2f}, {uu[:, 1].mean():+.2f}, {uu[:, 2].mean():+.2f}) m/s"
        f"  T med {np.median(T[mask]):.0f} max {T[mask].max():.0f}"
    )
    if p_recoil is not None:
        pr = p_recoil[mask]
        line += f"  pRecoil med {np.median(pr):.0f} max {pr.max():.0f} Pa"
    if qheat is not None:
        q = qheat[mask]
        line += f"  Qheat med {np.median(q):.2e} max {q.max():.2e}"
    down = float((uu[:, 2] < -0.2).mean())
    into = float((uu[:, 0] < -0.2).mean())
    line += f"  frac Uz<-0.2 {down:.2f}  frac Ux<-0.2 {into:.2f}"
    print(line)


def report(case, t0, t1):
    a = gather(case, t0)
    b = gather(case, t1)
    if len(a["alpha"]) != len(b["alpha"]):
        raise SystemExit("the two times do not share a mesh")
    cc = b["cc"]
    x, y, z = cc[:, 0], cc[:, 1], cc[:, 2]
    radius = np.sqrt(x * x + y * y)
    print(f"\n{case}  {t0} -> {t1}")
    rows = ns.film_rows(cc, b["alpha"])
    depth, zlo, zhi = open_depth(rows)
    closed = [(z, w) for z, _x0, w, ok in rows if ok and w is not None and 0.03e-3 <= w <= 0.08e-3]
    print(
        f"  open column depth {depth * 1e3:.2f} mm"
        + (f"  z {zlo * 1e3:.2f}-{zhi * 1e3:.2f} mm" if zlo is not None else "")
        + f"  thin closed bins {len(closed)}"
    )
    for zz, x0, w, ok in rows:
        if w is None or w < 0.05e-3:
            continue
        print(
            f"  z={zz * 1e3:5.2f}  gas_x0={x0 * 1e3:.3f}  width={w * 1e3:.3f}"
            f"  {'closed' if ok else 'open'}"
        )
    centre = (np.abs(y) < 8e-5) & (z > 0.40e-3) & (z < 1.55e-3) & (x > 0.15e-3) & (x < 1.3e-3)
    inside = centre & (radius < WIRE_R - 2e-5)
    gas1 = b["alpha"] < 0.5
    metal0 = a["alpha"] >= 0.5
    eaten = inside & metal0 & gas1
    still = inside & metal0 & (b["alpha"] >= 0.5)
    column = centre & gas1 & (x < 1.1e-3)
    outside = column & (radius > WIRE_R + 2e-5)
    print(
        f"  centre-plane metal->gas inside the wire: {int(eaten.sum())}"
        f"  still metal there: {int(still.sum())}"
    )
    if eaten.any():
        print(
            f"  eaten z {z[eaten].min() * 1e3:.2f}-{z[eaten].max() * 1e3:.2f} mm"
            f"  x {x[eaten].min() * 1e3:.3f}-{x[eaten].max() * 1e3:.3f} mm"
        )
    neck = (x > 0.2e-3) & (x < 1.2e-3) & (np.abs(y) < 0.4e-3) & (z > 0.3e-3) & (z < 1.6e-3)
    print(
        f"  neck metal cells {int((neck & metal0).sum())} -> {int((neck & (b['alpha'] >= 0.5)).sum())}"
    )
    stats("eaten wire", eaten, b["U"], b["T"], b["pRecoil"], b["Qheat"])
    stats("gas inside wire", inside & gas1, b["U"], b["T"], b["pRecoil"], b["Qheat"])
    stats("gas outside wire", outside, b["U"], b["T"], b["pRecoil"], b["Qheat"])
    # Hot liquid next to the new gas, where recoil and Marangoni act.
    if eaten.any():
        from scipy.spatial import cKDTree
        near = np.zeros(len(cc), dtype=bool)
        hits = cKDTree(cc[eaten]).query_ball_point(cc, 4e-5, workers=4)
        near = np.fromiter((len(js) > 0 for js in hits), dtype=bool, count=len(cc))
        liquid = near & (b["alpha"] >= 0.5) & ~eaten
        stats("liquid beside eaten cells", liquid, b["U"], b["T"], b["pRecoil"], b["Qheat"])
    if b["dSigmadTField"] is not None and column.any():
        dsig = b["dSigmadTField"][column]
        print(
            f"  dSigmadT on column gas: med {np.median(dsig):.3e}"
            f"  frac<0 {(dsig < 0).mean():.2f}"
        )


def main():
    if len(sys.argv) != 4:
        print("usage: column_flow.py CASE EARLIER LATER", file=sys.stderr)
        return 2
    report(sys.argv[1], sys.argv[2], sys.argv[3])
    return 0


if __name__ == "__main__":
    sys.exit(main())
