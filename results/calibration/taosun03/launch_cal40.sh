#!/bin/bash
# cal40. Trailing window 20/90. A sticky receding angle on the wake face.
# One rank. Concurrent with the other taosun03 screens. Cap is 32 ranks.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal40_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal40"
tao_cal08_case "$CASE" \
    --end-time 0.28 --write-interval 0.14 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 20 --theta-advancing-wire-trail 90 \
    --wire-sector-half-angle 90 --wire-sector-blend 30

tao_run "$NP" "$CASE"
tao_post cal40 "$CASE"
echo "CAL40_DONE"
