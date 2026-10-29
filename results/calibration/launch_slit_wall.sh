#!/bin/bash
# Two smokes, 12 ranks, nice 10, 6 ms, small slab around the neck.
#
# (A) The wire is cut out of the mesh. wireWall is a real wall: alpha.metal
#     is constantAlphaContactAngle, U is the feed velocity (0 0 -0.02) on a
#     static mesh, and T is 1700 K below z = 1.35 mm (near the 316L liquidus)
#     and 600 K above that. A 0.05 mm gas film is painted on the trailing
#     face after the cut. The plate window stays 10/40. The internal wire
#     pin is off, so it cannot fight the wall condition. Laser, Marangoni
#     and recoil stay off. 3 ranks each.
#       cal51  140 deg, the non-wetting wire
#       cal52   40 deg, the wetting control
# (B) The wire stays a metal region, as in cal48 (static 140 deg, 0.06 mm
#     groove, internal pin). The neck is refined four times, to 9.4 um, in a
#     box that covers the groove only. 6 ranks.
#       cal53
#
# Usage: launch_slit_wall.sh
#        launch_slit_wall.sh mesh     # cal51 mesh and boundary check only
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_wall_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
MODE="${1:-run}"
set --
if ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
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
cd "$ROOT/solver"
./Allwmake
cd "$ROOT"

UP=2.2e-3
DOWN=3.2e-3
HALF=1.6e-3
SUB=0.8e-3
GAS=2.3e-3
GUNI=1.9e-3

decomp_n() {
    local np="$1"
    if [ "$np" -ge 4 ] && [ $((np % 2)) -eq 0 ]; then
        echo "($((np / 2)) 2 1)"
    else
        echo "($np 1 1)"
    fi
}

common_generate() {
    local case="$1" np="$2"
    shift 2
    python3 "$ROOT/generate_case.py" --case "$case" --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream "$UP" --downstream "$DOWN" --half-width "$HALF" \
        --substrate-thickness "$SUB" --gas-height "$GAS" --gas-uniform-height "$GUNI" \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0 \
        --scan-speed 0.004 --wire-feed-speed 0.020 \
        --beam-azimuths 30,-30,180 \
        --beam-inclinations=-26,-26,-38 \
        --beam-powers 160,160,420 \
        --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
        --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
        --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
        --end-time 0.051 --write-interval 0.002 --np "$np" --laser-ramp 1e-4 \
        --oxygen-ppm 300 --oxygen-sigma-only \
        --contact-pinning \
        --theta-receding 10 --theta-advancing 40 \
        --c-alpha-neck 4 \
        --settle 0.020 --settle-ramp 0.002 \
        --rigid-substrate 100 \
        "$@"
    foamDictionary "$case/system/controlDict" -entry endTime -set 0.006 > /dev/null
    foamDictionary "$case/0.orig/T" -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
}

mesh_base() {
    local case="$1" levels="$2"
    cd "$case"
    blockMesh > log.blockMesh 2>&1
    local i
    for i in $(seq 0 $((levels - 1))); do
        topoSet -dict "system/topoSetDict.neck${i}" > "log.topoSet.neck${i}" 2>&1
        refineMesh -overwrite -dict system/refineMeshDict.neck > "log.refineMesh.neck${i}" 2>&1
    done
    topoSet > log.topoSet 2>&1
    createPatch -overwrite > log.createPatch 2>&1
}

