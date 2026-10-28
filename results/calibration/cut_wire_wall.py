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

--pin is the drag case. alpha.metal is pinnedAlphaContactAngle (thetaA /
thetaR). U is partialSlip with refValue equal to the feed; the solver sets
valueFraction to no-slip on the trailing contact line. The lower wall is
1850 K up to z = 1.6 mm so the meniscus stays liquid. A wireDrag block is
written into meltProperties.

--oxide-angle implies --pin but does not write wireDrag or linePin. The
clean window on the patch is 10/40. thetaRox 40 and thetaAox 140 are the
covered limits. An oxideAngle block is written; coverage, not a painted
alpha, drives the blend.

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
# Drag cases: the contact has to stay liquid while the line is carried down.
Z_HOT_PIN = 1.6e-3
T_HOT_PIN = 1850
T_COLD = 600
FEED = (0.0, 0.0, -0.02)
# Covered trailing face. The clean window stays 10/40.
THETA_R_OX = 40.0
THETA_A_OX = 140.0


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


def wall_block(field, theta, feed, pin, theta_a, theta_r, oxide=False):
    uz = -abs(feed)
    z_hot = Z_HOT_PIN if pin else Z_HOT
    t_hot = T_HOT_PIN if pin else T_HOT
    if field == "alpha.metal":
        if pin:
            oxide_keys = ""
            if oxide:
                oxide_keys = (
                    f"        thetaAox        {THETA_A_OX:.8g};\n"
                    f"        thetaRox        {THETA_R_OX:.8g};\n"
                )
            body = (
                f"        type            pinnedAlphaContactAngle;\n"
                f"        thetaA          {theta_a:.8g};\n"
                f"        thetaR          {theta_r:.8g};\n"
                f"{oxide_keys}"
                f"        limit           gradient;\n"
                f"        gradient        uniform 0;\n"
                f"        value           uniform 0;"
            )
        else:
            body = (
                f"        type            constantAlphaContactAngle;\n"
                f"        theta0          {theta:g};\n"
                f"        limit           gradient;\n"
                f"        gradient        uniform 0;\n"
                f"        value           uniform 0;"
            )
    elif field == "U":
        if pin:
            body = (
                f"        type            partialSlip;\n"
                f"        refValue        uniform (0 0 {uz:.8g});\n"
                f"        valueFraction   uniform 0;"
            )
        else:
            body = (
                f"        type            fixedValue;\n"
                f"        value           uniform (0 0 {uz:.8g});"
            )
    elif field == "T":
        body = (
            f"        type            exprFixedValue;\n"
            f"        value           uniform {t_hot:g};\n"
            f'        valueExpr       "(pos().z() < {z_hot:.8g}) ? {t_hot:g} : {T_COLD:g}";'
        )
    elif field == "p_rgh":
        body = (
            "        type            fixedFluxPressure;\n"
            "        value           uniform 0;"
        )
    elif field in ("phi", "alphaPhi0.metal"):
        body = (
            "        type            calculated;\n"
            "        value           uniform 0;"
        )
    else:
        body = "        type            zeroGradient;"
    return f"    wireWall\n    {{\n{body}\n    }}"


def replace_field_block(tail, field, theta, feed, pin, theta_a, theta_r, oxide=False):
    span = find_block(tail, "wireWall")
    if span is None:
        raise SystemExit(f"{field}: no wireWall boundary")
    start, end = span
    block = tail[start:end]
    if "\x00" in block or "nonuniform" in block:
        raise SystemExit(
            f"{field}: wireWall value is a binary list; not rewriting it"
        )
    return tail[:start] + wall_block(
        field, theta, feed, pin, theta_a, theta_r, oxide
    ) + tail[end:]


def write_wire_drag(case, theta_a, theta_r):
    path = Path(case) / "constant/meltProperties"
    text = read_text(path)
    span = find_block(text, "wireDrag")
    if span is not None:
        text = text[:span[0]] + text[span[1]:]
    block = (
        "\nwireDrag\n"
        "{\n"
        "    enabled         true;\n"
        f"    thetaReceding   {theta_r:.8g};\n"
        f"    thetaAdvancing  {theta_a:.8g};\n"
        "    Kpin            1e12;\n"
        "    slipFar         0.001;\n"
        "    slipNear        5e-5;\n"
        "    gradMin         0.25;\n"
        "}\n"
    )
    banner = text.rfind("// ************************************************************************* //")
    if banner < 0:
        text = text.rstrip() + "\n" + block
    else:
        text = text[:banner] + block + "\n" + text[banner:]
    path.write_text(text)
    print(f"wireDrag thetaR {theta_r:.8g} thetaA {theta_a:.8g}")


