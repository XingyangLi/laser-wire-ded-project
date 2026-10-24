#!/bin/bash
# cal51. Tighter spots, 0.18 mm. Same aims and power as cal08, so the footprint cannot spread as far.
# One rank, nice 10, inside the 32-rank cap.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal51_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal51"
tao_cal08_case "$CASE" \
    --end-time 0.28 --write-interval 0.14 --np "$NP" \
    --beam-radii-each 0.18e-3,0.18e-3,0.18e-3

tao_run "$NP" "$CASE"
tao_post cal51 "$CASE"
echo "CAL51_DONE"
