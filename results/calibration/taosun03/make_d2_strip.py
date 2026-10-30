#!/usr/bin/env python3
"""Quasi-2D strip along the trailing wire wall for the dragged-line smoke.

One cell in y (empty front and back). A fine strip sits on the wall
(x = 0.5 mm). The bead is an imposed rectangle of hot metal; the slit
is not painted. dx_um is the fine-strip size.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path("/home/asb6102/laser-wire-ded-project")
SRC = ROOT / "cases/wire_cavity_wall_tip"

X0, X1, X2 = 0.0005, 0.00062, 0.0018
Z0, Z1, Z2, Z3 = 0.0004, 0.00100, 0.00175, 0.00190
Y0, Y1 = 0.0, 5.0e-5
DX_COARSE = 4.0e-5


def n_div(length, dx):
    return max(1, int(round(length / dx)))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def header(cls, obj):
    return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    object      {obj};
}}
"""


def block_mesh(dx):
    nx_f = n_div(X1 - X0, dx)
    nx_c = n_div(X2 - X1, DX_COARSE)
    nz_b = n_div(Z1 - Z0, DX_COARSE)
    nz_f = n_div(Z2 - Z1, dx)
    nz_t = n_div(Z3 - Z2, DX_COARSE)
    xs = (X0, X1, X2)
    zs = (Z0, Z1, Z2, Z3)
    ys = (Y0, Y1)

    def vid(ix, iy, iz):
        return ix + 3 * iy + 6 * iz

    verts = []
    for iz, z in enumerate(zs):
        for iy, y in enumerate(ys):
            for ix, x in enumerate(xs):
                verts.append(f"    ({x:.8g} {y:.8g} {z:.8g})")
    blocks = []
    nxy = [(nx_f, nz_b), (nx_c, nz_b), (nx_f, nz_f), (nx_c, nz_f), (nx_f, nz_t), (nx_c, nz_t)]
    k = 0
    cells = 0
    for iz in range(3):
        for ix in range(2):
            nx, nz = nxy[k]
            k += 1
            cells += nx * nz
            v = [
                vid(ix, 0, iz), vid(ix + 1, 0, iz), vid(ix + 1, 1, iz), vid(ix, 1, iz),
                vid(ix, 0, iz + 1), vid(ix + 1, 0, iz + 1), vid(ix + 1, 1, iz + 1), vid(ix, 1, iz + 1),
            ]
            blocks.append(f"    hex ({' '.join(str(i) for i in v)}) ({nx} 1 {nz}) simpleGrading (1 1 1)")

    def xfaces(ix, izs, left):
        # Out of the domain: -x on the wall, +x on the outlet.
        out = []
        for iz in izs:
            if left:
                quad = (vid(ix, 0, iz), vid(ix, 0, iz + 1), vid(ix, 1, iz + 1), vid(ix, 1, iz))
            else:
                quad = (vid(ix, 0, iz), vid(ix, 1, iz), vid(ix, 1, iz + 1), vid(ix, 0, iz + 1))
            out.append("            (" + " ".join(str(i) for i in quad) + ")")
        return "\n".join(out)

    def zfaces(iz, ixs, bottom):
        out = []
        for ix in ixs:
            if bottom:
                quad = (vid(ix, 0, iz), vid(ix, 1, iz), vid(ix + 1, 1, iz), vid(ix + 1, 0, iz))
            else:
                quad = (vid(ix, 0, iz), vid(ix + 1, 0, iz), vid(ix + 1, 1, iz), vid(ix, 1, iz))
            out.append("            (" + " ".join(str(i) for i in quad) + ")")
        return "\n".join(out)

    def empty_faces():
        # y = 0 points out as -y, y = 1 as +y.
        out = []
        for iz in range(3):
            for ix in range(2):
                out.append(
                    "            ("
                    + " ".join(str(i) for i in (
                        vid(ix, 0, iz), vid(ix + 1, 0, iz), vid(ix + 1, 0, iz + 1), vid(ix, 0, iz + 1)
                    ))
                    + ")"
                )
                out.append(
                    "            ("
                    + " ".join(str(i) for i in (
                        vid(ix, 1, iz), vid(ix, 1, iz + 1), vid(ix + 1, 1, iz + 1), vid(ix + 1, 1, iz)
                    ))
                    + ")"
                )
        return "\n".join(out)

    txt = header("dictionary", "blockMeshDict")
    txt += f"""
// Fine strip {dx*1e6:.2f} um on the wall, coarse {DX_COARSE*1e6:.0f} um outside. {cells} cells.
scale 1;

vertices
(
{chr(10).join(verts)}
);

blocks
(
{chr(10).join(blocks)}
);

edges
(
);

boundary
(
    wireWall
    {{
        type wall;
        faces
        (
{xfaces(0, range(3), True)}
        );
    }}
    outlet
    {{
        type patch;
        faces
        (
{xfaces(2, range(3), False)}
        );
    }}
    bottom
    {{
        type wall;
        faces
        (
{zfaces(0, range(2), True)}
        );
    }}
    top
    {{
        type patch;
        faces
        (
{zfaces(3, range(2), False)}
        );
    }}
    frontAndBack
    {{
        type empty;
        faces
        (
{empty_faces()}
        );
    }}
);

mergePatchPairs
(
);
"""
    return txt, cells, nx_f, nz_f


