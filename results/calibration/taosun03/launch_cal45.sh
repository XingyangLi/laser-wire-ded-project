#!/bin/bash
# cal45. Rear focus higher on the flank (aim z 0.95 mm) so the wire melts into a taller cap.
# One rank. Concurrent with the other taosun03 screens. Cap is 32 ranks.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal45_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal45"
tao_cal08_case "$CASE" \
    --end-time 0.28 --write-interval 0.14 --np "$NP" \
    --beam-aim-heights 0.08e-3,0.08e-3,0.95e-3

tao_run "$NP" "$CASE"
tao_post cal45 "$CASE"
echo "CAL45_DONE"
