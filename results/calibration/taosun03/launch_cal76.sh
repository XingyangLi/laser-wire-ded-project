#!/bin/bash
# cal76. The 50+50+650 W split with the 30/100 trailing window.
# That window matched 60/140 on the cal08 beams. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal76_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal76"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.018 \
    --beam-powers 50,50,650 \
    --end-time 0.40 --write-interval 0.10 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal76 "$CASE"
echo "CAL76_DONE"
