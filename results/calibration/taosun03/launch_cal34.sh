#!/bin/bash
# cal34. Trailing wire window 60/140 on the cal08 beams, coarse, to 0.30 s.
# Matched with cal32 and cal33. This is not cal10: cal10 is the refined
# 60/140 run on TaoSun-01 and is left to that machine.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal34_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=10
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal34"
tao_cal08_case "$CASE" \
    --end-time 0.30 --write-interval 0.10 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 60 --theta-advancing-wire-trail 140 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal34 "$CASE"
echo "CAL34_DONE"
