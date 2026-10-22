#!/bin/bash
# cal65. The two score-8 levers plus the best window: 100+100+700 W,
# scan 2 mm/s, feed 20 mm/s, trailing window 60/140. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal65_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal65"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --end-time 0.55 --write-interval 0.15 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 60 --theta-advancing-wire-trail 140 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal65 "$CASE"
echo "CAL65_DONE"
