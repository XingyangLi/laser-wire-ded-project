#!/bin/bash
# cal38. Trailing window 30/100. Narrower than the 45/120 screen.
# One rank. Concurrent with the other taosun03 screens. Cap is 32 ranks.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal38_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal38"
tao_cal08_case "$CASE" \
    --end-time 0.28 --write-interval 0.14 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
    --wire-sector-half-angle 90 --wire-sector-blend 30

tao_run "$NP" "$CASE"
tao_post cal38 "$CASE"
echo "CAL38_DONE"
