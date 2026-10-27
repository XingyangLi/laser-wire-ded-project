#!/bin/bash
# cal47. Milder plate window 90/140 and force factor 8. cal08 beams.
# One rank. Concurrent with the other taosun03 screens. Cap is 32 ranks.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal47_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal47"
tao_cal08_case "$CASE" \
    --end-time 0.25 --write-interval 0.125 --np "$NP" \
    --theta-receding 90 --theta-advancing 140 \
    --contact-force-factor 8

tao_run "$NP" "$CASE"
tao_post cal47 "$CASE"
echo "CAL47_DONE"
