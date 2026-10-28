#!/bin/bash
# cal89. cal36's 100+100+700 W at scan 3.5 mm/s, feed 22 mm/s.
# Between the 3 mm/s run, whose lead fell, and the 5 mm/s freeze test.
# One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal89_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal89"
tao_cal08_case "$CASE" \
    --scan-speed 0.0035 --wire-feed-speed 0.022 \
    --beam-powers 100,100,700 \
    --end-time 0.45 --write-interval 0.15 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal89 "$CASE"
echo "CAL89_DONE"
