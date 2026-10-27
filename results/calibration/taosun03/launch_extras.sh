#!/bin/bash
# Wider angle sweep and dome-shape screens, one rank each.
# Started while cal32-cal37 and cal31 are already running.
# 12 ranks here. With those seven, the total stays under 32.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/extras_launch.log") 2>&1
set -euo pipefail
echo "EXTRAS_START $(date --iso-8601=seconds)"
pids=()
for s in cal38 cal39 cal40 cal41 cal42 cal43 cal44 cal45 cal46 cal47 cal48 cal49; do
    "$DIR/launch_${s}.sh" &
    pids+=("$!")
done
fail=0
for pid in "${pids[@]}"; do
    wait "$pid" || fail=1
done
if (( fail )); then
    echo "EXTRAS_FAILED $(date --iso-8601=seconds)"
else
    echo "EXTRAS_DONE $(date --iso-8601=seconds)"
fi
