#!/bin/bash
# cal70. cal43's 50+50+650 W plus the 60/140 trailing window.
# Scan 3 mm/s, feed 18 mm/s. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal70_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal70"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.018 \
    --beam-powers 50,50,650 \
    --end-time 0.40 --write-interval 0.10 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 60 --theta-advancing-wire-trail 140 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal70 "$CASE"
echo "CAL70_DONE"
