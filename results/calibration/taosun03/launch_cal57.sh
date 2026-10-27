#!/bin/bash
# cal57. Uniform wire window 45/110, no trailing sector.
# One rank, nice 10, inside the 32-rank cap.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal57_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal57"
tao_cal08_case "$CASE" \
    --end-time 0.28 --write-interval 0.14 --np "$NP" \
    --theta-receding-wire 45 --theta-advancing-wire 110

tao_run "$NP" "$CASE"
tao_post cal57 "$CASE"
echo "CAL57_DONE"
