#!/bin/bash
# cal55. Steeper rear beam, inclination -48 deg, aim z 0.70 mm.
# One rank, nice 10, inside the 32-rank cap.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal55_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal55"
tao_cal08_case "$CASE" \
    --end-time 0.28 --write-interval 0.14 --np "$NP" \
    --beam-inclinations=-26,-26,-48 \
    --beam-aim-heights 0.08e-3,0.08e-3,0.70e-3

tao_run "$NP" "$CASE"
tao_post cal55 "$CASE"
echo "CAL55_DONE"
