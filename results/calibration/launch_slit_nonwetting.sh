#!/bin/bash
# Non-wetting oxide on the trailing face of the wire.
#
# Plate window stays 10/40. Trailing angles come from WIRE_OXIDE_TABLE:
# 50 ppm is 40/85 (wetting), 300 ppm is 110/145 (non-wetting). Four short
# runs, 3 ranks each, nice 10, written every 2 ms out to 16 ms. A film
# counts only if slit_metric.py calls it steady: 0.03–0.08 mm wide, at
# least 0.25 mm deep, for at least 4 ms.
#
#   cal44  300 ppm, 0.06 mm groove, laser / Marangoni / recoil off
#   cal45  300 ppm, 0.06 mm groove, those terms on from the first step
#   cal46  300 ppm, 0.12 mm groove, those terms off (resolved gap)
#   cal47   50 ppm, 0.06 mm groove, those terms off (wetting control)
#
# Usage: launch_slit_nonwetting.sh
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_nonwetting_launch.log) 2>&1
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
NP=3

# tag, ppm, groove mouth [mm], settle end [s]
# settle end past the run keeps the laser, Marangoni and recoil off.
mesh_and_run() {
    local tag="$1" ppm="$2" gap="$3" settle="$4"
    local case="$ROOT/cases/wire_cavity_${tag}"
    local log="$ROOT/results/calibration/${tag}_launch.log"
    {
        echo "=== nonwetting ${tag}: ${ppm} ppm, gap ${gap} mm, settle ${settle} s ==="
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
            --oxygen-ppm "$ppm" --oxygen-wire-angles \
            --contact-pinning --pin-wire --porosity --wire-cavity \
            --theta-receding 10 --theta-advancing 40 \
            --wire-sector \
            --wire-sector-half-angle 40 --wire-sector-blend 15 \
            --contact-force-factor 6 \
            --contact-blend 8 \
            --c-alpha-neck 4 \
            --settle "$settle" --settle-ramp 0.002 \
            --wire-pin-frame head \
            --rigid-substrate 100
        # end-time 0.051 keeps the contact-line interval at 10. The run itself
        # stops at 16 ms.
        foamDictionary "$case/system/controlDict" -entry endTime -set 0.016 > /dev/null
        foamDictionary "$case/0.orig/T" -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
        grep -q "oxygenWireAnglesOnly true" "$case/constant/meltProperties"
        grep -q "marangoni           true" "$case/constant/meltProperties"
        if [ "$ppm" = 300 ]; then
            grep -q "thetaRecedingWireTrail 110" "$case/constant/meltProperties"
            grep -q "thetaAdvancingWireTrail 145" "$case/constant/meltProperties"
        else
            grep -q "thetaRecedingWireTrail 40" "$case/constant/meltProperties"
            grep -q "thetaAdvancingWireTrail 85" "$case/constant/meltProperties"
        fi
        grep -E -q 'thetaReceding[[:space:]]+10;' "$case/constant/meltProperties"
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
        python3 "$ROOT/results/calibration/paint_slit_meniscus.py" \
            --case "$case" --wire-t 300 --gap-mm "$gap"
        foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
        foamDictionary -entry coeffs.n -set "(${NP} 1 1)" system/decomposeParDict > /dev/null
        decomposePar -force > log.decomposePar 2>&1
        touch case.foam
        nice -n 10 mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
        python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$tag" || true
        echo "NONWETTING_DONE ${tag}"
    } > "$log" 2>&1
}

echo "NONWETTING wave: cal44 300/narrow/off, cal45 300/narrow/on, cal46 300/wide/off, cal47 50/narrow/off; ${NP} ranks each"
mesh_and_run cal44 300 0.06 0.020 &
p1=$!
mesh_and_run cal45 300 0.06 0 &
p2=$!
mesh_and_run cal46 300 0.12 0.020 &
p3=$!
mesh_and_run cal47 50 0.06 0.020 &
p4=$!
fail=0
wait "$p1" || fail=1
wait "$p2" || fail=1
wait "$p3" || fail=1
wait "$p4" || fail=1
echo "NONWETTING_WAIT_DONE fail=$fail"
exit "$fail"
