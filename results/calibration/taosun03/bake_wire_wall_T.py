#!/usr/bin/env python3
"""Replace wireWall exprFixedValue with the same z-split stored as values.

The expression (z < zHot) ? THot : TCold is re-parsed inside every matrix
update. On the fine neck that stalls the pressure solve. The numbers stay
the imposed hot-zone / cold-shaft split.
"""
import re
import struct
import sys
from pathlib import Path


def read_labellist(data, pos):
    while data[pos] in b" \n\r\t":
        pos += 1
    j = pos
    while 48 <= data[j] <= 57:
        j += 1
    n = int(data[pos:j])
    pos = j
    while data[pos] in b" \n\r\t":
        pos += 1
    if data[pos:pos + 1] != b"(":
        raise RuntimeError("labelList missing '('")
    pos += 1
    if data[pos:pos + 1] == b"\n":
        pos += 1
    labs = struct.unpack_from("<" + "i" * n, data, pos)
    pos += 4 * n
    while data[pos] in b" \n\r\t":
        pos += 1
    if data[pos:pos + 1] != b")":
        raise RuntimeError("labelList missing ')'")
    return labs, pos + 1


def face_centres(mesh):
    faces = (mesh / "faces").read_bytes()
    base = faces.find(b"object      faces;")
    m = re.search(br"\n(\d+)\n\(", faces[base:])
    pos = base + m.start()
    offs, pos = read_labellist(faces, pos)
    elems, _ = read_labellist(faces, pos)
    pts_raw = (mesh / "points").read_bytes()
    base = pts_raw.find(b"object      points;")
    m = re.search(br"\n(\d+)\n\(", pts_raw[base:])
    n = int(m.group(1))
    ppos = base + m.end()
    if pts_raw[ppos:ppos + 1] == b"\n":
        ppos += 1
    pts = struct.unpack_from("<" + "d" * (n * 3), pts_raw, ppos)
    centres = []
    for i in range(len(offs) - 1):
        ids = elems[offs[i]:offs[i + 1]]
        if not ids:
            centres.append((0.0, 0.0, 0.0))
            continue
        cx = cy = cz = 0.0
        for k in ids:
            cx += pts[3 * k]
            cy += pts[3 * k + 1]
            cz += pts[3 * k + 2]
        inv = 1.0 / len(ids)
        centres.append((cx * inv, cy * inv, cz * inv))
    return centres


def wire_span(boundary):
    m = re.search(r"wireWall\s*\{([^}]*)\}", boundary)
    if not m:
        return None
    body = m.group(1)
    nf = re.search(r"nFaces\s+(\d+)", body)
    sf = re.search(r"startFace\s+(\d+)", body)
    if not nf or not sf:
        raise RuntimeError("wireWall patch has no nFaces/startFace")
    return int(sf.group(1)), int(nf.group(1))


def bake_field(tpath, mesh):
    data = tpath.read_bytes()
    m = re.search(br"wireWall\s*\{.*?\n    \}", data, re.S)
    if not m:
        print(f"skip {tpath}: no wireWall")
        return
    block = m.group(0).decode("latin1")
    if "exprFixedValue" not in block and "valueExpr" not in block:
        print(f"skip {tpath}: already stored values")
        return
    em = re.search(
        r"pos\(\)\.z\(\)\s*<\s*([0-9.eE+-]+)\s*\)\s*\?\s*([0-9.eE+-]+)\s*:\s*([0-9.eE+-]+)",
        block,
    )
    if not em:
        raise SystemExit(f"{tpath}: could not read the z split")
    z_hot = float(em.group(1))
    t_hot = float(em.group(2))
    t_cold = float(em.group(3))
    boundary = (mesh / "boundary").read_text(errors="replace")
    span = wire_span(boundary)
    if span is None:
        raise SystemExit(f"{mesh}/boundary has no wireWall")
    start, nfaces = span
    binary = b"format      binary" in data[:1200]
    if nfaces == 0:
        values = b"uniform 1850"
        nhot = ncold = 0
    else:
        centres = face_centres(mesh)
        vals = []
        for i in range(start, start + nfaces):
            vals.append(t_hot if centres[i][2] < z_hot else t_cold)
        nhot = sum(1 for v in vals if v == t_hot)
        ncold = nfaces - nhot
        if binary:
            blob = struct.pack("<" + "d" * nfaces, *vals)
            values = b"nonuniform List<scalar> \n%d\n(%s)" % (nfaces, blob)
        else:
            body = "\n".join(f"{v:.8g}" for v in vals).encode()
            values = b"nonuniform List<scalar>\n%d\n(\n%s\n)" % (nfaces, body)
    new = (
        b"wireWall\n"
        b"    {\n"
        b"        type            fixedValue;\n"
        b"        value           " + values + b";\n"
        b"    }"
    )
    tpath.write_bytes(data[:m.start()] + new + data[m.end():])
    print(f"baked {tpath}: {nfaces} faces, hot {nhot}, cold {ncold}, zHot {z_hot}")


def bake_case(case):
    case = Path(case)
    mesh = case / "constant" / "polyMesh"
    parent = case / "0" / "T"
    if parent.is_file() and (mesh / "faces").is_file():
        bake_field(parent, mesh)
    for proc in sorted(case.glob("processor*")):
        tf = proc / "0" / "T"
        pm = proc / "constant" / "polyMesh"
        if tf.is_file() and (pm / "faces").is_file():
            bake_field(tf, pm)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: bake_wire_wall_T.py CASE [CASE...]")
    for c in sys.argv[1:]:
        bake_case(c)
