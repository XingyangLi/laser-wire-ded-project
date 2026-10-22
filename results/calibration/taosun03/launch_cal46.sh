#!/bin/bash
# cal46. Rear focus down at the foot (aim z 0.30 mm), powers 80+80+520 W, scan 3 mm/s.
# One rank. Concurrent with the other taosun03 screens. Cap is 32 ranks.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal46_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal46"
tao_cal08_case "$CASE" \
    --end-time 0.30 --write-interval 0.15 --np "$NP" \
    --beam-powers 80,80,520 \
    --beam-aim-heights 0.08e-3,0.08e-3,0.30e-3 \
    --scan-speed 0.003

tao_run "$NP" "$CASE"
tao_post cal46 "$CASE"
echo "CAL46_DONE"
