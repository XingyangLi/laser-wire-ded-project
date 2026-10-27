#!/bin/bash
# What keeps a thin trailing-face film steady.
#
# Same curved groove as launch_slit_curve.sh (300 ppm, feed 20 mm/s, wire
# 300 K, cal14 beams). Three short runs, 4 ranks each, nice 10, written
# every 2 ms out to 16 ms. A film counts only if slit_metric.py calls it
# steady: 0.03–0.08 mm wide, at least 0.25 mm deep, for at least 4 ms.
#
#   cal41  settle 6 ms, hard contact switch, cAlpha 1
#          laser / Marangoni / recoil off, then a 2 ms ramp
#   cal42  no settle, Young force blended over 8 deg, neck cAlpha x4
#   cal43  settle and the numerical package together
#
# Usage: launch_slit_stable.sh
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_stable_launch.log) 2>&1
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
NP=4

mesh_and_run() {
    local tag="$1" settle="$2" blend="$3" calpha="$4"
    local case="$ROOT/cases/wire_cavity_${tag}"
    local log="$ROOT/results/calibration/${tag}_launch.log"
    {
        echo "=== stable ${tag}: settle ${settle} s, blend ${blend} deg, cAlphaNeck ${calpha} ==="
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
            --end-time 0.051 --write-interval 0.002 --np "$NP" --laser-ramp 1e-4 \
            --neck-refine 3 \
            --oxygen-ppm 300 --oxygen-wire-angles \
            --contact-pinning --pin-wire --porosity --wire-cavity \
            --theta-receding 10 --theta-advancing 40 \
            --wire-sector \
            --wire-sector-half-angle 40 --wire-sector-blend 15 \
            --contact-force-factor 6 \
            --contact-blend "$blend" \
            --c-alpha-neck "$calpha" \
            --settle "$settle" --settle-ramp 0.002 \
            --wire-pin-frame head \
            --rigid-substrate 100
        # end-time 0.051 keeps the contact-line interval at 10. The run itself
        # stops at 16 ms, which is enough to see whether the film sits still.
        foamDictionary "$case/system/controlDict" -entry endTime -set 0.016 > /dev/null
        foamDictionary "$case/0.orig/T" -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
        grep -q "oxygenWireAnglesOnly true" "$case/constant/meltProperties"
        grep -q "marangoni           true" "$case/constant/meltProperties"
        if [ "$settle" != 0 ]; then
            grep -q "tEnd" "$case/constant/meltProperties"
        fi
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
        python3 "$ROOT/results/calibration/paint_slit_meniscus.py" --case "$case" --wire-t 300
        foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
        foamDictionary -entry coeffs.n -set "(2 2 1)" system/decomposeParDict > /dev/null
        decomposePar -force > log.decomposePar 2>&1
        touch case.foam
        nice -n 10 mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
        python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$tag" || true
        echo "STABLE_DONE ${tag}"
    } > "$log" 2>&1
}

echo "STABLE wave: cal41 settle, cal42 blend+compression, cal43 both; ${NP} ranks each"
mesh_and_run cal41 0.006 0 1 &
p1=$!
mesh_and_run cal42 0 8 4 &
p2=$!
mesh_and_run cal43 0.006 8 4 &
p3=$!
fail=0
wait "$p1" || fail=1
wait "$p2" || fail=1
wait "$p3" || fail=1
echo "STABLE_WAIT_DONE fail=$fail"
exit "$fail"
