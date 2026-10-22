#!/bin/bash
# cal10. cal08 beams, plus a wide pin on the trailing face of the wire
# (60/140 within 90 deg of +x, blended over 30 deg to the front 25/70).
# --wire-refine 2 is about 38 um in x and y, enough to see a gap behind the wire.
# TaoSun-01 is shared: 12 ranks and a lower priority, never 24.
# End 0.30 s is the upper plan. Half of the cal09 24-rank rate makes that
# about 11 h, past the ~9 h still in the 24 h budget, so the first minutes
# of this 12-rank log decide whether endTime stays or is cut.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/cal10_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal10"
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
    --end-time 0.30 --write-interval 0.10 --np 12 --laser-ramp 2e-3 \
    --wire-refine 2 \
    --contact-pinning --pin-wire --porosity --wire-cavity \
    --theta-receding 110 --theta-advancing 150 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 60 --theta-advancing-wire-trail 140 \
    --wire-sector-half-angle 90 --wire-sector-blend 30 \
    --contact-force-factor 6 \
    --no-marangoni \
    --wire-pin-frame head \
    --rigid-substrate 100
cd "$CASE"
./Allclean >/dev/null 2>&1 || true
nice -n 10 ./Allrun 12
python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" || true
echo "CAL10_DONE"
