#!/bin/bash
# Static trailing-face angle, no hysteresis and no blend.
#
# Sahoo-Belton sigma stays at 300 ppm. The angle table is off, so the
# trailing window is the scalar pair and the plate stays 10/40. Receding
# and advancing are the same number: the Young force restores that one
# angle, and the velocity sink stays off except on an exact hit. Sector
# blend and force blend are 0. Laser, Marangoni and recoil stay off.
# 4 ranks each, nice 10, written every 2 ms, stopped at 6 ms.
#
#   cal48  140 deg, tapered 0.06 mm groove
#   cal49  160 deg, tapered 0.06 mm groove
#   cal50  140 deg, 0.05 mm gas film on the whole trailing half
#
# WireForce in the solver log is the neck check: cells on the wire face,
# the 1.75h band, the cap, and |F|*h against 2*sigma/w at the mouth.
# There is no velocity cap.
#
# Usage: launch_slit_static.sh
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_static_launch.log) 2>&1
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

# tag, static trailing angle [deg], film thickness [mm] (0 = tapered groove)
mesh_and_run() {
    local tag="$1" angle="$2" film="$3"
    local case="$ROOT/cases/wire_cavity_${tag}"
    local log="$ROOT/results/calibration/${tag}_launch.log"
    {
        echo "=== static ${tag}: ${angle} deg, film ${film} mm ==="
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
            --oxygen-ppm 300 --oxygen-sigma-only \
            --contact-pinning --pin-wire --porosity --wire-cavity \
            --theta-receding 10 --theta-advancing 40 \
            --theta-receding-wire 25 --theta-advancing-wire 70 \
            --wire-sector \
            --theta-receding-wire-trail "$angle" \
            --theta-advancing-wire-trail "$angle" \
            --wire-sector-half-angle 90 --wire-sector-blend 0 \
            --contact-force-factor 6 \
            --contact-blend 0 \
            --c-alpha-neck 4 \
            --settle 0.020 --settle-ramp 0.002 \
            --wire-pin-frame head \
            --rigid-substrate 100
        foamDictionary "$case/system/controlDict" -entry endTime -set 0.006 > /dev/null
        foamDictionary "$case/0.orig/T" -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
        grep -q "oxygenDependent  true" "$case/constant/meltProperties"
        if grep -q "oxygenAngleTable" "$case/constant/meltProperties"; then
            echo "oxygen angle table must stay off" >&2
            exit 1
        fi
        grep -q "thetaRecedingWireTrail ${angle}" "$case/constant/meltProperties"
        grep -q "thetaAdvancingWireTrail ${angle}" "$case/constant/meltProperties"
        grep -E -q 'thetaReceding[[:space:]]+10;' "$case/constant/meltProperties"
        grep -E -q 'forceBlend[[:space:]]+0;' "$case/constant/meltProperties"
        grep -E -q 'wireSectorBlend 0;' "$case/constant/meltProperties"
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
        if [ "$film" = "0" ]; then
            python3 "$ROOT/results/calibration/paint_slit_meniscus.py" \
                --case "$case" --wire-t 300 --gap-mm 0.06
        else
            python3 "$ROOT/results/calibration/paint_slit_meniscus.py" \
                --case "$case" --wire-t 300 --film-mm "$film"
        fi
        foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
        foamDictionary -entry coeffs.n -set "(2 2 1)" system/decomposeParDict > /dev/null
        decomposePar -force > log.decomposePar 2>&1
        touch case.foam
        nice -n 10 mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
        python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$tag" || true
        echo "STATIC_DONE ${tag}"
    } > "$log" 2>&1
}

echo "STATIC wave: cal48 140 groove, cal49 160 groove, cal50 140 film; ${NP} ranks each"
mesh_and_run cal48 140 0 &
p1=$!
mesh_and_run cal49 160 0 &
p2=$!
mesh_and_run cal50 140 0.05 &
p3=$!
fail=0
wait "$p1" || fail=1
wait "$p2" || fail=1
wait "$p3" || fail=1
echo "STATIC_WAIT_DONE fail=$fail"
exit "$fail"
