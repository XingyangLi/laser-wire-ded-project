#!/bin/bash
# cal59. Cross of the best window (cal34, trail 60/140) with the taller
# section of cal35 (scan 2 mm/s, feed 18 mm/s, powers 120+120+560 W).
# One rank, nice 10. Not the refined cal10 mesh.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal59_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal59"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.018 \
    --beam-powers 120,120,560 \
    --end-time 0.60 --write-interval 0.20 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 60 --theta-advancing-wire-trail 140 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal59 "$CASE"
echo "CAL59_DONE"
