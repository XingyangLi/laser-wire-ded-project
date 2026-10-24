#!/bin/bash
# Iteration 6. The contact-angle force did not set the foot angle (cal04, cal05).
# Shrink the heated footprint onto the wire and the immediate foot, slow the
# scan, and slow the feed so the wire is consumed and the melt has to pile up.
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal06"
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
    --upstream 4e-3 --downstream 6e-3 --half-width 3.0e-3 \
    --substrate-thickness 2e-3 --gas-height 4.0e-3 --gas-uniform-height 2.8e-3 \
    --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0.06 \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-azimuths 18,-18,180 \
    --beam-inclinations=-24,-24,-22 \
    --beam-powers 220,220,320 \
    --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
    --beam-aim-radii 0.42e-3,0.42e-3,0.20e-3 \
    --beam-aim-heights 0.20e-3,0.20e-3,0.45e-3 \
    --end-time 0.32 --write-interval 0.08 --np 24 --laser-ramp 2e-3 \
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
echo "CAL06_DONE"
