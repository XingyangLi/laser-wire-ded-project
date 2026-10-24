#!/bin/bash
# cal90. cal36's 100+100+700 W with the contact force factor raised from 6 to 10.
# One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal90_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal90"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --contact-force-factor 10 \
    --end-time 0.40 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal90 "$CASE"
echo "CAL90_DONE"
