#!/bin/bash
# cal43. Rear-heavy power. 50+50+650 W, scan 3 mm/s, feed 18 mm/s.
# One rank. Concurrent with the other taosun03 screens. Cap is 32 ranks.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal43_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal43"
tao_cal08_case "$CASE" \
    --end-time 0.32 --write-interval 0.16 --np "$NP" \
    --beam-powers 50,50,650 \
    --scan-speed 0.003 --wire-feed-speed 0.018

tao_run "$NP" "$CASE"
tao_post cal43 "$CASE"
echo "CAL43_DONE"
