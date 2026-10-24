#!/bin/bash
# cal113. cal111's heated 20/55 plate grew the fused dome (trail 2.06 mm,
# lead 0.99 mm at 0.60 s) but the wire angle sat on the 20 deg trail floor,
# so 6 of 10 cells receded and the line stayed 0.6 mm below the crest.
# Floor 10 deg, ceiling 70 deg, on a 60 deg trailing sector, to 0.65 s.
# One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal113_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal113"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.55 \
    --preheat 900 \
    --end-time 0.65 --write-interval 0.10 --np "$NP" \
    --theta-receding 20 --theta-advancing 55 \
    --theta-receding-wire 10 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 10 --theta-advancing-wire-trail 70 \
    --wire-sector-half-angle 60 --wire-sector-blend 20
tao_run "$NP" "$CASE"
tao_post cal113 "$CASE"
echo "CAL113_DONE"