def write_oxide_angle(case):
    """Coverage law. wireDrag and linePin stay off."""
    path = Path(case) / "constant/meltProperties"
    text = read_text(path)
    for name in ("wireDrag", "linePin", "oxideAngle"):
        span = find_block(text, name)
        if span is not None:
            text = text[:span[0]] + text[span[1]:]
    block = (
        "\noxideAngle\n"
        "{\n"
        "    enabled         true;\n"
        "    nCells          3;\n"
        "    tau             0.001;\n"
        "    ppmRef          300;\n"
        "    sigmaDrop       0.5;\n"
        "    sigmaFloor      0.1;\n"
        "    zMin            0.0003;\n"
        "}\n"
    )
    banner = text.rfind("// ************************************************************************* //")
    if banner < 0:
        text = text.rstrip() + "\n" + block
    else:
        text = text[:banner] + block + "\n" + text[banner:]
    path.write_text(text)
    print("oxideAngle enabled, 3 cells, ppmRef 300, sigmaDrop 0.5")


def write_line_pin(case):
    """Imposed material point. wireDrag stays off so it does not fight the shell."""
    path = Path(case) / "constant/meltProperties"
    text = read_text(path)
    for name in ("wireDrag", "linePin"):
        span = find_block(text, name)
        if span is not None:
            text = text[:span[0]] + text[span[1]:]
    block = (
        "\nlinePin\n"
        "{\n"
        "    enabled         true;\n"
        "    nCells          2;\n"
        "    ppmRef          300;\n"
        "    Kpin            1e12;\n"
        "    tau             0.0005;\n"
        "}\n"
    )
    banner = text.rfind("// ************************************************************************* //")
    if banner < 0:
        text = text.rstrip() + "\n" + block
    else:
        text = text[:banner] + block + "\n" + text[banner:]
    path.write_text(text)
    print("linePin enabled, 2 cells, ppmRef 300")


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


def apply_bcs(case, theta, feed, pin, theta_a, theta_r, line_pin=False, oxide=False):
    case = Path(case)
    boundary = case / "constant/polyMesh/boundary"
    text = read_text(boundary)
    text, n_wall = set_type(text, "wireWall", "wall", "wall")
    if n_wall < 200:
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
    if pin:
        print(
            f"wireWall type wall, {n_wall} faces, "
            f"pinned {theta_r:.8g}/{theta_a:.8g} deg, feed {feed:.8g}"
        )
        if oxide:
            write_oxide_angle(case)
        elif line_pin:
            write_line_pin(case)
        else:
            write_wire_drag(case, theta_a, theta_r)
    else:
        print(f"wireWall type wall, {n_wall} faces, theta0 {theta:g} deg")

    for path in field_files(case):
        head, tail = split_boundary(load_field(path), path)
        if dropped and "wireInlet" in tail:
            tail, _ = drop_block(tail, "wireInlet")
        tail = replace_field_block(
            tail, path.name, theta, feed, pin, theta_a, theta_r, oxide
        )
        save_field(path, head + tail)
        print(f"  {path.name}: wireWall set")


