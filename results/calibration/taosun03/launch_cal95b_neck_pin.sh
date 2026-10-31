#!/bin/bash
# Unpainted hard pin on the cal95b bead, with a 19 um neck.
#
# The bead is taosun01's equal-power checkpoint (247 W x 3, trailing crest
# 1.76 mm at 0.8 s). This is the metal-region pin: trailDrag holds a shell
# on the trailing wire face and moves it at the feed. The true-wall cut is
# not used. Nothing is painted.
#
# The neck band is the trailing face only, x just inside the wire to 0.3 mm
# of gas, |y| < 0.35 mm, z = 0.45-1.55 mm, halved three times (~19 um).
# The rest of the mesh stays at 150 um. Feed 24 mm/s. The window is 6 ms.
#
#   ./launch_cal95b_neck_pin.sh
#
# Four ranks, nice 10, inside the 32-core cap.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal95b_neck_pin_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
ROOT="$TAO_ROOT"
SRC="${CAL95B_SRC:-/tmp/results/calibration/checkpoints/cal95b}"
CASE="$ROOT/cases/wire_cavity_cal95b_neck"
MAP_TIME=0.8
END_TIME=0.806
NP=4
if [[ ! -f "$SRC/$MAP_TIME/alpha.metal" ]]; then
    echo "cal95b checkpoint is missing: $SRC/$MAP_TIME" >&2
    exit 1
fi
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build

if [[ "${RESUME:-0}" == 1 ]]; then
    echo "RESUME from the existing neck mesh in $CASE"
else
echo "GENERATE neck mesh from the cal95b recipe"
python3 "$ROOT/generate_case.py" --case "$CASE" --laser-config triple \
    --wire-type solid --material 316L --resolution coarse --domain-y half \
    --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
    --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
    --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0.05 \
    --scan-speed 0.004 --wire-feed-speed 0.024 \
    --beam-azimuths 60,-60,180 \
    --beam-inclinations=-15,-15,-15 \
    --beam-powers 246.6667,246.6667,246.6666 \
    --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
    --beam-aim-radii 0.604e-3,0.604e-3,0.604e-3 \
    --beam-aim-heights 0.20e-3,0.20e-3,0.20e-3 \
    --end-time "$END_TIME" --write-interval 0.002 --np "$NP" \
    --laser-ramp 2e-3 \
    --neck-refine 3 --capillary-dt-factor 3 \
    --contact-pinning --pin-wire --porosity --wire-cavity \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 30 --theta-advancing-wire 90 \
    --contact-force-factor 6 \
    --no-marangoni \
    --wire-pin-frame head \
    --rigid-substrate 100

python3 - "$CASE" <<'PY'
from pathlib import Path
import re
p = Path(__import__("sys").argv[1]) / "constant/meltProperties"
t = p.read_text()
if "trailDrag" in t:
    raise SystemExit("trailDrag already present")
t += """
trailDrag   // unpainted metal-region pin on the cal95b bead
// Wet shell below the moving line, dry face above it.
// Pool outside the shell is free. No painted film.
{
    enabled         true;
    radialCells     3;
    axialCells      3;
    sectorDeg       75;
}
"""
p.write_text(t)
print("trailDrag on, 3 x 3 cells, 75 deg, unpainted")
PY

if ! grep -q "limited corrected 0.5" "$CASE/system/fvSchemes"; then
    echo "neck schemes were not written" >&2
    exit 1
fi

echo "MESH $(date --iso-8601=seconds)"
tao_source_foam
(
    cd "$CASE"
    MESH_ONLY=1 ./Allrun 1
)
grep -E "cells:|Max aspect ratio|Mesh OK|Failed" "$CASE/log.checkMesh" | head -20
if ! grep -q "Mesh OK" "$CASE/log.checkMesh"; then
    echo "checkMesh did not report Mesh OK" >&2
    exit 1
fi
fi

echo "MAP from cal95b t=$MAP_TIME"
cat > "$CASE/system/mapFieldsDict" <<'EOF'
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      mapFieldsDict;
}
patchMap
(
    inletSubstrate inletSubstrate
    inletGas       inletGas
    outlet         outlet
    bottom         bottom
    top            top
    symmetry       symmetry
    side           side
    wireInlet      wireInlet
);
cuttingPatches
(
);
EOF
tao_source_foam
mapFields -case "$CASE" -sourceTime "$MAP_TIME" \
    -mapMethod interpolate "$SRC" > "$CASE/log.mapFields" 2>&1 \
    || { tail -40 "$CASE/log.mapFields" >&2; exit 1; }

