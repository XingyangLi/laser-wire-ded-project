#!/bin/bash
# Restart from the cal95b checkpoint, refine a thin trailing band to ~19 um,
# cut the wire into a true wall, and impose the feed-following line.
# The rest of the mesh stays at 150 um. Nothing is painted.
#
#   FINE_TAG    case tag (default cal105)
#   FINE_FEED   wire feed [m/s] (default 0.024)
#   FINE_END    pin window [s] (default 0.006)
#   FINE_NP     ranks (default 12)
#   FINE_PARALLEL / FINE_SKIP_BUILD
#
# Inner band: x 0.42-0.85 mm, y 0-0.30 mm, z 0.45-1.55 mm.
# Three halving passes, each padded so the jump is 2:1.
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
SRC=${FINE_SRC:-$ROOT/results/calibration/checkpoints/cal95b}
TAG=${FINE_TAG:-cal105}
FEED=${FINE_FEED:-0.024}
END=${FINE_END:-0.006}
NP=${FINE_NP:-12}
exec > >(tee -a "$ROOT/results/calibration/pin_fine_${TAG}.log") 2>&1
if [ "${FINE_PARALLEL:-0}" != 1 ] && ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
    echo "a solver is already running" >&2
    exit 1
fi
set +e
set +u
set +o pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -e
set -u
set -o pipefail
export PATH="${FOAM_USER_APPBIN}:$PATH"
hash -r
if [ "${FINE_SKIP_BUILD:-0}" != 1 ]; then
    (cd "$ROOT/solver" && ./Allwmake)
fi

case="$ROOT/cases/wire_cavity_${TAG}"
echo "=== fine-neck pin ${TAG}: feed ${FEED}, end ${END}, np ${NP} ==="
rm -rf "$case"
mkdir -p "$case"
cp -a "$SRC/constant" "$SRC/system" "$SRC/0.8" "$case/"
# Surface fluxes are rebuilt from U. refineMesh maps the volume fields.
rm -f "$case/0.8/phi" "$case/0.8/alphaPhi0.metal"
cd "$case"

write_topo() {
    local level=$1 x0=$2 x1=$3 y0=$4 y1=$5 z0=$6 z1=$7
    cat > "system/topoSetDict.neck${level}" << EOF
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      topoSetDict.neck${level};
}
actions
(
    {
        name    neckBox;
        type    cellSet;
        action  new;
        source  boxToCell;
        box     (${x0} ${y0} ${z0}) (${x1} ${y1} ${z1});
    }
);
EOF
}
cat > system/refineMeshDict.neck << 'EOF'
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      refineMeshDict.neck;
}
set             neckBox;
coordinateSystem global;
globalCoeffs
{
    tan1        (1 0 0);
    tan2        (0 1 0);
    tan3        (0 0 1);
}
directions      (tan1 tan2 normal);
useHexTopology  no;
geometricCut    no;
writeMesh       no;
EOF
# level 0 is the outer 2:1 shell (pad 0.225 mm), then 0.075 mm, then the core.
write_topo 0  1.95e-4  1.075e-3   -3.25e-4  5.25e-4   2.25e-4  1.775e-3
write_topo 1  3.45e-4  9.25e-4    -1.75e-4  3.75e-4   3.75e-4  1.625e-3
write_topo 2  4.20e-4  8.50e-4    -1.00e-4  3.00e-4   4.50e-4  1.550e-3

for i in 0 1 2; do
    topoSet -dict "system/topoSetDict.neck${i}" > "log.topoSet.neck${i}" 2>&1
    refineMesh -overwrite -dict system/refineMeshDict.neck > "log.refineMesh.neck${i}" 2>&1
    python3 "$ROOT/results/calibration/remap_refined_fields.py" 0.8
    echo "refine pass ${i} done"
done
checkMesh > log.checkMesh 2>&1 || true
grep -E "cells:|Mesh OK|Failed|Min volume" log.checkMesh || true
ls 0.8 | head

python3 "$ROOT/results/calibration/cut_wire_wall.py" --case "$case" --write-dict
topoSet -dict system/topoSetDict.wireCut > log.topoSet.wireCut 2>&1
subsetMesh -overwrite -patch wireWall keepCells > log.subsetMesh 2>&1
# BC rewrite reads 0/. The mapped bead is the only time directory.
if [ -d 0.8 ] && [ ! -d 0 ]; then
    mv 0.8 0
elif [ -d 0.8 ]; then
    rm -rf 0
    mv 0.8 0
fi
python3 "$ROOT/results/calibration/cut_wire_wall.py" \
    --case "$case" --apply --line-pin --feed "$FEED" \
    --theta-a 140 --theta-r 40
python3 - << 'PY'
from pathlib import Path
import re
p = Path("constant/meltProperties")
text = p.read_text()
text2, n = re.subn(r"(pinWire\s+)true", r"\1false", text, count=1)
if n != 1:
    raise SystemExit("pinWire true was not in meltProperties")
p.write_text(text2)
print("pinWire set false")
PY
foamDictionary constant/meltProperties -entry wire/tFeedStart -set 0 > /dev/null
foamDictionary constant/meltProperties -entry wire/feedVelocity -set "(0 0 -$FEED)" > /dev/null
foamDictionary system/controlDict -entry startFrom -set startTime > /dev/null
foamDictionary system/controlDict -entry startTime -set 0 > /dev/null
foamDictionary system/controlDict -entry endTime -set "$END" > /dev/null
foamDictionary system/controlDict -entry deltaT -set 1e-7 > /dev/null
foamDictionary system/controlDict -entry writeInterval -set 0.002 > /dev/null
foamDictionary system/controlDict -entry functions/sidePlane/writeInterval -set 0.002 > /dev/null
if [ "$NP" -ge 4 ] && [ $((NP % 2)) -eq 0 ]; then
    N="($((NP / 2)) 2 1)"
else
    N="($NP 1 1)"
fi
foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
foamDictionary -entry coeffs.n -set "$N" system/decomposeParDict > /dev/null
decomposePar -force > log.decomposePar 2>&1
touch case.foam
nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel \
    > log.laserWireDEDFoam 2>&1
echo "FINE_PIN_DONE ${TAG}"
