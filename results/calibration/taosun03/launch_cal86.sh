#!/bin/bash
# cal86. cal36's 100+100+700 W with the wire gap closed to 0.02 mm.
# Asks whether a closer wire lets the wake bridge. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal86_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal86"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --wire-gap 0.02e-3 \
    --end-time 0.45 --write-interval 0.15 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal86 "$CASE"
echo "CAL86_DONE"
