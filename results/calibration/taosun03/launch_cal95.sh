#!/bin/bash
# cal95. The 50+50+650 W split that dropped the lead to 0.54 mm,
# at scan 2.5 mm/s instead of 2 mm/s. Feed 20 mm/s. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal95_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal95"
tao_cal08_case "$CASE" \
    --scan-speed 0.0025 --wire-feed-speed 0.020 \
    --beam-powers 50,50,650 \
    --end-time 0.48 --write-interval 0.12 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal95 "$CASE"
echo "CAL95_DONE"