def check(case, theta, feed, pin, theta_a, theta_r, line_pin=False, oxide=False):
    case = Path(case)
    boundary = read_text(case / "constant/polyMesh/boundary")
    span = find_block(boundary, "wireWall")
    if span is None:
        raise SystemExit("wireWall missing")
    block = boundary[span[0]:span[1]]
    if not re.search(r"type\s+wall;", block):
        raise SystemExit("wireWall is not type wall")
    n_wall = nfaces(block)
    if n_wall < 200:
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
    ub = wall_body("U")
    tb = wall_body("T")
    uz = f"{-abs(feed):.8g}"
    if pin:
        if "pinnedAlphaContactAngle" not in ab:
            raise SystemExit("alpha.metal wireWall is not pinnedAlphaContactAngle")
        if not re.search(rf"thetaA\s+{theta_a:.8g}\s*;", ab):
            raise SystemExit(f"thetaA is not {theta_a:.8g} in alpha.metal")
        if not re.search(rf"thetaR\s+{theta_r:.8g}\s*;", ab):
            raise SystemExit(f"thetaR is not {theta_r:.8g} in alpha.metal")
        if "partialSlip" not in ub or uz not in ub:
            raise SystemExit(f"U wireWall is not partialSlip at the feed: {ub}")
        if "exprFixedValue" not in tb or "1850" not in tb:
            raise SystemExit("T wireWall is not the liquid hot zone")
        props = read_text(case / "constant/meltProperties")
        if oxide:
            if not re.search(rf"thetaAox\s+{THETA_A_OX:.8g}\s*;", ab):
                raise SystemExit("thetaAox is missing from alpha.metal")
            if not re.search(rf"thetaRox\s+{THETA_R_OX:.8g}\s*;", ab):
                raise SystemExit("thetaRox is missing from alpha.metal")
            ox_span = find_block(props, "oxideAngle")
            if ox_span is None:
                raise SystemExit("meltProperties has no oxideAngle block")
            ox_body = props[ox_span[0]:ox_span[1]]
            if not re.search(r"enabled\s+true;", ox_body):
                raise SystemExit("oxideAngle is not enabled")
            if not re.search(r"nCells\s+3\s*;", ox_body):
                raise SystemExit("oxideAngle nCells is not 3")
            if not re.search(r"sigmaDrop\s+0\.5\s*;", ox_body):
                raise SystemExit("oxideAngle sigmaDrop is not 0.5")
            for name in ("linePin", "wireDrag"):
                span = find_block(props, name)
                if span is not None and re.search(
                    r"enabled\s+true;", props[span[0]:span[1]]
                ):
                    raise SystemExit(f"{name} is enabled next to oxideAngle")
        elif line_pin:
            pin_span = find_block(props, "linePin")
            if pin_span is None:
                raise SystemExit("meltProperties has no linePin block")
            pin_body = props[pin_span[0]:pin_span[1]]
            if not re.search(r"enabled\s+true;", pin_body):
                raise SystemExit("linePin is not enabled")
            if not re.search(r"nCells\s+2\s*;", pin_body):
                raise SystemExit("linePin nCells is not 2")
            drag_span = find_block(props, "wireDrag")
            if drag_span is not None and re.search(
                r"enabled\s+true;", props[drag_span[0]:drag_span[1]]
            ):
                raise SystemExit("wireDrag is enabled next to linePin")
        else:
            drag_span = find_block(props, "wireDrag")
            if drag_span is None:
                raise SystemExit("meltProperties has no wireDrag block")
            drag_body = props[drag_span[0]:drag_span[1]]
            if not re.search(r"enabled\s+true;", drag_body):
                raise SystemExit("wireDrag is not enabled")
            if not re.search(rf"thetaReceding\s+{theta_r:.8g}\s*;", drag_body):
                raise SystemExit("wireDrag thetaReceding does not match the wall")
            if not re.search(rf"thetaAdvancing\s+{theta_a:.8g}\s*;", drag_body):
                raise SystemExit("wireDrag thetaAdvancing does not match the wall")
    else:
        if "constantAlphaContactAngle" not in ab:
            raise SystemExit("alpha.metal wireWall is not constantAlphaContactAngle")
        if not re.search(rf"theta0\s+{theta:g}\s*;", ab):
            raise SystemExit(f"theta0 is not {theta:g} in alpha.metal")
        if "fixedValue" not in ub or uz not in ub:
            raise SystemExit(f"U wireWall is not the feed velocity: {ub}")
        if "exprFixedValue" not in tb or "1700" not in tb:
            raise SystemExit("T wireWall is not the lower-end temperature")
    if "limit" not in ab or "gradient" not in ab:
        raise SystemExit("contact-angle limit is missing")

    pb = wall_body("p_rgh")
    if "fixedFluxPressure" not in pb:
        raise SystemExit("p_rgh wireWall is not fixedFluxPressure")
    if pin:
        print(
            f"check ok: wall {n_wall} faces, "
            f"pinned {theta_r:.8g}/{theta_a:.8g}, feed {uz}"
        )
    else:
        print(f"check ok: wall {n_wall} faces, theta0 {theta:g}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--theta", type=float, default=140.0)
    ap.add_argument("--feed", type=float, default=0.02,
                    help="wire feed speed [m/s], downward")
    ap.add_argument("--pin", action="store_true",
                    help="hysteresis angle and partial-slip feed velocity")
    ap.add_argument("--line-pin", action="store_true",
                    help="imposed trailing contact that moves at the feed")
    ap.add_argument("--oxide-angle", action="store_true",
                    help="trailing oxide coverage sets angle, sigma and slip")
    ap.add_argument("--theta-a", type=float, default=140.0)
    ap.add_argument("--theta-r", type=float, default=40.0)
    ap.add_argument("--write-dict", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not (args.write_dict or args.apply or args.check):
        raise SystemExit("pass --write-dict, --apply or --check")
    if args.oxide_angle and args.line_pin:
        raise SystemExit("oxide-angle and line-pin are different tests")
    if args.oxide_angle:
        args.pin = True
        args.theta_r = 10.0
        args.theta_a = 40.0
    if args.line_pin:
        args.pin = True
    if args.pin and args.theta_a < args.theta_r:
        raise SystemExit("thetaA is below thetaR")
    if args.write_dict:
        write_dict(args.case)
    if args.apply:
        apply_bcs(
            args.case, args.theta, args.feed, args.pin,
            args.theta_a, args.theta_r, args.line_pin, args.oxide_angle,
        )
    if args.check or args.apply:
        check(
            args.case, args.theta, args.feed, args.pin,
            args.theta_a, args.theta_r, args.line_pin, args.oxide_angle,
        )


if __name__ == "__main__":
    main()
