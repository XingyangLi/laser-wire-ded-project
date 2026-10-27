#!/bin/bash
# Curved-meniscus smokes for the trailing-face slit.
#
# cal34–cal37 cut a square 0.06 mm slot in a rectangular bead. At 4 ms the
# metal wall was gone on the center plane for every oxygen, feed and preheat
# in that set, so the slot is not a slit the contact line can hold.
# These two start from a smooth dome with the groove already tapered
# (paint_slit_meniscus.py): 300 ppm and 50 ppm, both at the cal14 feed,
# wire 300 K. Six ranks each, nice 10.
#
# Usage: launch_slit_curve.sh
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_curve_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
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
NP=6

mesh_and_run() {
    local tag="$1" ppm="$2" feed="$3" wire_t="$4"
    local case="$ROOT/cases/wire_cavity_${tag}"
    local log="$ROOT/results/calibration/${tag}_launch.log"
    {
        echo "=== curve ${tag}: ${ppm} ppm, feed ${feed} m/s, wire ${wire_t} K ==="
        python3 "$ROOT/generate_case.py" --case "$case" --laser-config triple \
            --wire-type solid --material 316L --resolution coarse --domain-y half \
            --upstream "$UP" --downstream "$DOWN" --half-width "$HALF" \
            --substrate-thickness "$SUB" --gas-height "$GAS" --gas-uniform-height "$GUNI" \
            --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0 \
            --scan-speed 0.004 --wire-feed-speed "$feed" \
            --beam-azimuths 30,-30,180 \
            --beam-inclinations=-26,-26,-38 \
            --beam-powers 160,160,420 \
            --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
            --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
            --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
            --end-time 0.051 --write-interval 0.004 --np "$NP" --laser-ramp 1e-4 \
            --neck-refine 3 \
            --oxygen-ppm "$ppm" --oxygen-wire-angles \
            --contact-pinning --pin-wire --porosity --wire-cavity \
            --theta-receding 10 --theta-advancing 40 \
            --wire-sector \
            --wire-sector-half-angle 40 --wire-sector-blend 15 \
            --contact-force-factor 6 \
            --wire-pin-frame head \
            --rigid-substrate 100
        foamDictionary "$case/0.orig/T" -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
        if [ "$wire_t" != 300 ]; then
            foamDictionary "$case/0.orig/T" -entry boundaryField/wireInlet/value -set "uniform $wire_t" > /dev/null
        fi
        grep -q "oxygenWireAnglesOnly true" "$case/constant/meltProperties"
        grep -q "marangoni           true" "$case/constant/meltProperties"
        cd "$case"
        blockMesh > log.blockMesh 2>&1
        for i in 0 1 2; do
            topoSet -dict system/topoSetDict.neck$i > log.topoSet.neck$i 2>&1
            refineMesh -overwrite -dict system/refineMeshDict.neck > log.refineMesh.neck$i 2>&1
        done
        topoSet > log.topoSet 2>&1
        createPatch -overwrite > log.createPatch 2>&1
        checkMesh > log.checkMesh 2>&1 || true
        rm -rf 0 && mkdir 0 && cp 0.orig/* 0/
        for f in 0/*.orig; do mv "$f" "${f%.orig}"; done
        python3 "$ROOT/results/calibration/paint_slit_meniscus.py" --case "$case" --wire-t "$wire_t"
        foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
        foamDictionary -entry coeffs.n -set "($((NP / 2)) 2 1)" system/decomposeParDict > /dev/null
        decomposePar -force > log.decomposePar 2>&1
        touch case.foam
        nice -n 10 mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
        python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$tag" || true
        echo "CURVE_DONE ${tag}"
    } > "$log" 2>&1
}

echo "CURVE wave: cal39 300 ppm, cal40 50 ppm, ${NP} ranks each"
mesh_and_run cal39 300 0.020 300 &
p1=$!
mesh_and_run cal40 50 0.020 300 &
p2=$!
fail=0
wait "$p1" || fail=1
wait "$p2" || fail=1
echo "CURVE_WAIT_DONE fail=$fail"
exit "$fail"
