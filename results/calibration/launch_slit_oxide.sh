#!/bin/bash
# Oxide skin on the painted 0.05 mm trailing film.
#
# Same small-domain slab and static 140 deg window as cal50. Sahoo-Belton
# sigma at 300 ppm (full skin strength: ppmRef 300). Laser, Marangoni and
# recoil stay off for the 6 ms. The skin is an implicit interfacial
# viscosity plus a radial damper inside 0.10 mm of the wire face.
# 12 ranks, nice 10, written every 2 ms.
#
#   OXIDE_TAG   case tag          (default cal54)
#   OXIDE_MU    muSkin [Pa.s]     (default 20)
#   OXIDE_K     Kskin [kg/m^3/s]  (default 1e14)
#   OXIDE_PPM   chamber oxygen    (default 300; strength is min(ppm/300, 1))
#   OXIDE_FEED  wire feed [m/s]   (default 0.020)
#   OXIDE_PARALLEL    skip the single-solver lock (a sweep runs two at once)
#   OXIDE_SKIP_BUILD  skip Allwmake (the sweep builds once)
#
# Usage: launch_slit_oxide.sh
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_oxide_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
TAG=${OXIDE_TAG:-cal54}
MU=${OXIDE_MU:-20}
KSKIN=${OXIDE_K:-1e14}
PPM=${OXIDE_PPM:-300}
FEED=${OXIDE_FEED:-0.020}
set --
if [ "${OXIDE_PARALLEL:-0}" != 1 ] && ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
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
if [ "${OXIDE_SKIP_BUILD:-0}" != 1 ]; then
    cd "$ROOT/solver"
    ./Allwmake
    cd "$ROOT"
fi

UP=2.2e-3
DOWN=3.2e-3
HALF=1.6e-3
SUB=0.8e-3
GAS=2.3e-3
GUNI=1.9e-3
NP=12
ANGLE=140

case="$ROOT/cases/wire_cavity_${TAG}"
log="$ROOT/results/calibration/${TAG}_launch.log"
{
    echo "=== oxide ${TAG}: mu ${MU} Pa.s, K ${KSKIN}, ppm ${PPM}, feed ${FEED} m/s, film 0.05 mm, ${ANGLE} deg ==="
    python3 "$ROOT/generate_case.py" --case "$case" --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream "$UP" --downstream "$DOWN" --half-width "$HALF" \
        --substrate-thickness "$SUB" --gas-height "$GAS" --gas-uniform-height "$GUNI" \
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
        --oxide-skin --oxide-skin-mu "$MU" --oxide-skin-k "$KSKIN" \
        --oxide-skin-gap 0.10e-3 --oxide-skin-ppm-ref 300 \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 10 --theta-advancing 40 \
        --theta-receding-wire 25 --theta-advancing-wire 70 \
        --wire-sector \
        --theta-receding-wire-trail "$ANGLE" \
        --theta-advancing-wire-trail "$ANGLE" \
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
    grep -q "chamberOxygenPpm ${PPM}" "$case/constant/meltProperties" \
        || grep -q "chamberOxygenPpm ${PPM}.0" "$case/constant/meltProperties" \
        || { echo "chamberOxygenPpm ${PPM} not written"; exit 1; }
    python3 - "$case/constant/meltProperties" "$FEED" << 'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
feed = f"{float(sys.argv[2]):.8g}"
line = next(ln for ln in text.splitlines() if "feedVelocity" in ln)
if f"-{feed}" not in line:
    raise SystemExit(f"feedVelocity {line.strip()} does not contain -{feed}")
print("feed", line.strip())
PY
    if grep -q "oxygenAngleTable" "$case/constant/meltProperties"; then
        echo "oxygen angle table must stay off" >&2
        exit 1
    fi
    grep -q "oxideSkin" "$case/constant/meltProperties"
    grep -q "Kskin" "$case/constant/meltProperties"
    grep -q "muSkin          ${MU};" "$case/constant/meltProperties" \
        || grep -q "muSkin          ${MU}.0;" "$case/constant/meltProperties" \
        || { echo "muSkin not written"; exit 1; }
    grep -q "thetaRecedingWireTrail ${ANGLE}" "$case/constant/meltProperties"
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
        --case "$case" --wire-t 300 --film-mm 0.05
    foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
    foamDictionary -entry coeffs.n -set "(6 2 1)" system/decomposeParDict > /dev/null
    decomposePar -force > log.decomposePar 2>&1
    touch case.foam
    nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
    python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$TAG" || true
    echo "OXIDE_DONE ${TAG}"
} > "$log" 2>&1
echo "OXIDE_WAIT_DONE ${TAG}"
