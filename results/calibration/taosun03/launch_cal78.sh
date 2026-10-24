#!/bin/bash
# cal78. cal36's 100+100+700 W with the tight 15/50 wire window, no sector.
# That window matched cal34 on the cal08 beams. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal78_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal78"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --theta-receding-wire 15 --theta-advancing-wire 50 \
    --end-time 0.36 --write-interval 0.12 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal78 "$CASE"
echo "CAL78_DONE"
