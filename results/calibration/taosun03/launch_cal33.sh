#!/bin/bash
# cal33. Trailing wire window 75/160 on the cal08 beams. Coarse screen.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal33_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal33"
tao_cal08_case "$CASE" \
    --end-time 0.30 --write-interval 0.10 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 75 --theta-advancing-wire-trail 160 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal33 "$CASE"
echo "CAL33_DONE"
