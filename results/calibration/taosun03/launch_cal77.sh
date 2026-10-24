#!/bin/bash
# cal77. cal36's 100+100+700 W with a shallower rear beam, inclination -28 deg.
# Steeper (-48 deg) on the cal08 beams did not raise the crest. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal77_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal77"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --beam-inclinations=-26,-26,-28 \
    --end-time 0.36 --write-interval 0.12 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal77 "$CASE"
echo "CAL77_DONE"
