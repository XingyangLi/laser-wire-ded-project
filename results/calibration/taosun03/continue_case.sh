#!/bin/bash
# Continue an existing case to a new end time. Does not remesh or Allclean.
# Usage: continue_case.sh cal32 0.55
DIR="$(cd "$(dirname "$0")" && pwd)"
TAG="${1:?tag}"
END="${2:?end time}"
exec > >(tee -a "$DIR/${TAG}_continue.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
CASE="$TAO_ROOT/cases/wire_cavity_${TAG}"
if [[ ! -d "$CASE" ]]; then
    echo "no case $CASE" >&2
    exit 1
fi
for d in /proc/[0-9]*; do
    cwd=$(readlink "$d/cwd" 2>/dev/null || true)
    comm=$(cat "$d/comm" 2>/dev/null || true)
    if [[ "$cwd" == "$CASE" && "$comm" == "laserWireDEDFoam" ]]; then
        echo "$TAG is still running" >&2
        exit 0
    fi
done
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_source_foam
cd "$CASE"
foamDictionary -entry endTime -set "$END" system/controlDict >/dev/null
foamDictionary -entry startFrom -set latestTime system/controlDict >/dev/null
echo "CONTINUE $TAG to $END $(date --iso-8601=seconds)"
nice -n 10 laserWireDEDFoam > log.laserWireDEDFoam.continue 2>&1
tao_post "$TAG" "$CASE"
echo "CONTINUE_${TAG}_DONE"
