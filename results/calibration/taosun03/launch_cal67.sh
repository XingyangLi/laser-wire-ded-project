#!/bin/bash
# cal67. cal36's 100+100+700 W with the rear aim lowered from 0.55 mm to
# 0.35 mm, so more of that spot falls on the trailing bead. One rank.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal67_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal67"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --beam-aim-heights 0.08e-3,0.08e-3,0.35e-3 \
    --end-time 0.40 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal67 "$CASE"
echo "CAL67_DONE"
