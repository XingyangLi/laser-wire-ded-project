#!/bin/bash
# Thin gas slit on the trailing face of the wire, on the cal14 bead.
#
# The plate stays at 1100 K with the 10/40 window. The wire and the trailing
# sector take their windows from the oxide table at --oxygen-ppm
# (--oxygen-wire-angles): higher ppm, poorer wetting on the wire. Sahoo-Belton
# sigma(T, a_O) is on, and so are Marangoni and recoil. The wire inlet stays
# at 300 K. The neck box is refined three times in x, y and z (about 19 um);
# the rest of the track stays at 150 um.
#
# Wave 1 uses 4 ranks each, 12 in total, nice 10:
#   cal26  50 ppm   24 mm/s
#   cal29  100 ppm  24 mm/s
#   cal32  300 ppm  24 mm/s
# Wave 2 is the other feed rates (18 and 28 mm/s) and is not started here
# while wave 1 holds the rank budget. End 0.20 s, write every 0.05 s.
#
# Usage: launch_slit_sweep.sh [wave1|mesh]
#   mesh   write and check only cal29 (100 ppm, 24 mm/s), no solve
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
MODE=${1:-wave1}
# bashrc forwards "$@" into config.sh/setup, so drop the mode argument first.
set --
if ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
    echo "a solver is already running" >&2
    exit 1
fi
# bashrc reads variables it has not set yet, and a helper returns 1 when a
# ThirdParty library is the system one. nounset and errexit have to be off
# for that one source.
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

hot_plate() {
    local case_dir="$1"
    python3 - << PY
from pathlib import Path
p = Path("$case_dir") / "system/setFieldsDict"
s = p.read_text()
old = "            volScalarFieldValue alpha.metal 1\\n        );"
new = "            volScalarFieldValue alpha.metal 1\\n            volScalarFieldValue T 1100\\n        );"
n = s.count(old)
if n != 1:
    raise SystemExit(f"substrate block count {n} in {p}")
p.write_text(s.replace(old, new, 1))
print("substrate T set to 1100 in", p)
PY
    foamDictionary "$case_dir/0.orig/T" -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
}

gen_one() {
    local tag="$1" ppm="$2" feed="$3"
    local case="$ROOT/cases/wire_cavity_${tag}"
    echo "=== generate ${tag}: ${ppm} ppm, feed ${feed} m/s ==="
    python3 "$ROOT/generate_case.py" --case "$case" --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
        --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0.05 \
        --scan-speed 0.004 --wire-feed-speed "$feed" \
        --beam-azimuths 30,-30,180 \
        --beam-inclinations=-26,-26,-38 \
        --beam-powers 160,160,420 \
        --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
        --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
        --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
        --end-time 0.20 --write-interval 0.05 --np 4 --laser-ramp 2e-3 \
        --neck-refine 3 \
        --oxygen-ppm "$ppm" --oxygen-wire-angles \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 10 --theta-advancing 40 \
        --wire-sector \
        --wire-sector-half-angle 40 --wire-sector-blend 15 \
        --contact-force-factor 6 \
        --wire-pin-frame head \
        --rigid-substrate 100
    hot_plate "$case"
    grep -q "volScalarFieldValue T 1100" "$case/system/setFieldsDict"
    foamDictionary "$case/0.orig/T" -entry boundaryField/inletSubstrate/value | grep -q 1100
    foamDictionary "$case/0.orig/T" -entry boundaryField/wireInlet/value | grep -q 300
    grep -q "oxygenWireAnglesOnly true" "$case/constant/meltProperties"
    grep -q "marangoni           true" "$case/constant/meltProperties"
    grep -q "recoil      true" "$case/constant/meltProperties"
    echo "--- ${tag} windows ---"
    grep -n -E "thetaReceding|thetaAdvancing|chamberOxygenPpm|wireSectorHalfAngle|oxygenWireAnglesOnly" \
        "$case/constant/meltProperties" | head -n 40
}

run_one() {
    local tag="$1" ppm="$2" feed="$3"
    local case="$ROOT/cases/wire_cavity_${tag}"
    local log="$ROOT/results/calibration/${tag}_launch.log"
    {
        gen_one "$tag" "$ppm" "$feed"
        cd "$case"
        if [ "$MODE" = "mesh" ]; then
            MESH_ONLY=1 nice -n 10 ./Allrun 4
            echo "MESH_DONE ${tag}"
            grep -E "cells:|Max aspect ratio|Mesh OK|Failed" log.checkMesh || true
        else
            nice -n 10 ./Allrun 4
            python3 "$ROOT/scripts/quantify_pores.py" --case "$case" || true
            echo "SLIT_DONE ${tag}"
        fi
    } > "$log" 2>&1
}

if [ "$MODE" = "mesh" ]; then
    run_one cal29 100 0.024
    echo "MESH_ONLY finished, see results/calibration/cal29_launch.log"
    exit 0
fi

if [ "$MODE" != "wave1" ]; then
    echo "unknown mode: $MODE" >&2
    exit 1
fi

echo "WAVE1 cal26 (50 ppm), cal29 (100 ppm), cal32 (300 ppm) at 24 mm/s, 4 ranks each"
run_one cal26 50 0.024 &
p1=$!
run_one cal29 100 0.024 &
p2=$!
run_one cal32 300 0.024 &
p3=$!
fail=0
wait "$p1" || fail=1
wait "$p2" || fail=1
wait "$p3" || fail=1
echo "WAVE1_WAIT_DONE fail=$fail"
exit "$fail"
