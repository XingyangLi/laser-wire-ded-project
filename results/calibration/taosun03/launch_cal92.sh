#!/bin/bash
# cal92. Front spots 60 W, rear 700 W. Between the 50 W fronts that
# kept the neck and the 80 W fronts. Scan 3 mm/s, feed 20 mm/s.
# One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal92_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal92"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 60,60,700 \
    --end-time 0.50 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal92 "$CASE"
echo "CAL92_DONE"
