#!/bin/bash
# Coarse screens together. One rank each: on this 35k-cell mesh a 10-rank
# run spent the step in MPI (~1.8 s/step) and one rank does ~0.24 s/step.
# Six ranks in total, under the 32-core cap. cal31 is launched separately.
DIR0="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR0/screens_launch.log") 2>&1
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
(
    flock 9
    echo 0 > /tmp/taosun03-lwded-slots
) 9>/tmp/taosun03-lwded-slots.lock
run_batch() {
    local name="$1"
    shift
    echo "${name}_START $(date --iso-8601=seconds)"
    local pids=()
    local s
    for s in "$@"; do
        "$s" &
        pids+=("$!")
    done
    local fail=0
    local pid
    for pid in "${pids[@]}"; do
        wait "$pid" || fail=1
    done
    if (( fail )); then
        echo "${name}_FAILED $(date --iso-8601=seconds)"
    else
        echo "${name}_DONE $(date --iso-8601=seconds)"
    fi
}

run_batch SCREENS \
    "$DIR/launch_cal32.sh" "$DIR/launch_cal33.sh" "$DIR/launch_cal34.sh" \
    "$DIR/launch_cal35.sh" "$DIR/launch_cal36.sh" "$DIR/launch_cal37.sh"
echo "SCREENS_DONE $(date --iso-8601=seconds)"
