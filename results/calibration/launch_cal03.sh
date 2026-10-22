#!/bin/bash
# Iteration 3 screening. Narrower spots so the pool does not wet out to 3 mm,
# and a lower rear-beam hit so the wire line stays nearer the bead crown.
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal03"
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
    --beam-azimuths 22,-22,180 \
    --beam-inclinations=-16,-16,-30 \
    --beam-powers 350,350,520 \
    --beam-radii-each 0.32e-3,0.32e-3,0.32e-3 \
    --beam-aim-radii 0.85e-3,0.85e-3,0.32e-3 \
    --beam-aim-heights 0.10e-3,0.10e-3,0.25e-3 \
    --end-time 0.70 --write-interval 0.05 --np 24 --laser-ramp 2e-3 \
    --contact-pinning --pin-wire --porosity --wire-cavity \
    --theta-receding 20 --theta-advancing 90 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-pin-frame head \
    --rigid-substrate 100
cd "$CASE"
./Allclean >/dev/null 2>&1 || true
./Allrun 24
python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" || true
echo "CAL03_DONE"
