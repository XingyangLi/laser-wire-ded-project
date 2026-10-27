#!/bin/bash
# Short 3D smokes for the trailing-face slit, on the cal14 beams and plate.
#
# The full-track neck mesh (cal26/cal29/cal32) was still at t ~ 0.014 s after
# an hour, because it starts from a cold wire and a 19 um step. These smokes
# are a few millimetres around the neck, a short plate, and a hot bead that
# is already fused, with a 0.06 mm gas gap cut on the trailing wire face from
# z = 0.75 mm to the free surface. Feed is on from t = 0. End 51 ms, write
# every 10 ms. The question is whether that gap stays a thin open slit.
#
#   cal34  50 ppm   feed 20 mm/s  wire 300 K
#   cal35  300 ppm  feed 20 mm/s  wire 300 K
#   cal36  300 ppm  feed 28 mm/s  wire 300 K
#   cal37  100 ppm  feed 24 mm/s  wire 900 K
#
# Four cases, 3 ranks each, nice 10. Plate window 10/40. Wire and trailing
# windows follow the oxide table. Marangoni and recoil stay on.
#
# Usage: launch_slit_smoke.sh [wave|mesh]
#   mesh   build only cal35 and stop after setFields
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_smoke_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
MODE=${1:-wave}
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

# Small box around the neck. Wire axis at the origin. x is -upstream..+downstream.
UP=2.2e-3
DOWN=3.2e-3
HALF=1.6e-3
SUB=0.8e-3
GAS=2.3e-3
GUNI=1.9e-3

paint_pool() {
    local case_dir="$1"
    local wire_t="$2"
    python3 - << PY
from pathlib import Path
p = Path("$case_dir") / "system/setFieldsDict"
s = p.read_text()
old = "            volScalarFieldValue alpha.metal 1\\n        );"
new = (
    "            volScalarFieldValue alpha.metal 1\\n"
    "            volScalarFieldValue T 1100\\n"
    "            volScalarFieldValue meltHistory 1\\n"
    "        );"
)
n = s.count(old)
if n != 1:
    raise SystemExit(f"substrate block count {n}")
s = s.replace(old, new, 1)
marker = "    cylinderToCell  // wire (held at rest until tFeedStart)\\n"
extra = """    boxToCell       // molten plate under the bead
    {
        box (-0.0012 -1 -0.00045) (0.0016 0.0011 0);
        fieldValues
        (
            volScalarFieldValue alpha.metal 1
            volScalarFieldValue T 1900
            volScalarFieldValue meltHistory 1
        );
    }
    boxToCell       // bead
    {
        box (-0.0010 -1 0) (0.0015 0.0011 0.00115);
        fieldValues
        (
            volScalarFieldValue alpha.metal 1
            volScalarFieldValue cWire 1
            volScalarFieldValue T 2000
            volScalarFieldValue meltHistory 1
        );
    }
    boxToCell       // taller dome on the trailing side, outside the slit
    {
        box (0.00058 -1 0.00115) (0.0014 0.0010 0.00155);
        fieldValues
        (
            volScalarFieldValue alpha.metal 1
            volScalarFieldValue cWire 1
            volScalarFieldValue T 1900
            volScalarFieldValue meltHistory 1
        );
    }
    boxToCell       // gas slit, trailing face, open into the gas above 1.15 mm
    {
        box (0.00050 -1 0.00075) (0.00056 0.00030 0.00128);
        fieldValues
        (
            volScalarFieldValue alpha.metal 0
            volScalarFieldValue cWire 0
            volScalarFieldValue T 500
            volScalarFieldValue meltHistory 0
        );
    }
"""
if marker not in s:
    raise SystemExit("wire cylinder marker missing")
s = s.replace(marker, extra + marker, 1)
if int("$wire_t") != 300:
    head, tail = s.split(marker, 1)
    old_t = "            volScalarFieldValue T 300\\n"
    if old_t not in tail:
        raise SystemExit("wire T 300 not in the cylinder block")
    tail = tail.replace(old_t, "            volScalarFieldValue T $wire_t\\n", 1)
    s = head + marker + tail
p.write_text(s)
print("painted pool and slit in", p)
PY
    foamDictionary "$case_dir/0.orig/T" -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
    if [ "$wire_t" != 300 ]; then
        foamDictionary "$case_dir/0.orig/T" -entry boundaryField/wireInlet/value -set "uniform $wire_t" > /dev/null
    fi
}

gen_one() {
    local tag="$1" ppm="$2" feed="$3" wire_t="$4"
    local case="$ROOT/cases/wire_cavity_${tag}"
    echo "=== generate ${tag}: ${ppm} ppm, feed ${feed} m/s, wire ${wire_t} K ==="
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
        --end-time 0.051 --write-interval 0.01 --np 3 --laser-ramp 1e-4 \
        --neck-refine 3 \
        --oxygen-ppm "$ppm" --oxygen-wire-angles \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 10 --theta-advancing 40 \
        --wire-sector \
        --wire-sector-half-angle 40 --wire-sector-blend 15 \
        --contact-force-factor 6 \
        --wire-pin-frame head \
        --rigid-substrate 100
    paint_pool "$case" "$wire_t"
    grep -q "gas slit" "$case/system/setFieldsDict"
    grep -q "oxygenWireAnglesOnly true" "$case/constant/meltProperties"
    grep -q "marangoni           true" "$case/constant/meltProperties"
    foamDictionary "$case/0.orig/T" -entry boundaryField/inletSubstrate/value | grep -q 1100
    foamDictionary "$case/0.orig/T" -entry boundaryField/inletGas/value | grep -q 300
}

run_one() {
    local tag="$1" ppm="$2" feed="$3" wire_t="$4"
    local case="$ROOT/cases/wire_cavity_${tag}"
    local log="$ROOT/results/calibration/${tag}_launch.log"
    {
        gen_one "$tag" "$ppm" "$feed" "$wire_t"
        cd "$case"
        if [ "$MODE" = "mesh" ]; then
            # Serial mesh and setFields, no decompose, so the slit can be counted.
            bash -c '
              set -e
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
              setFields > log.setFields 2>&1
            '
            echo "MESH_DONE ${tag}"
            grep -E "cells:|Mesh OK|Failed" log.checkMesh || true
            grep -E "cells|Set " log.setFields || true
        else
            nice -n 10 ./Allrun 3
            python3 "$ROOT/results/calibration/slit_metric.py" --case "$case" --tag "$tag" || true
            echo "SMOKE_DONE ${tag}"
        fi
    } > "$log" 2>&1
}

if [ "$MODE" = "mesh" ]; then
    run_one cal35 300 0.020 300
    echo "MESH_ONLY finished"
    exit 0
fi

if [ "$MODE" != "wave" ]; then
    echo "unknown mode: $MODE" >&2
    exit 1
fi

echo "SMOKE wave: cal34 cal35 cal36 cal37, 3 ranks each"
run_one cal34 50 0.020 300 &
p1=$!
run_one cal35 300 0.020 300 &
p2=$!
run_one cal36 300 0.028 300 &
p3=$!
run_one cal37 100 0.024 900 &
p4=$!
fail=0
wait "$p1" || fail=1
wait "$p2" || fail=1
wait "$p3" || fail=1
wait "$p4" || fail=1
echo "SMOKE_WAIT_DONE fail=$fail"
exit "$fail"
