#!/bin/bash
# Full-domain continuation of a curved-meniscus smoke that held the slit.
# Same bead and groove as paint_slit_meniscus.py, on the cal14 extents,
# 19 um neck, 12 ranks, nice 10. Writes a center-plane frame every 4 ms.
# Renders results/calibration/slit_demo.mp4 once several frames exist, and
# again when the run finishes. The solver is not stopped at the first render.
#
# Usage: launch_slit_demo.sh PPM FEED_M_S WIRE_T
#   example: launch_slit_demo.sh 300 0.020 300
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_demo_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
PPM=${1:?ppm}
FEED=${2:?feed m/s}
WIRE_T=${3:?wire T}
TAG=cal38
set --
if ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
    echo "a solver is already running; stop the other ranks first" >&2
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

CASE="$ROOT/cases/wire_cavity_${TAG}"
echo "=== demo ${TAG}: ${PPM} ppm, feed ${FEED} m/s, wire ${WIRE_T} K, 12 ranks ==="
python3 "$ROOT/generate_case.py" --case "$CASE" --laser-config triple \
    --wire-type solid --material 316L --resolution coarse --domain-y half \
    --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
    --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
    --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0 \
    --scan-speed 0.004 --wire-feed-speed "$FEED" \
    --beam-azimuths 30,-30,180 \
    --beam-inclinations=-26,-26,-38 \
    --beam-powers 160,160,420 \
    --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
    --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
    --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
    --end-time 0.061 --write-interval 0.004 --np 12 --laser-ramp 1e-4 \
    --neck-refine 3 \
    --oxygen-ppm "$PPM" --oxygen-wire-angles \
    --contact-pinning --pin-wire --porosity --wire-cavity \
    --theta-receding 10 --theta-advancing 40 \
    --wire-sector \
    --wire-sector-half-angle 40 --wire-sector-blend 15 \
    --contact-force-factor 6 \
    --wire-pin-frame head \
    --rigid-substrate 100
foamDictionary "$CASE/0.orig/T" -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
if [ "$WIRE_T" != 300 ]; then
    foamDictionary "$CASE/0.orig/T" -entry boundaryField/wireInlet/value -set "uniform $WIRE_T" > /dev/null
fi
grep -q "oxygenWireAnglesOnly true" "$CASE/constant/meltProperties"
grep -q "marangoni           true" "$CASE/constant/meltProperties"
cd "$CASE"
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
python3 "$ROOT/results/calibration/paint_slit_meniscus.py" --case "$CASE" --wire-t "$WIRE_T"
foamDictionary -entry numberOfSubdomains -set 12 system/decomposeParDict > /dev/null
foamDictionary -entry coeffs.n -set "(6 2 1)" system/decomposeParDict > /dev/null
decomposePar -force > log.decomposePar 2>&1
touch case.foam
nice -n 10 mpirun --use-hwthread-cpus -np 12 laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1 &
SOLVER=$!
echo "demo solver pid ${SOLVER}"
rendered=0
while kill -0 "$SOLVER" 2>/dev/null; do
    n=$(find postProcessing/sidePlane -name 'alpha.metal_xz.raw' 2>/dev/null | wc -l)
    if [ "$n" -ge 3 ] && [ "$n" -gt "$rendered" ]; then
        python3 "$ROOT/results/calibration/render_slit_video.py" \
            --case "$CASE" --tag "$TAG" \
            --out "$ROOT/results/calibration/slit_demo.mp4" || true
        rendered=$n
        echo "DEMO_RENDER frames=${n}"
    fi
    sleep 20
done
wait "$SOLVER" || true
python3 "$ROOT/results/calibration/render_slit_video.py" \
    --case "$CASE" --tag "$TAG" \
    --out "$ROOT/results/calibration/slit_demo.mp4" || true
echo "DEMO_DONE ${TAG}"
