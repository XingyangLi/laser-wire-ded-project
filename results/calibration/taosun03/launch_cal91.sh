#!/bin/bash
# cal91. Front spots 40 W, rear 650 W, scan 3 mm/s, feed 18 mm/s.
# cal81 got a 0.69 mm lead with 40 W fronts at 2 mm/s, and locked a foot pore.
# The faster scan asks whether that pore was the long dwell. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal91_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal91"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.018 \
    --beam-powers 40,40,650 \
    --end-time 0.50 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal91 "$CASE"
echo "CAL91_DONE"
