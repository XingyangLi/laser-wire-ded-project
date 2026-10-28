#!/bin/bash
# cal61. Cross of the best window (cal34, trail 60/140) with cal36's
# wire-heavy power (100+100+700 W, scan 3 mm/s, feed 20 mm/s).
# One rank, nice 10. Not the refined cal10 mesh.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal61_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal61"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --end-time 0.40 --write-interval 0.10 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 60 --theta-advancing-wire-trail 140 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal61 "$CASE"
echo "CAL61_DONE"
