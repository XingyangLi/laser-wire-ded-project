#!/bin/bash
# Gas cavity on the cal56 slab, without the oxide skin.
#
# Pressure support and/or a gas flux at the trailing triple line. Both
# scale with oxygen. The flux also scales with wire feed. Paint is a
# shallow film (default 0.1 mm) or a wetted neck when GAS_DEPTH=0.
# Laser, Marangoni and recoil stay off. 12 ranks, nice 10, 6 ms.
#
#   GAS_TAG    case tag           (default cal68)
#   GAS_PPM    chamber oxygen     (default 300)
#   GAS_FEED   wire feed [m/s]    (default 0.020)
#   GAS_P      pSupport at 300 ppm [Pa] (default 5000)
#   GAS_Q      qRef at 300 ppm and 20 mm/s [m/s] (default 0)
#   GAS_DEPTH  painted depth [mm] (default 0.1; 0 is a wetted neck)
#   GAS_PARALLEL    skip the single-solver lock
#   GAS_SKIP_BUILD  skip Allwmake
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_gas_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
TAG=${GAS_TAG:-cal68}
PPM=${GAS_PPM:-300}
FEED=${GAS_FEED:-0.020}
PGAS=${GAS_P:-5000}
QGAS=${GAS_Q:-0}
DEPTH=${GAS_DEPTH:-0.1}
set --
if [ "${GAS_PARALLEL:-0}" != 1 ] && ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
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
if [ "${GAS_SKIP_BUILD:-0}" != 1 ]; then
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
ANGLE=140

case="$ROOT/cases/wire_cavity_${TAG}"
log="$ROOT/results/calibration/${TAG}_launch.log"
{
    echo "=== gas ${TAG}: p ${PGAS} Pa, q ${QGAS} m/s, ppm ${PPM}, feed ${FEED} m/s, painted depth ${DEPTH} mm, ${ANGLE} deg ==="
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
        --gas-cavity --gas-pressure "$PGAS" --gas-q "$QGAS" \
        --gas-gap 0.10e-3 --gas-ppm-ref 300 \
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
    if grep -q "oxideSkin" "$case/constant/meltProperties"; then
        echo "oxide skin must stay off for the gas-cavity smoke" >&2
        exit 1
    fi
    if grep -q "oxygenAngleTable" "$case/constant/meltProperties"; then
        echo "oxygen angle table must stay off" >&2
        exit 1
    fi
    python3 - "$case/constant/meltProperties" "$FEED" "$PGAS" "$QGAS" "$PPM" << 'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
feed = f"{float(sys.argv[2]):.8g}"
p_gas = f"{float(sys.argv[3]):.8g}"
q_gas = f"{float(sys.argv[4]):.8g}"
ppm = f"{float(sys.argv[5]):.8g}"
line = next(ln for ln in text.splitlines() if "feedVelocity" in ln)
if f"-{feed}" not in line:
    raise SystemExit(f"feedVelocity {line.strip()} does not contain -{feed}")
if f"pSupport        {p_gas};" not in text:
    raise SystemExit(f"pSupport {p_gas} not written")
if f"qRef            {q_gas};" not in text:
    raise SystemExit(f"qRef {q_gas} not written")
if f"chamberOxygenPpm {ppm};" not in text and f"chamberOxygenPpm {ppm}.0;" not in text:
    raise SystemExit(f"chamberOxygenPpm {ppm} not written")
print("feed", line.strip())
print("gas", p_gas, q_gas, "ppm", ppm)
PY
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
        --case "$case" --wire-t 300 --film-mm 0.05 --film-depth-mm "$DEPTH"
    foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
    foamDictionary -entry coeffs.n -set "(6 2 1)" system/decomposeParDict > /dev/null
    decomposePar -force > log.decomposePar 2>&1
    touch case.foam
    nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
    python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$TAG" || true
    echo "GAS_DONE ${TAG}"
} > "$log" 2>&1
echo "GAS_WAIT_DONE ${TAG}"
