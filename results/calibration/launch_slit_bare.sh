#!/bin/bash
# Bare wetted neck: no painted film. 12 ranks, nice 10, 8 ms.
#
#   BARE_MODE  surface  skin carried by the surface flow, angles 140/40,
#                      laser/Marangoni/recoil off
#              flow     the same skin, with Marangoni and recoil on
#              travel   no skin; contact line and travel speed only
#   BARE_TAG   case tag (default cal74)
#   BARE_PPM   oxygen ppm (default 300)
#   BARE_FEED  wire feed [m/s] (default 0.020)
#   BARE_SCAN  travel speed [m/s] (default 0.004)
#   BARE_PARALLEL / BARE_SKIP_BUILD
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_bare_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
TAG=${BARE_TAG:-cal74}
MODE=${BARE_MODE:-surface}
PPM=${BARE_PPM:-300}
FEED=${BARE_FEED:-0.020}
SCAN=${BARE_SCAN:-0.004}
set --
if [ "${BARE_PARALLEL:-0}" != 1 ] && ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
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
if [ "${BARE_SKIP_BUILD:-0}" != 1 ]; then
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

SKIN=()
SETTLE=()
case "$MODE" in
    surface)
        SKIN=(--oxide-skin-surface --oxide-skin-mu 20 --oxide-skin-k 1e14
              --oxide-skin-gap 0.10e-3 --oxide-skin-ppm-ref 300)
        SETTLE=(--settle 0.020 --settle-ramp 0.002)
        ;;
    flow)
        SKIN=(--oxide-skin-surface --oxide-skin-mu 20 --oxide-skin-k 1e14
              --oxide-skin-gap 0.10e-3 --oxide-skin-ppm-ref 300)
        ;;
    travel)
        ;;
    *)
        echo "BARE_MODE must be surface, flow, or travel" >&2
        exit 1
        ;;
esac

case="$ROOT/cases/wire_cavity_${TAG}"
log="$ROOT/results/calibration/${TAG}_launch.log"
{
    echo "=== bare ${TAG}: mode ${MODE}, ppm ${PPM}, feed ${FEED}, scan ${SCAN}, no painted film ==="
    python3 "$ROOT/generate_case.py" --case "$case" --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream "$UP" --downstream "$DOWN" --half-width "$HALF" \
        --substrate-thickness "$SUB" --gas-height "$GASH" --gas-uniform-height "$GUNI" \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0 \
            --scan-speed "$SCAN" --wire-feed-speed "$FEED" \
        --beam-azimuths 30,-30,180 \
        --beam-inclinations=-26,-26,-38 \
        --beam-powers 160,160,420 \
        --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
        --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
        --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
        --end-time 0.051 --write-interval 0.002 --np "$NP" --laser-ramp 1e-4 \
        --neck-refine 3 \
            --oxygen-ppm "$PPM" --oxygen-sigma-only \
        "${SKIN[@]}" \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 10 --theta-advancing 40 \
        --theta-receding-wire 40 --theta-advancing-wire 140 \
        --wire-sector \
        --theta-receding-wire-trail 40 \
        --theta-advancing-wire-trail 140 \
        --wire-sector-half-angle 90 --wire-sector-blend 0 \
        --contact-force-factor 6 \
        --contact-blend 0 \
        --c-alpha-neck 4 \
        "${SETTLE[@]}" \
        --wire-pin-frame head \
        --rigid-substrate 100
    foamDictionary "$case/system/controlDict" -entry endTime -set 0.008 > /dev/null
    foamDictionary "$case/0.orig/T" -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
    if grep -q "oxygenAngleTable" "$case/constant/meltProperties"; then
        echo "oxygen angle table must stay off" >&2
        exit 1
    fi
    grep -E -q 'thetaAdvancingWire[[:space:]]+140;' "$case/constant/meltProperties"
    grep -E -q 'thetaRecedingWire[[:space:]]+40;' "$case/constant/meltProperties"
    grep -E -q 'thetaAdvancingWireTrail[[:space:]]+140;' "$case/constant/meltProperties"
    grep -E -q 'thetaRecedingWireTrail[[:space:]]+40;' "$case/constant/meltProperties"
    if [ "$MODE" = "travel" ]; then
        if grep -q "oxideSkin" "$case/constant/meltProperties"; then
            echo "travel mode must not write an oxide skin" >&2
            exit 1
        fi
    else
        grep -q "surface         true;" "$case/constant/meltProperties"
    fi
    if [ "$MODE" = "flow" ]; then
        if grep -q "settle" "$case/constant/meltProperties"; then
            echo "flow mode must leave laser, Marangoni and recoil on" >&2
            exit 1
        fi
    else
        grep -q "tEnd    0.02;" "$case/constant/meltProperties"
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
    python3 "$ROOT/results/calibration/paint_slit_meniscus.py" \
        --case "$case" --wire-t 300 --film-mm 0 --film-depth-mm 0
    foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
    foamDictionary -entry coeffs.n -set "(6 2 1)" system/decomposeParDict > /dev/null
    decomposePar -force > log.decomposePar 2>&1
    touch case.foam
    nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
    python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$TAG" || true
    echo "BARE_DONE ${TAG} ${MODE}"
} > "$log" 2>&1
echo "BARE_WAIT_DONE ${TAG}"
