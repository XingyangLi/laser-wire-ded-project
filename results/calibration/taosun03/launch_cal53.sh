#!/bin/bash
# cal53. Feed 32 mm/s at the cal08 scan. Steady section about 6.3 mm^2.
# One rank, nice 10, inside the 32-rank cap.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal53_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal53"
tao_cal08_case "$CASE" \
    --end-time 0.30 --write-interval 0.15 --np "$NP" \
    --wire-feed-speed 0.032

tao_run "$NP" "$CASE"
tao_post cal53 "$CASE"
echo "CAL53_DONE"
