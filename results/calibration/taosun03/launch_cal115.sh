#!/bin/bash
# cal115. cal114 at 0.70 s scores 8 (trail 1.91 / lead 1.15 mm, plate wetted,
# 9/15 columns melted) but 4 of 10 wire cells recede at a mean of 29 deg,
# just under the 30 deg floor. Same plate and absorptivity, floor 15 deg.
# One rank, nice 10, to 0.55 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal115_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal115"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.65 \
    --end-time 0.55 --write-interval 0.10 --np "$NP" \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 15 --theta-advancing-wire 80 \
    --wire-sector \
    --theta-receding-wire-trail 15 --theta-advancing-wire-trail 80 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal115 "$CASE"
echo "CAL115_DONE"
