#!/bin/bash
# Time cal31's refined mesh with Scotch at NP ranks (default 4).
# Copies the finished probe mesh, so the running cal31 case is not touched.
# The ray deposit is a global min-reduction, so a z-split still hits the
# same cell. zSurface is a local column sum and can be wrong if Scotch cuts
# a column; the heat source is the check that matters.
DIR="$(cd "$(dirname "$0")" && pwd)"
NP="${1:-4}"
exec > >(tee -a "$DIR/cal31_scotch_np${NP}.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
if (( NP < 2 || NP > TAO_MAX_CORES )); then
    echo "scotch probe np must be 2..${TAO_MAX_CORES}" >&2
    exit 1
fi
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
SRC="$TAO_ROOT/cases/wire_cavity_cal31_probe"
CASE="$TAO_ROOT/cases/wire_cavity_cal31_scotch${NP}"
rm -rf "$CASE"
mkdir -p "$CASE"
cp -a "$SRC/constant" "$SRC/system" "$SRC/0" "$SRC/0.orig" "$CASE/" 2>/dev/null || true
if [[ ! -d "$CASE/constant/polyMesh" ]]; then
    echo "refined mesh missing in $SRC" >&2
    exit 1
fi
rm -rf "$CASE"/processor* "$CASE"/log.* "$CASE"/postProcessing
# Drop any solved times so this starts from the initial fields.
find "$CASE" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended \
    -regex '.*/[0-9]+(\.[0-9]+)?$' ! -name '0' -exec rm -rf {} +
tao_source_foam
cd "$CASE"
foamDictionary -entry endTime -set 0.00025 system/controlDict >/dev/null
foamDictionary -entry startFrom -set startTime system/controlDict >/dev/null
foamDictionary -entry writeInterval -set 0.00025 system/controlDict >/dev/null
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
decomposePar -force > log.decomposePar 2>&1
nice -n 10 mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel \
    > log.laserWireDEDFoam 2>&1
echo "SCOTCH_DONE np=${NP}"
