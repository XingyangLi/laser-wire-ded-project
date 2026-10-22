#!/bin/bash
# cal79. cal58's 80+80+500 W at scan 2 mm/s, feed 16 mm/s, plus the
# 60/140 trailing window. That window was the best one on the cal08 beams.
# One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal79_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal79"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.016 \
    --beam-powers 80,80,500 \
    --end-time 0.45 --write-interval 0.15 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 60 --theta-advancing-wire-trail 140 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal79 "$CASE"
echo "CAL79_DONE"
