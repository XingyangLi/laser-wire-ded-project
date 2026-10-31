#!/bin/bash
# Two extra 2:1 passes on the trailing neck so the slit band is ~5 um.
# The band above z=1.52 mm is still ~75 um, so it is refined twice first,
# then the whole slit band (already ~19 um below 1.55 mm) is refined twice.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/lib.sh"
ROOT="$TAO_ROOT"
SRC="$ROOT/cases/wire_cavity_wall_tip"
CASE="$ROOT/cases/wire_cavity_skinFine"
rm -rf "$CASE"
cp -a "$SRC" "$CASE"
cd "$CASE"
tao_source_foam

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

# Coarse cells above z=1.56 mm (~75 um) get two passes, down to ~19 um.
# The box stays above the existing 19 um band so those cells are not
# refined three times (that made ~2 um cells and a 1e-7 s capillary step).
write_topo A 4.6e-4 7.6e-4  -2e-5 1.6e-4  1.56e-3 1.80e-3
write_topo B 4.7e-4 7.4e-4  -1e-5 1.4e-4  1.58e-3 1.78e-3
# One pass on the whole slit band: ~19 um -> ~10 um, top and bottom.
write_topo C 4.6e-4 7.4e-4  -2e-5 1.6e-4  1.15e-3 1.78e-3

for level in A B C; do
    topoSet -dict "system/topoSetDict.neck${level}" > "log.topoSet.neck${level}" 2>&1
    refineMesh -overwrite -dict system/refineMeshDict.neck > "log.refineMesh.neck${level}" 2>&1
    if [[ -f constant/polyMesh/cellMap ]]; then
        mkdir -p 0/polyMesh
        cp -a constant/polyMesh/cellMap 0/polyMesh/cellMap
    fi
    if [[ ! -f 0/polyMesh/cellMap ]]; then
        echo "pass ${level}: cellMap missing" >&2
        exit 1
    fi
    "$TAO_PY" "$ROOT/results/calibration/remap_refined_fields.py" 0
    echo "pass ${level} done"
done
checkMesh > log.checkMesh 2>&1 || true
grep -E "cells:|Mesh OK|Failed|Max aspect|Min volume" log.checkMesh | head -20
echo REFINE_DONE