def scalar_field(name, dims, internal, bcs):
    body = "\n".join(f"    {k}\n    {{\n{v}\n    }}" for k, v in bcs.items())
    return header("volScalarField", name) + f"""
dimensions      {dims};

internalField   {internal};

boundaryField
{{
{body}
}}
"""


def vector_field(name, internal, bcs):
    body = "\n".join(f"    {k}\n    {{\n{v}\n    }}" for k, v in bcs.items())
    return header("volVectorField", name) + f"""
dimensions      [0 1 -1 0 0 0 0];

internalField   {internal};

boundaryField
{{
{body}
}}
"""


def build(dx_um, end=0.008, np=1, ppm=300, feed_mm=24, thresh=None, tag=None):
    dx = dx_um * 1e-6
    feed = -abs(feed_mm) / 1000.0
    if tag is None:
        tag = f"d2s{dx_um:g}".replace(".", "p")
    case = ROOT / "cases" / f"wire_cavity_{tag}"
    if case.exists():
        shutil.rmtree(case)
    (case / "constant").mkdir(parents=True)
    (case / "system").mkdir()
    (case / "0").mkdir()
    for name in ("g", "transportProperties", "turbulenceProperties", "meltProperties"):
        shutil.copy(SRC / "constant" / name, case / "constant" / name)
    for name in ("fvSchemes", "fvSolution"):
        shutil.copy(SRC / "system" / name, case / "system" / name)
    sol = (case / "system/fvSolution").read_text()
    sol = sol.replace("nAlphaSubCycles 1;", "nAlphaSubCycles 2;")
    (case / "system/fvSolution").write_text(sol)

    mesh, cells, nx_f, nz_f = block_mesh(dx)
    write(case / "system/blockMeshDict", mesh)

    zg = "        type            zeroGradient;"
    empty = "        type            empty;"
    io0 = "        type            inletOutlet;\n        inletValue      uniform 0;\n        value           uniform 0;"
    ioT = "        type            inletOutlet;\n        inletValue      uniform 300;\n        value           uniform 300;"
    bcs_a = {
        "wireWall": zg,
        "outlet": io0,
        "bottom": zg,
        "top": io0,
        "frontAndBack": empty,
    }
    bcs_s = {
        "wireWall": zg,
        "outlet": zg,
        "bottom": zg,
        "top": zg,
        "frontAndBack": empty,
    }
    bcs_T = {
        "wireWall": "        type            fixedValue;\n        value           uniform 1850;",
        "outlet": ioT,
        "bottom": zg,
        "top": ioT,
        "frontAndBack": empty,
    }
    bcs_p = {
        "wireWall": "        type            fixedFluxPressure;\n        value           uniform 0;",
        "outlet": "        type            fixedValue;\n        value           uniform 0;",
        "bottom": "        type            fixedFluxPressure;\n        value           uniform 0;",
        "top": "        type            fixedValue;\n        value           uniform 0;",
        "frontAndBack": empty,
    }
    bcs_U = {
        "wireWall": f"        type            fixedValue;\n        value           uniform (0 0 {feed:.8g});",
        "outlet": "        type            pressureInletOutletVelocity;\n        value           uniform (0 0 0);",
        "bottom": "        type            noSlip;",
        "top": "        type            pressureInletOutletVelocity;\n        value           uniform (0 0 0);",
        "frontAndBack": empty,
    }
    write(case / "0/alpha.metal", scalar_field("alpha.metal", "[0 0 0 0 0 0 0]", "uniform 0", bcs_a))
    write(case / "0/T", scalar_field("T", "[0 0 0 1 0 0 0]", "uniform 300", bcs_T))
    write(case / "0/liquidFraction", scalar_field("liquidFraction", "[0 0 0 0 0 0 0]", "uniform 0", bcs_s))
    write(case / "0/meltHistory", scalar_field("meltHistory", "[0 0 0 0 0 0 0]", "uniform 0", bcs_s))
    write(case / "0/cWire", scalar_field("cWire", "[0 0 0 0 0 0 0]", "uniform 0", bcs_s))
    write(case / "0/p_rgh", scalar_field("p_rgh", "[1 -1 -2 0 0 0 0]", "uniform 0", bcs_p))
    write(case / "0/U", vector_field("U", "uniform (0 0 0)", bcs_U))

    write(case / "system/setFieldsDict", header("dictionary", "setFieldsDict") + """
defaultFieldValues
(
    volScalarFieldValue alpha.metal 0
    volScalarFieldValue T 300
    volScalarFieldValue liquidFraction 0
    volScalarFieldValue meltHistory 0
);

regions
(
    boxToCell
    {
        box (0.0005 -1 0.0004) (0.00125 1 0.00156);
        fieldValues
        (
            volScalarFieldValue alpha.metal 1
            volScalarFieldValue T 2200
            volScalarFieldValue liquidFraction 1
            volScalarFieldValue meltHistory 1
        );
    }
);
""")
    write(case / "system/controlDict", header("dictionary", "controlDict") + f"""
application     laserWireDEDFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {end};
deltaT          1e-7;
writeControl    adjustableRunTime;
writeInterval   0.002;
purgeWrite      0;
writeFormat     ascii;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable yes;
adjustTimeStep  yes;
maxCo           0.4;
maxAlphaCo      0.2;
maxDeltaT       2e-6;
""")
    write(case / "system/decomposeParDict", header("dictionary", "decomposeParDict") + f"""
numberOfSubdomains {np};
method          simple;
coeffs
{{
    n ( {np} 1 1 );
}}
""")
    # slit entry, laser off, planar rays, alloy sigma
    mp = (case / "constant/meltProperties").read_text()
    mp = mp.replace("sigmaScale      1.5;", "sigmaScale      1;")
    mp = mp.replace("planar2D        false;", "planar2D        true;")
    mp = mp.replace("symmetryY       true;", "symmetryY       false;")
    # first laser enabled only
    mp = mp.replace(
        "laser\n{\n    enabled         true;",
        "laser\n{\n    enabled         false;",
        1,
    )
    mp = mp.replace("recoil          true;", "recoil          false;", 1)
    mp = mp.replace("feedVelocity    ( 0 0 -0.024 );", f"feedVelocity    ( 0 0 {feed:.8g} );")
    if "\nslitEntry\n" not in mp:
        mp = mp.rstrip() + """

wireSlide
{
    enabled         false;
}

oxideSkin
{
    enabled         false;
}

slitEntry
{
    enabled         true;
    ppm             {ppm};
    depthSpan       0.00035;
    // Imposed. The pinned line moves at the feed from the generated crest.
    // Gas enters only after the line is this far below that crest.
    // Columns: ppm threshold[m] entryRate[m/s] gapMouth[m] gapRoot[m]
    oxygenTable
    (
        (50  1.2e-4  0.012  4.5e-5  3.0e-5)
        (100 8.0e-5  0.020  5.5e-5  3.2e-5)
        (300 {4.0e-5 if thresh is None else thresh:.8g}  0.040  6.5e-5  3.5e-5)
    );
}
"""
    th = 4.0e-5 if thresh is None else thresh
    mp = mp.replace("ppm             {ppm};", f"ppm             {ppm};")
    mp = mp.replace(
        "(300 {4.0e-5 if thresh is None else thresh:.8g}  0.040  6.5e-5  3.5e-5)",
        f"(300 {th:.8g}  0.040  6.5e-5  3.5e-5)",
    )
    (case / "constant/meltProperties").write_text(mp)
    print(f"{tag} cells~{cells} fine {nx_f} x {nz_f} dx {dx_um} um -> {case}")
    return case


if __name__ == "__main__":
    dx = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    end = float(sys.argv[2]) if len(sys.argv) > 2 else 0.008
    np = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    ppm = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    feed_mm = float(sys.argv[5]) if len(sys.argv) > 5 else 24.0
    thresh = float(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] else None
    tag = sys.argv[7] if len(sys.argv) > 7 else None
    build(dx, end, np, ppm, feed_mm, thresh, tag)