python3 - "$CASE" "$MAP_TIME" <<'PY'
import struct, sys
from pathlib import Path
case, tname = Path(sys.argv[1]), sys.argv[2]
src = case / "0"
templates = {
    "U": "U.orig",
    "alpha.metal": "alpha.metal.orig",
    "cWire": "cWire.orig",
    "T": "T",
    "liquidFraction": "liquidFraction",
    "meltHistory": "meltHistory",
    "p_rgh": "p_rgh",
}
orig = case / "0.orig"
for name, tmpl in templates.items():
    mapped = (src / name).read_bytes()
    key = b"boundaryField"
    i = mapped.rfind(key)
    if i < 0:
        sys.exit(f"{name}: no boundaryField after map")
    body = (orig / tmpl).read_text()
    j = body.rfind("boundaryField")
    if j < 0:
        sys.exit(f"{tmpl}: no boundaryField")
    out = mapped[:i] + body[j:].encode()
    out = out.replace(b'location    "0";', f'location    "{tname}";'.encode(), 1)
    (src / name).write_bytes(out)

def scalar_minmax(path):
    data = path.read_bytes()
    key = b"internalField   nonuniform List<scalar>"
    i = data.find(key)
    if i < 0:
        sys.exit(f"{path.name}: expected a nonuniform scalar field")
    rest = data[i + len(key):].lstrip()
    n_str, _, rest = rest.partition(b"\n")
    n = int(n_str.strip())
    if not rest.startswith(b"("):
        sys.exit(f"{path.name}: scalar list is not binary")
    blob = rest[1:1 + n * 8]
    if len(blob) != n * 8:
        sys.exit(f"{path.name}: short scalar list")
    vals = struct.unpack("<" + "d" * n, blob)
    return min(vals), max(vals)

t_lo, t_hi = scalar_minmax(src / "T")
a_lo, a_hi = scalar_minmax(src / "alpha.metal")
print(f"MAPPED T {t_lo:.0f}..{t_hi:.0f} K  alpha {a_lo:.3f}..{a_hi:.3f}")
if t_hi < 1500 or a_hi < 0.9:
    sys.exit("mapped bead is missing metal or a hot pool")
dest = case / tname
if dest.exists():
    import shutil
    shutil.rmtree(dest)
src.rename(dest)
print("time directory", dest)
PY

if ! grep -q "uniformValue table" "$CASE/$MAP_TIME/U"; then
    echo "wire inlet feed table was not restored" >&2
    exit 1
fi

tao_source_foam
foamDictionary "$CASE/system/controlDict" -entry startFrom -set latestTime > /dev/null
foamDictionary "$CASE/system/controlDict" -entry endTime -set "$END_TIME" > /dev/null
foamDictionary "$CASE/system/controlDict" -entry writeInterval -set 0.002 > /dev/null
foamDictionary "$CASE/system/controlDict" -entry deltaT -set 1e-6 > /dev/null
# x-only split so a vertical column stays on one rank
foamDictionary -entry numberOfSubdomains -set "$NP" "$CASE/system/decomposeParDict" > /dev/null
foamDictionary -entry coeffs.n -set "($NP 1 1)" "$CASE/system/decomposeParDict" > /dev/null
(
    cd "$CASE"
    decomposePar -force > log.decomposePar 2>&1
)
echo "SOLVE $(date --iso-8601=seconds) np=$NP end=$END_TIME"
tao_source_foam
(
    cd "$CASE"
    nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
        laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
)
rc=$?
echo "SOLVE_RC $rc"
# Reconstruct the last write for the side view.
tao_source_foam
(
    cd "$CASE"
    latest=$(ls -d processor0/[0-9]* processor0/[0-9].* 2>/dev/null | sed 's#processor0/##' | sort -g | tail -1)
    echo "RECONSTRUCT $latest"
    reconstructPar -time "$latest" > log.reconstructPar 2>&1 || true
)
"$TAO_PY" "$DIR/render_baseline_bead.py" --case "$CASE" \
    --out "$DIR/cal95b_neck_pin_views.png" || true
grep -E 'TrailDrag:|WireSlit:' "$CASE/log.laserWireDEDFoam" | head -5
grep -E 'TrailDrag:|WireSlit:' "$CASE/log.laserWireDEDFoam" | tail -8
echo "CAL95B_NECK_PIN_RC $rc"
exit "$rc"
