#!/bin/bash
# cal58. Front spots cut to 80 W, rear 500 W, scan 2 mm/s, feed 16 mm/s.
# One rank, nice 10, inside the 32-rank cap.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal58_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal58"
tao_cal08_case "$CASE" \
    --end-time 0.34 --write-interval 0.17 --np "$NP" \
    --beam-powers 80,80,500 \
    --scan-speed 0.002 --wire-feed-speed 0.016

tao_run "$NP" "$CASE"
tao_post cal58 "$CASE"
echo "CAL58_DONE"
