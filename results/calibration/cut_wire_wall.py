#!/usr/bin/env python3
"""Cut the vertical wire out of a generated case and give it a wall.

subsetMesh keeps every cell outside a cylinder of the wire radius, from just
above the plate to above the gas cap. The exposed faces are the patch
wireWall. OpenFOAM creates that patch as type empty; this script turns it
into a wall and writes the boundary conditions.

alpha.metal uses constantAlphaContactAngle (theta0 in degrees, the angle
through the metal). U is fixedValue at the feed velocity: the mesh does not
move, so movingWallVelocity would be zero. T is near the 316L liquidus on
the lower end and cold above the slit. p_rgh is fixedFluxPressure, which is
what a gradient contact-angle condition needs. Other fields are zeroGradient.

An empty wireInlet (every inlet face belonged to a removed cell) is dropped.
"""
import argparse
import re
from pathlib import Path

WIRE_R = 5.0e-4
Z_LO = 5.0e-5
Z_HI = 1.0e-2
# Lower end covers the painted slit (tip 0.75 mm, mouth 1.20 mm).
Z_HOT = 1.35e-3
T_HOT = 1700
T_COLD = 600
FEED = (0.0, 0.0, -0.02)


def foam_dict(body):
    return (
        "FoamFile\n{\n    version     2.0;\n    format      ascii;\n"
        "    class       dictionary;\n    object      topoSetDict.wireCut;\n}\n"
        "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n\n"
        + body
        + "\n// ************************************************************************* //\n"
    )


def write_dict(case):
    path = Path(case) / "system/topoSetDict.wireCut"
    # subsetMesh keeps the cellSet. Subtract the wire so the kept cells are
    # the pool, the plate and the gas. point1 starts above the plate so the
    # substrate is not cut; the lower end of the hole is a blunt wall cap.
    body = f"""actions
(
    {{
        name    keepCells;
        type    cellSet;
        action  new;
        source  boxToCell;
        box     (-1 -1 -1) (1 1 1);
    }}
    {{
        name    keepCells;
        type    cellSet;
        action  subtract;
        source  cylinderToCell;
        point1  (0 0 {Z_LO:.8g});
        point2  (0 0 {Z_HI:.8g});
        radius  {WIRE_R:.8g};
    }}
);
"""
    path.write_text(foam_dict(body))
    print(f"wrote {path}")


