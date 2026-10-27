#!/bin/bash
# cal56. Weaker Young force, factor 2, cal08 angles.
# One rank, nice 10, inside the 32-rank cap.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal56_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal56"
tao_cal08_case "$CASE" \
    --end-time 0.25 --write-interval 0.125 --np "$NP" \
    --contact-force-factor 2

tao_run "$NP" "$CASE"
tao_post cal56 "$CASE"
echo "CAL56_DONE"
