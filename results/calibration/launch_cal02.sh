#!/bin/bash
# Iteration 2 screening. Rear beam axis meets the wire flank near z = 0.75 mm
# (inward inclination). Front beams clip the wire foot and heat the plate.
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal02"
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
    --upstream 5e-3 --downstream 5e-3 --half-width 3.5e-3 \
    --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
    --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.10e-3 --feed-start 0.02 \
    --scan-speed 0.006 --wire-feed-speed 0.030 \
    --beam-azimuths 30,-30,180 \
    --beam-inclinations=-28,-28,-32 \
    --beam-powers 400,400,700 \
    --beam-radii-each 0.40e-3,0.40e-3,0.40e-3 \
    --beam-aim-radii 0.55e-3,0.55e-3,0.22e-3 \
    --beam-aim-heights 0.20e-3,0.20e-3,0.30e-3 \
    --end-time 0.16 --write-interval 0.04 --np 24 --laser-ramp 2e-3 \
    --contact-pinning --pin-wire --porosity --wire-cavity \
    --theta-receding 20 --theta-advancing 90 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-pin-frame head \
    --rigid-substrate 100
cd "$CASE"
./Allclean >/dev/null 2>&1 || true
./Allrun 24
python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" || true
echo "CAL02_DONE"
