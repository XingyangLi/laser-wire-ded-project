#!/bin/bash
# cal37. Steeper plate window, 150/170, force factor 10. Earlier iterations
# left the foot near 50 deg because the heated footprint sets it. This screen
# checks whether a higher floor and a stronger Young force move that foot.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal37_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal37"
tao_cal08_case "$CASE" \
    --theta-receding 150 --theta-advancing 170 \
    --contact-force-factor 10 \
    --end-time 0.25 --write-interval 0.125 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal37 "$CASE"
echo "CAL37_DONE"
