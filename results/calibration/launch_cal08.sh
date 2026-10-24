#!/bin/bash
# Iteration 8. cal07 built a 1.45 mm mound but the metal skirted out to a
# fillet and the two sides were the same height. Keep the rear spot on the
# trailing flank (axis ~0.9 mm, outer ray on the foot) and only kiss the
# plate with the front spots, so the melt has to pile up instead of spreading.
# Scan 4 mm/s and feed 20 mm/s: steady section 3.93 mm^2, and the wire core
# has time to melt.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/cal08_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal08"
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
    --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
    --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
    --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0.05 \
    --scan-speed 0.004 --wire-feed-speed 0.020 \
    --beam-azimuths 30,-30,180 \
    --beam-inclinations=-26,-26,-38 \
    --beam-powers 160,160,420 \
    --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
    --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
    --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
    --end-time 1.50 --write-interval 0.25 --np 24 --laser-ramp 2e-3 \
    --contact-pinning --pin-wire --porosity --wire-cavity \
    --theta-receding 110 --theta-advancing 150 \
    --theta-receding-wire 30 --theta-advancing-wire 90 \
    --contact-force-factor 6 \
    --no-marangoni \
    --wire-pin-frame head \
    --rigid-substrate 100
cd "$CASE"
./Allclean >/dev/null 2>&1 || true
./Allrun 24
python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" || true
echo "CAL08_DONE"
