#!/bin/bash
# cal82. The 45/120 trailing window, which grew a 1.91 mm trail on the
# cal08 beams, on the 50+50+650 W split that kept the leading crest lowest.
# Scan 3 mm/s, feed 18 mm/s. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal82_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal82"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.018 \
    --beam-powers 50,50,650 \
    --end-time 0.45 --write-interval 0.15 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 45 --theta-advancing-wire-trail 120 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal82 "$CASE"
echo "CAL82_DONE"
