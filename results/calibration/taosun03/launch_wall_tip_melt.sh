#!/bin/bash
# Solid-wire restart of the cal95b bead, with a melt rule at the tip.
#
# The bead is the equal-power checkpoint (247 W x 3, t = 0.8 s). A thin
# trailing band is refined to about 19 um, the wire cylinder is cut out as
# a wall moving at the feed, and linePin holds the trailing contact. The
# tip melt is the generated part: superheat on the wall bottom becomes
# liquid wire. Nothing is painted.
#
#   FEED   m/s (default 0.024)
#   END    pin window s (default 0.006)
#   NP     ranks (default 4)
#
# Four ranks, nice 10. One job, inside the 32-core cap.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/wall_tip_melt_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
ROOT="$TAO_ROOT"
SRC="${CAL95B_SRC:-/tmp/results/calibration/checkpoints/cal95b}"
CASE="${CASE:-$ROOT/cases/wire_cavity_wall_tip}"
FEED="${FEED:-0.024}"
END="${END:-0.006}"
NP="${NP:-4}"
SIGMA_SCALE="${SIGMA_SCALE:-1}"
if [[ ! -f "$SRC/0.8/alpha.metal" ]]; then
    echo "missing checkpoint $SRC/0.8" >&2
    exit 1
fi
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build

echo "=== wall tip melt feed=$FEED end=$END np=$NP sigmaScale=$SIGMA_SCALE ==="
rm -rf "$CASE"
mkdir -p "$CASE"
cp -a "$SRC/constant" "$SRC/system" "$SRC/0.8" "$CASE/"
rm -f "$CASE/0.8/phi" "$CASE/0.8/alphaPhi0.metal"
# The 2:1 neck needs a bounded gradient or the gas step collapses.
python3 - "$CASE/system/fvSchemes" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
t = p.read_text()
t = t.replace("Gauss linear corrected;", "Gauss linear limited corrected 0.5;")
t = t.replace("default         corrected;", "default         limited corrected 0.5;")
p.write_text(t)
print("schemes: limited corrected 0.5")
PY
python3 - "$CASE/system/fvSolution" <<'PY'
from pathlib import Path
import sys, re
p = Path(sys.argv[1])
t = p.read_text()
t2, n = re.subn(r"(nNonOrthogonalCorrectors\s+)\d+", r"\g<1>2", t, count=1)
p.write_text(t2 if n else t)
print("non-orthogonal correctors", "2" if n else "unchanged")
PY

cd "$CASE"
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
write_topo 0  1.95e-4  1.075e-3   -3.25e-4  5.25e-4   2.25e-4  1.775e-3
write_topo 1  3.45e-4  9.25e-4    -1.75e-4  3.75e-4   3.75e-4  1.625e-3
write_topo 2  4.20e-4  8.50e-4    -1.00e-4  3.00e-4   4.50e-4  1.550e-3

tao_source_foam
for i in 0 1 2; do
    topoSet -dict "system/topoSetDict.neck${i}" > "log.topoSet.neck${i}" 2>&1
    refineMesh -overwrite -dict system/refineMeshDict.neck > "log.refineMesh.neck${i}" 2>&1
    # v2406 writes the new-to-old map next to the time directory.
    if [[ ! -f 0.8/polyMesh/cellMap && -f constant/polyMesh/cellMap ]]; then
        mkdir -p 0.8/polyMesh
        cp -a constant/polyMesh/cellMap 0.8/polyMesh/cellMap
    fi
    if [[ ! -f 0.8/polyMesh/cellMap ]]; then
        echo "refine pass ${i}: cellMap missing" >&2
        exit 1
    fi
    "$TAO_PY" "$ROOT/results/calibration/remap_refined_fields.py" 0.8
    echo "refine pass ${i} done"
done
checkMesh > log.checkMesh 2>&1 || true
grep -E "cells:|Mesh OK|Failed|Min volume|Max aspect" log.checkMesh | head -20
if ! grep -q "Mesh OK" log.checkMesh; then
    echo "checkMesh failed" >&2
    exit 1
fi

python3 "$ROOT/results/calibration/cut_wire_wall.py" --case "$CASE" --write-dict
topoSet -dict system/topoSetDict.wireCut > log.topoSet.wireCut 2>&1
subsetMesh -overwrite -patch wireWall keepCells > log.subsetMesh 2>&1
if [ -d 0.8 ]; then
    rm -rf 0
    mv 0.8 0
fi
python3 "$ROOT/results/calibration/cut_wire_wall.py" \
    --case "$CASE" --apply --line-pin --feed "$FEED" \
    --theta-a 140 --theta-r 40
python3 - << 'PY'
from pathlib import Path
import re
p = Path("constant/meltProperties")
text = p.read_text()
text2, n = re.subn(r"(pinWire\s+)true", r"\1false", text, count=1)
if n != 1:
    raise SystemExit("pinWire true missing")
if "wireTipMelt" in text2:
    raise SystemExit("wireTipMelt already present")
text2 = text2.rstrip() + """

wireTipMelt
{
    enabled         true;
    Twire           300;
    band            4e-4;
    vMax            0.05;
}
"""
p.write_text(text2 + "\n")
print("pinWire false, wireTipMelt on")
PY
# sigmaScale is an imposed numerical enhancement of the CSF coefficient.
# 1 would leave the alloy value (1.75 N/m). It is not a measured sigma.
foamDictionary constant/meltProperties -entry surfaceTension/sigmaScale -set "$SIGMA_SCALE" > /dev/null
grep -n "sigmaScale" constant/meltProperties
foamDictionary constant/meltProperties -entry wire/tFeedStart -set 0 > /dev/null
foamDictionary constant/meltProperties -entry wire/feedVelocity -set "(0 0 -$FEED)" > /dev/null
foamDictionary system/controlDict -entry startFrom -set startTime > /dev/null
foamDictionary system/controlDict -entry startTime -set 0 > /dev/null
foamDictionary system/controlDict -entry endTime -set "$END" > /dev/null
foamDictionary system/controlDict -entry deltaT -set 2e-7 > /dev/null
foamDictionary system/controlDict -entry writeInterval -set 0.002 > /dev/null
foamDictionary system/controlDict -entry functions/sidePlane/writeInterval -set 0.002 > /dev/null
if [[ "${PREP_ONLY:-0}" == 1 ]]; then
    echo "PREP_ONLY: mesh, wall and tip melt are ready in $CASE"
    exit 0
fi
foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
foamDictionary -entry coeffs.n -set "($NP 1 1)" system/decomposeParDict > /dev/null
decomposePar -force > log.decomposePar 2>&1
touch case.foam
echo "SOLVE $(date --iso-8601=seconds)"
nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
    laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
rc=$?
echo "SOLVE_RC $rc"
latest=$(ls -d processor0/[0-9]* processor0/[0-9].* 2>/dev/null | sed 's#processor0/##' | sort -g | tail -1)
reconstructPar -time "$latest" > log.reconstructPar 2>&1 || true
cd "$ROOT"
"$TAO_PY" "$DIR/render_baseline_bead.py" --case "$CASE" \
    --out "$DIR/wall_tip_melt_views.png" || true
grep -E 'LinePin:|WireTipMelt:|WireSlit:|FOAM FATAL' "$CASE/log.laserWireDEDFoam" | head -8
grep -E 'LinePin:|WireTipMelt:|WireSlit:' "$CASE/log.laserWireDEDFoam" | tail -12
echo "WALL_TIP_RC $rc"
exit "$rc"
