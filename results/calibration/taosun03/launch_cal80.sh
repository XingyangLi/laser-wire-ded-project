#!/bin/bash
# cal80. cal58's 80+80+500 W and scan 2 mm/s, with the feed raised to 22 mm/s.
# Extra wire on the heat split that kept the leading crest at 1.15 mm.
# One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal80_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal80"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.022 \
    --beam-powers 80,80,500 \
    --end-time 0.45 --write-interval 0.15 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal80 "$CASE"
echo "CAL80_DONE"
