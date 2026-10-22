#!/bin/bash
# cal44. Longer dwell. Scan 1.5 mm/s, feed 14 mm/s, section about 7.3 mm^2.
# One rank. Concurrent with the other taosun03 screens. Cap is 32 ranks.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal44_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal44"
tao_cal08_case "$CASE" \
    --end-time 0.36 --write-interval 0.12 --np "$NP" \
    --scan-speed 0.0015 --wire-feed-speed 0.014

tao_run "$NP" "$CASE"
tao_post cal44 "$CASE"
echo "CAL44_DONE"
