#!/bin/bash
# Iteration 7. cal06 melted a band at z ~ 2 mm and the plate stayed dry.
# These beams meet the wire at the foot (rear axis z ~ 0.4 mm, inner ray
# z ~ 0.9 mm) and put a narrow spot on the plate just outside the wire.
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal07"
cd "$ROOT/solver"
set +euo pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -euo pipefail
./Allwmake
export PATH="${FOAM_USER_APPBIN}:$PATH"
hash -r
cd "$ROOT"
python3 generate_case.py --case "$CASE" --laser-config triple \
    --wire-type solid --material 316L --resolution coarse --domain-y half \
    --upstream 4e-3 --downstream 6e-3 --half-width 3.5e-3 \
    --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
    --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0.05 \
    --scan-speed 0.003 --wire-feed-speed 0.022 \
    --beam-azimuths 20,-20,180 \
    --beam-inclinations=-14,-14,-32 \
    --beam-powers 300,300,400 \
    --beam-radii-each 0.30e-3,0.30e-3,0.30e-3 \
    --beam-aim-radii 0.62e-3,0.62e-3,0.38e-3 \
    --beam-aim-heights 0.10e-3,0.10e-3,0.20e-3 \
    --end-time 0.40 --write-interval 0.08 --np 24 --laser-ramp 2e-3 \
    --contact-pinning --pin-wire --porosity --wire-cavity \
    --theta-receding 70 --theta-advancing 125 \
    --theta-receding-wire 20 --theta-advancing-wire 150 \
    --contact-force-factor 4 \
    --no-marangoni \
    --wire-pin-frame head \
    --rigid-substrate 100
cd "$CASE"
./Allclean >/dev/null 2>&1 || true
./Allrun 24
python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" || true
echo "CAL07_DONE"
