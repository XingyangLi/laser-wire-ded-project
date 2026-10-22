#!/bin/bash
# cal54. Scan 2.5 mm/s, feed 22 mm/s. Between cal08 and the slow dwell.
# One rank, nice 10, inside the 32-rank cap.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal54_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal54"
tao_cal08_case "$CASE" \
    --end-time 0.36 --write-interval 0.12 --np "$NP" \
    --scan-speed 0.0025 --wire-feed-speed 0.022

tao_run "$NP" "$CASE"
tao_post cal54 "$CASE"
echo "CAL54_DONE"
