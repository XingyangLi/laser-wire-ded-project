#!/bin/bash
# cal52. Wire gap 0.02 mm so the feed enters the pool immediately.
# One rank, nice 10, inside the 32-rank cap.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal52_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal52"
tao_cal08_case "$CASE" \
    --end-time 0.28 --write-interval 0.14 --np "$NP" \
    --wire-gap 0.02e-3

tao_run "$NP" "$CASE"
tao_post cal52 "$CASE"
echo "CAL52_DONE"