# tag, contact angle [deg], np
wall_case() {
    local tag="$1" angle="$2" np="$3"
    local case="$ROOT/cases/wire_cavity_${tag}"
    local log="$ROOT/results/calibration/${tag}_launch.log"
    local n
    n="$(decomp_n "$np")"
    {
        echo "=== wall ${tag}: ${angle} deg, ${np} ranks ${n} ==="
        common_generate "$case" "$np" \
            --neck-refine 3 \
            --theta-receding-wire 25 --theta-advancing-wire 70
        grep -q "oxygenDependent  true" "$case/constant/meltProperties"
        if grep -q "oxygenAngleTable" "$case/constant/meltProperties"; then
            echo "oxygen angle table must stay off" >&2
            exit 1
        fi
        grep -q "pinWire         false" "$case/constant/meltProperties"
        grep -E -q 'thetaReceding[[:space:]]+10;' "$case/constant/meltProperties"
        mesh_base "$case" 3
        rm -rf 0 && mkdir 0 && cp 0.orig/* 0/
        for f in 0/*.orig; do mv "$f" "${f%.orig}"; done
        # Paint while the fields are still ASCII and the mesh is still the
        # binary blockMesh. subsetMesh then drops the wire cells and keeps
        # the film values. foamFormatConvert is not used: it rewrites the
        # mesh as ASCII, which the painter cannot read.
        python3 "$ROOT/results/calibration/paint_slit_meniscus.py" \
            --case "$case" --wire-t 300 --film-mm 0.05
        python3 "$ROOT/results/calibration/cut_wire_wall.py" --case "$case" --write-dict
        topoSet -dict system/topoSetDict.wireCut > log.topoSet.wireCut 2>&1
        subsetMesh -overwrite -patch wireWall keepCells > log.subsetMesh 2>&1
        grep -E "Subset|Adding exposed" log.subsetMesh
        python3 "$ROOT/results/calibration/cut_wire_wall.py" \
            --case "$case" --apply --theta "$angle"
        python3 "$ROOT/results/calibration/paint_slit_meniscus.py" \
            --case "$case" --wire-t 300 --film-mm 0.05 --dry-run \
            > log.paintCut 2>&1
        cat log.paintCut
        wire_n=$(awk '$1=="wire"{print $2}' log.paintCut)
        slit_n=$(awk '$1=="slit"{print $2}' log.paintCut)
        if [ "${wire_n:-x}" != 0 ]; then
            echo "wire cells remain after the cut: ${wire_n}" >&2
            exit 1
        fi
        if [ "${slit_n:-0}" -lt 1 ]; then
            echo "no film cells left after the cut" >&2
            exit 1
        fi
        if ! grep -a -q "format      binary" constant/polyMesh/points; then
            echo "mesh points are not binary" >&2
            exit 1
        fi
        checkMesh > log.checkMesh 2>&1 || true
        grep -E "cells:|Mesh OK|Failed" log.checkMesh || true
        if [ "$MODE" = "mesh" ]; then
            echo "MESH_ONLY ${tag}"
            return 0
        fi
        foamDictionary -entry numberOfSubdomains -set "$np" system/decomposeParDict > /dev/null
        foamDictionary -entry coeffs.n -set "$n" system/decomposeParDict > /dev/null
        decomposePar -force > log.decomposePar 2>&1
        touch case.foam
        nice -n 10 mpirun --use-hwthread-cpus -np "$np" laserWireDEDFoam -parallel \
            > log.laserWireDEDFoam 2>&1
        python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$tag" || true
        echo "WALL_DONE ${tag}"
    } > "$log" 2>&1
}

# cal48 again, neck at 9.4 um
fine_case() {
    local tag="cal53" np=6
    local case="$ROOT/cases/wire_cavity_${tag}"
    local log="$ROOT/results/calibration/${tag}_launch.log"
    local n
    n="$(decomp_n "$np")"
    {
        echo "=== fine neck ${tag}: 140 deg, 9.4 um, ${np} ranks ${n} ==="
        common_generate "$case" "$np" \
            --neck-refine 4 \
            --neck-box 0.40e-3:0.80e-3:0:0.18e-3:0.65e-3:1.35e-3 \
            --pin-wire --porosity --wire-cavity \
            --theta-receding-wire 25 --theta-advancing-wire 70 \
            --wire-sector \
            --theta-receding-wire-trail 140 \
            --theta-advancing-wire-trail 140 \
            --wire-sector-half-angle 90 --wire-sector-blend 0 \
            --contact-force-factor 6 \
            --contact-blend 0 \
            --wire-pin-frame head
        grep -q "oxygenDependent  true" "$case/constant/meltProperties"
        if grep -q "oxygenAngleTable" "$case/constant/meltProperties"; then
            echo "oxygen angle table must stay off" >&2
            exit 1
        fi
        grep -q "thetaRecedingWireTrail 140" "$case/constant/meltProperties"
        grep -q "pinWire         true" "$case/constant/meltProperties"
        grep -E -q 'forceBlend[[:space:]]+0;' "$case/constant/meltProperties"
        grep -E -q 'wireSectorBlend 0;' "$case/constant/meltProperties"
        mesh_base "$case" 4
        checkMesh > log.checkMesh 2>&1 || true
        rm -rf 0 && mkdir 0 && cp 0.orig/* 0/
        for f in 0/*.orig; do mv "$f" "${f%.orig}"; done
        python3 "$ROOT/results/calibration/paint_slit_meniscus.py" \
            --case "$case" --wire-t 300 --gap-mm 0.06
        grep -E "cells:|Mesh OK|Failed" log.checkMesh || true
        foamDictionary -entry numberOfSubdomains -set "$np" system/decomposeParDict > /dev/null
        foamDictionary -entry coeffs.n -set "$n" system/decomposeParDict > /dev/null
        decomposePar -force > log.decomposePar 2>&1
        touch case.foam
        nice -n 10 mpirun --use-hwthread-cpus -np "$np" laserWireDEDFoam -parallel \
            > log.laserWireDEDFoam 2>&1
        python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$tag" || true
        echo "FINE_DONE ${tag}"
    } > "$log" 2>&1
}

if [ "$MODE" = "mesh" ]; then
    echo "MESH check: cal51 wall 140 only"
    wall_case cal51 140 3
    echo "MESH_CHECK_DONE"
    exit 0
fi

echo "WALL wave: cal51 140 wall, cal52 40 wall, cal53 9.4 um neck; 3+3+6 ranks"
wall_case cal51 140 3 &
p1=$!
wall_case cal52 40 3 &
p2=$!
fine_case &
p3=$!
fail=0
wait "$p1" || fail=1
wait "$p2" || fail=1
wait "$p3" || fail=1
echo "WALL_WAIT_DONE fail=$fail"
exit "$fail"
