#!/bin/bash
# cal83. The 45/120 trailing window on cal36's 100+100+700 W.
# The 60/140 window on this power (cal61) left most of the wire line receding.
# Scan 3 mm/s, feed 20 mm/s. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal83_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal83"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --end-time 0.40 --write-interval 0.10 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 45 --theta-advancing-wire-trail 120 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal83 "$CASE"
echo "CAL83_DONE"
