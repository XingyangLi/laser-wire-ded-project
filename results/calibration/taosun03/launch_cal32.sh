#!/bin/bash
# cal32. Trailing wire window 45/120 on the cal08 beams. Coarse screen.
# Front of the wire stays 25/70. One rank: 10 ranks were slower on this mesh.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal32_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal32"
tao_cal08_case "$CASE" \
    --end-time 0.30 --write-interval 0.10 --np "$NP" \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 45 --theta-advancing-wire-trail 120 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal32 "$CASE"
echo "CAL32_DONE"
