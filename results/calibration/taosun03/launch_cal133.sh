#!/bin/bash
# Feed 28 mm/s with the rear spot at 600 W, to freeze the multi-cell region cal125 held. To 0.70 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal133_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal133"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.028 \
    --beam-powers 100,100,600 \
    --absorptivity-substrate 0.65 \
    --end-time 0.70 --write-interval 0.10 --np "$NP" \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal133 "$CASE"
echo "CAL133_DONE"
