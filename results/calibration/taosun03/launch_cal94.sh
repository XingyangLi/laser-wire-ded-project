#!/bin/bash
# cal94. cal81's slow scan with the front spots raised from 40 W to 60 W.
# Rear 560 W, scan 2 mm/s, feed 16 mm/s. Asks whether 20 W more in front
# removes the locked foot pore without lifting the lead. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal94_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal94"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.016 \
    --beam-powers 60,60,560 \
    --end-time 0.55 --write-interval 0.11 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal94 "$CASE"
echo "CAL94_DONE"
