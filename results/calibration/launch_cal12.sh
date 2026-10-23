#!/bin/bash
# cal12. cal36's wire-heavy split (100+100+700 W, scan 3 mm/s, feed 20 mm/s)
# on the refined mesh, with cal10's trailing window (60/140 within 90 deg of +x).
# Twelve ranks, nice 10. End 0.80 s.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/cal12_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal12"
if ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
    echo "a solver is already running" >&2
    exit 1
fi
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
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-azimuths 30,-30,180 \
    --beam-inclinations=-26,-26,-38 \
    --beam-powers 100,100,700 \
    --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
    --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
    --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
    --end-time 0.80 --write-interval 0.20 --np 12 --laser-ramp 2e-3 \
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
echo "CAL12_DONE"
