#!/bin/bash
# Bare wetted neck. The trailing contact is an imposed material point of
# the wire: it moves at the feed, inside a 2-cell shell. The pool outside
# that shell is free. ppm sets the hold fraction s = min(ppm/300, 1).
# The wall angle stays 40/140 at every ppm.
#
#   LINE_TAG    case tag (default cal79)
#   LINE_PPM    oxygen ppm (default 300)
#   LINE_FEED   wire feed [m/s] (default 0.024)
#   LINE_END    end time [s] (default 0.01)
#   LINE_PARALLEL / LINE_SKIP_BUILD
#
# 12 ranks, nice 10. Laser, Marangoni and recoil stay off.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_linepin_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
TAG=${LINE_TAG:-cal79}
PPM=${LINE_PPM:-300}
FEED=${LINE_FEED:-0.024}
END=${LINE_END:-0.01}
set --
if [ "${LINE_PARALLEL:-0}" != 1 ] && ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
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
if [ "${LINE_SKIP_BUILD:-0}" != 1 ]; then
    cd "$ROOT/solver"
    ./Allwmake
    cd "$ROOT"
fi

UP=2.2e-3
DOWN=3.2e-3
HALF=1.6e-3
SUB=0.8e-3
GASH=2.3e-3
GUNI=1.9e-3
NP=12

case="$ROOT/cases/wire_cavity_${TAG}"
log="$ROOT/results/calibration/${TAG}_launch.log"
{
    echo "=== line pin ${TAG}: ppm ${PPM}, feed ${FEED}, end ${END}, bare neck, imposed contact ==="
    python3 "$ROOT/generate_case.py" --case "$case" --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream "$UP" --downstream "$DOWN" --half-width "$HALF" \
        --substrate-thickness "$SUB" --gas-height "$GASH" --gas-uniform-height "$GUNI" \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0 \
        --scan-speed 0.004 --wire-feed-speed "$FEED" \
        --beam-azimuths 30,-30,180 \
        --beam-inclinations=-26,-26,-38 \
        --beam-powers 160,160,420 \
        --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
        --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
        --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
        --end-time 0.051 --write-interval 0.002 --np "$NP" --laser-ramp 1e-4 \
        --neck-refine 3 \
        --oxygen-ppm "$PPM" --oxygen-sigma-only \
        --contact-pinning \
        --theta-receding 10 --theta-advancing 40 \
        --c-alpha-neck 4 \
        --settle 0.020 --settle-ramp 0.002 \
        --rigid-substrate 100
    foamDictionary "$case/system/controlDict" -entry endTime -set "$END" > /dev/null
    foamDictionary "$case/0.orig/T" -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
    grep -q "oxygenDependent  true" "$case/constant/meltProperties"
    if grep -q "oxygenAngleTable" "$case/constant/meltProperties"; then
        echo "oxygen angle table must stay off" >&2
        exit 1
    fi
    grep -q "pinWire         false" "$case/constant/meltProperties"
    if grep -q "oxideSkin" "$case/constant/meltProperties"; then
        echo "line-pin case must not write an oxide skin" >&2
        exit 1
    fi
    if grep -q "gasCavity" "$case/constant/meltProperties"; then
        echo "line-pin case must not write a gas cavity" >&2
        exit 1
    fi
    grep -q "tEnd    0.02;" "$case/constant/meltProperties"
    cd "$case"
    blockMesh > log.blockMesh 2>&1
    for i in 0 1 2; do
        topoSet -dict "system/topoSetDict.neck${i}" > "log.topoSet.neck${i}" 2>&1
        refineMesh -overwrite -dict system/refineMeshDict.neck > "log.refineMesh.neck${i}" 2>&1
    done
    topoSet > log.topoSet 2>&1
    createPatch -overwrite > log.createPatch 2>&1
    rm -rf 0 && mkdir 0 && cp 0.orig/* 0/
    for f in 0/*.orig; do mv "$f" "${f%.orig}"; done
    python3 "$ROOT/results/calibration/paint_slit_meniscus.py" \
        --case "$case" --wire-t 300 --film-mm 0 --film-depth-mm 0 \
        > log.paint 2>&1
    cat log.paint
    grep -q "wetted neck" log.paint
    python3 "$ROOT/results/calibration/cut_wire_wall.py" --case "$case" --write-dict
    topoSet -dict system/topoSetDict.wireCut > log.topoSet.wireCut 2>&1
    subsetMesh -overwrite -patch wireWall keepCells > log.subsetMesh 2>&1
    grep -E "Subset|Adding exposed" log.subsetMesh
    python3 "$ROOT/results/calibration/cut_wire_wall.py" \
        --case "$case" --apply --line-pin --feed "$FEED" \
        --theta-a 140 --theta-r 40
    python3 "$ROOT/results/calibration/paint_slit_meniscus.py" \
        --case "$case" --wire-t 300 --film-mm 0 --film-depth-mm 0 --dry-run \
        > log.paintCut 2>&1
    cat log.paintCut
    grep -q "wetted neck" log.paintCut
    wire_n=$(awk '$1=="wire"{print $2}' log.paintCut)
    if [ "${wire_n:-x}" != 0 ]; then
        echo "wire cells remain after the cut: ${wire_n}" >&2
        exit 1
    fi
    if ! grep -a -q "format      binary" constant/polyMesh/points; then
        echo "mesh points are not binary" >&2
        exit 1
    fi
    checkMesh > log.checkMesh 2>&1 || true
    grep -E "cells:|Mesh OK|Failed" log.checkMesh || true
    foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
    foamDictionary -entry coeffs.n -set "(6 2 1)" system/decomposeParDict > /dev/null
    decomposePar -force > log.decomposePar 2>&1
    if ! grep -a -q "linePin" constant/meltProperties; then
        echo "linePin block missing" >&2
        exit 1
    fi
    touch case.foam
    nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel \
        > log.laserWireDEDFoam 2>&1
    python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$TAG" || true
    echo "LINEPIN_DONE ${TAG}"
} > "$log" 2>&1
echo "LINEPIN_WAIT_DONE ${TAG}"
