#!/bin/bash
# Restart cases/wire_cavity_cal31 from its latest time with Scotch and NP ranks.
# Does not remesh and does not Allclean. Refuses to start if that solver is live.
DIR="$(cd "$(dirname "$0")" && pwd)"
NP="${1:-8}"
exec > >(tee -a "$DIR/cal31_resume_np${NP}.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
if (( NP < 2 || NP > TAO_MAX_CORES )); then
    echo "resume np must be 2..${TAO_MAX_CORES}" >&2
    exit 1
fi
CASE="$TAO_ROOT/cases/wire_cavity_cal31"
for d in /proc/[0-9]*; do
    cwd=$(readlink "$d/cwd" 2>/dev/null || true)
    if [[ "$cwd" == "$CASE" ]]; then
        comm=$(cat "$d/comm" 2>/dev/null || true)
        if [[ "$comm" == "laserWireDEDFoam" ]]; then
            echo "cal31 is still running (pid ${d#/proc/})" >&2
            exit 1
        fi
    fi
done
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_source_foam
cd "$CASE"
rm -rf processor*
cat > system/decomposeParDict << EOF
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      decomposeParDict;
}
numberOfSubdomains ${NP};
method          scotch;
EOF
# Keep the written end time. Continue from the newest time directory.
latest=$(find . -mindepth 1 -maxdepth 1 -type d -regextype posix-extended \
    -regex './[0-9]+(\.[0-9]+)?$' -printf '%f\n' | sort -g | tail -1)
echo "resuming from ${latest:-0} with scotch np=${NP}"
if [[ -f log.laserWireDEDFoam ]]; then
    cp -a log.laserWireDEDFoam "log.laserWireDEDFoam.np1"
fi
foamDictionary -entry startFrom -set latestTime system/controlDict >/dev/null
decomposePar -force > log.decomposePar.scotch 2>&1
nice -n 10 mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel \
    > log.laserWireDEDFoam 2>&1
tao_post cal31 "$CASE"
echo "CAL31_RESUME_DONE"
