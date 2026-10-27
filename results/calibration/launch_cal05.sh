#!/bin/bash
# Iteration 5. cal04 asked for a 70 deg receding angle but the apparent angle
# stayed near 50 deg and the pool stayed a 3 mm fillet. Marangoni is off and
# the Young force is scaled by 4 (still capped at 2*sigma/h^2) so the line
# can pull the melt up into a dome.
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal05"
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
    --upstream 5e-3 --downstream 6e-3 --half-width 3.5e-3 \
    --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
    --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.10e-3 --feed-start 0.05 \
    --scan-speed 0.004 --wire-feed-speed 0.030 \
    --beam-azimuths 25,-25,180 \
    --beam-inclinations=-18,-18,-26 \
    --beam-powers 420,420,680 \
    --beam-radii-each 0.38e-3,0.38e-3,0.38e-3 \
    --beam-aim-radii 0.72e-3,0.72e-3,0.28e-3 \
    --beam-aim-heights 0.15e-3,0.15e-3,0.40e-3 \
    --end-time 0.30 --write-interval 0.06 --np 24 --laser-ramp 2e-3 \
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
echo "CAL05_DONE"