def find_block(text, name):
    m = re.search(rf"(?m)^([ \t]*){re.escape(name)}[ \t]*\n[ \t]*\{{", text)
    if not m:
        m = re.search(rf"(?m)^([ \t]*){re.escape(name)}[ \t]*\{{", text)
    if not m:
        return None
    start = m.start()
    i = text.find("{", start)
    depth = 0
    for j in range(i, len(text)):
        c = text[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return start, j + 1
    raise SystemExit(f"unclosed block {name}")


def read_text(path):
    """Text dictionaries. Mesh and volume fields may be binary; those use load_field."""
    data = Path(path).read_bytes()
    if b"\x00" in data:
        raise SystemExit(f"{path} is binary")
    return data.decode("utf-8")


def load_field(path):
    """Volume fields stay binary after subsetMesh. The boundary dictionary is ASCII."""
    return Path(path).read_bytes().decode("latin-1")


def save_field(path, text):
    Path(path).write_bytes(text.encode("latin-1"))


def split_boundary(text, path):
    i = text.find("boundaryField")
    if i < 0:
        raise SystemExit(f"no boundaryField in {path}")
    return text[:i], text[i:]


def nfaces(block):
    m = re.search(r"nFaces\s+(\d+)\s*;", block)
    if not m:
        raise SystemExit("patch block has no nFaces")
    return int(m.group(1))


def set_type(text, name, ptype, group):
    span = find_block(text, name)
    if span is None:
        raise SystemExit(f"patch {name} not in boundary file")
    start, end = span
    block = text[start:end]
    if not re.search(r"type\s+\S+;", block):
        raise SystemExit(f"patch {name} has no type")
    block = re.sub(r"type\s+\S+;", f"type            {ptype};", block, count=1)
    groups = f"inGroups        1({group});"
    if re.search(r"inGroups\s+", block):
        block = re.sub(r"inGroups\s+[^;]+;", groups, block, count=1)
    else:
        block = block.replace(
            f"type            {ptype};",
            f"type            {ptype};\n        {groups}",
            1,
        )
    return text[:start] + block + text[end:], nfaces(block)


def drop_block(text, name):
    span = find_block(text, name)
    if span is None:
        return text, False
    start, end = span
    # Eat one leading newline so a removed patch does not leave a blank hole
    # that still parses, and so the following patch stays indented.
    if start > 0 and text[start - 1] == "\n":
        start -= 1
    return text[:start] + text[end:], True


def drop_empty_inlet(text):
    span = find_block(text, "wireInlet")
    if span is None:
        return text, False
    if nfaces(text[span[0]:span[1]]) != 0:
        return text, False
    text, removed = drop_block(text, "wireInlet")
    if not removed:
        return text, False

    def dec(m):
        return f"\n{int(m.group(1)) - 1}\n("

    text, n = re.subn(r"\n(\d+)\n\(", dec, text, count=1)
    if n != 1:
        raise SystemExit("could not decrement the boundary patch count")
    return text, True


def wall_block(field, theta):
    ux, uy, uz = FEED
    if field == "alpha.metal":
        body = (
            f"        type            constantAlphaContactAngle;\n"
            f"        theta0          {theta:g};\n"
            f"        limit           gradient;\n"
            f"        gradient        uniform 0;\n"
            f"        value           uniform 0;"
        )
    elif field == "U":
        body = (
            f"        type            fixedValue;\n"
            f"        value           uniform ({ux:.8g} {uy:.8g} {uz:.8g});"
        )
    elif field == "T":
        body = (
            f"        type            exprFixedValue;\n"
            f"        value           uniform {T_HOT:g};\n"
            f'        valueExpr       "(pos().z() < {Z_HOT:.8g}) ? {T_HOT:g} : {T_COLD:g}";'
        )
    elif field == "p_rgh":
        body = (
            "        type            fixedFluxPressure;\n"
            "        value           uniform 0;"
        )
    else:
        body = "        type            zeroGradient;"
    return f"    wireWall\n    {{\n{body}\n    }}"


def replace_field_block(tail, field, theta):
    span = find_block(tail, "wireWall")
    if span is None:
        raise SystemExit(f"{field}: no wireWall boundary")
    start, end = span
    block = tail[start:end]
    if "\x00" in block or "nonuniform" in block:
        raise SystemExit(
            f"{field}: wireWall value is a binary list; not rewriting it"
        )
    return tail[:start] + wall_block(field, theta) + tail[end:]


def field_files(case):
    root = Path(case) / "0"
    files = []
    for p in sorted(root.iterdir()):
        if not p.is_file():
            continue
        if p.suffix == ".orig" or p.name.startswith("."):
            continue
        files.append(p)
    if not files:
        raise SystemExit(f"no fields in {root}")
    return files


def apply_bcs(case, theta):
    case = Path(case)
    boundary = case / "constant/polyMesh/boundary"
    text = read_text(boundary)
    text, n_wall = set_type(text, "wireWall", "wall", "wall")
    if n_wall < 500:
        raise SystemExit(f"wireWall has only {n_wall} faces")
    sym = find_block(text, "symmetry")
    if sym is None:
        raise SystemExit("symmetry patch missing after subsetMesh")
    sym_body = text[sym[0]:sym[1]]
    if not re.search(r"type\s+symmetryPlane;", sym_body):
        text, _ = set_type(text, "symmetry", "symmetryPlane", "symmetryPlane")
        print("restored symmetry type symmetryPlane")
    else:
        print("symmetry stayed symmetryPlane")
    text, dropped = drop_empty_inlet(text)
    if dropped:
        print("dropped empty wireInlet")
    boundary.write_text(text)
    print(f"wireWall type wall, {n_wall} faces, theta0 {theta:g} deg")

    for path in field_files(case):
        head, tail = split_boundary(load_field(path), path)
        if dropped and "wireInlet" in tail:
            tail, _ = drop_block(tail, "wireInlet")
        tail = replace_field_block(tail, path.name, theta)
        save_field(path, head + tail)
        print(f"  {path.name}: wireWall set")


def check(case, theta):
    case = Path(case)
    boundary = read_text(case / "constant/polyMesh/boundary")
    span = find_block(boundary, "wireWall")
    if span is None:
        raise SystemExit("wireWall missing")
    block = boundary[span[0]:span[1]]
    if not re.search(r"type\s+wall;", block):
        raise SystemExit("wireWall is not type wall")
    n_wall = nfaces(block)
    if n_wall < 500:
        raise SystemExit(f"wireWall has only {n_wall} faces")
    sym = find_block(boundary, "symmetry")
    if sym is None or not re.search(r"type\s+symmetryPlane;", boundary[sym[0]:sym[1]]):
        raise SystemExit("symmetry is not symmetryPlane")
    inlet = find_block(boundary, "wireInlet")
    if inlet is not None and nfaces(boundary[inlet[0]:inlet[1]]) == 0:
        raise SystemExit("empty wireInlet is still in the mesh")

    def wall_body(name):
        _head, tail = split_boundary(load_field(case / "0" / name), name)
        span = find_block(tail, "wireWall")
        if span is None:
            raise SystemExit(f"{name} has no wireWall")
        return tail[span[0]:span[1]]

    ab = wall_body("alpha.metal")
    if "constantAlphaContactAngle" not in ab:
        raise SystemExit("alpha.metal wireWall is not constantAlphaContactAngle")
    if not re.search(rf"theta0\s+{theta:g}\s*;", ab):
        raise SystemExit(f"theta0 is not {theta:g} in alpha.metal")
    if "limit" not in ab or "gradient" not in ab:
        raise SystemExit("contact-angle limit is missing")

    ub = wall_body("U")
    if "fixedValue" not in ub or "-0.02" not in ub:
        raise SystemExit(f"U wireWall is not the feed velocity: {ub}")

    tb = wall_body("T")
    if "exprFixedValue" not in tb or "1700" not in tb:
        raise SystemExit("T wireWall is not the lower-end temperature")

    pb = wall_body("p_rgh")
    if "fixedFluxPressure" not in pb:
        raise SystemExit("p_rgh wireWall is not fixedFluxPressure")
    print(f"check ok: wall {n_wall} faces, theta0 {theta:g}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--theta", type=float, default=140.0)
    ap.add_argument("--write-dict", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not (args.write_dict or args.apply or args.check):
        raise SystemExit("pass --write-dict, --apply or --check")
    if args.write_dict:
        write_dict(args.case)
    if args.apply:
        apply_bcs(args.case, args.theta)
    if args.check or args.apply:
        check(args.case, args.theta)


if __name__ == "__main__":
    main()
