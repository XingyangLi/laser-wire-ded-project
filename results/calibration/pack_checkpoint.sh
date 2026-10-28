#!/bin/bash
# Pack a compact restart of a finished track case.
# Mesh, dictionaries and one reconstructed time. No processor directories.
#
#   PACK_CASE   source case (default cases/wire_cavity_cal95b)
#   PACK_TIME   time directory (default 0.8)
#   PACK_NAME   checkpoint name (default the case tag)
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE=${PACK_CASE:-$ROOT/cases/wire_cavity_cal95b}
TIME=${PACK_TIME:-0.8}
NAME=${PACK_NAME:-$(basename "$CASE" | sed 's/wire_cavity_//')}
DEST="$ROOT/results/calibration/checkpoints/$NAME"
set +e
set +u
set +o pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -e
set -u
set -o pipefail
cd "$CASE"
if [ ! -d "$TIME" ]; then
    reconstructPar -time "$TIME" > "$ROOT/results/calibration/${NAME}_reconstruct.log" 2>&1
fi
rm -rf "$DEST"
mkdir -p "$DEST/constant" "$DEST/system"
cp -a constant/polyMesh constant/meltProperties constant/transportProperties \
    constant/turbulenceProperties "$DEST/constant/" 2>/dev/null || true
# g is sometimes a separate file
if [ -f constant/g ]; then cp -a constant/g "$DEST/constant/"; fi
cp -a system/controlDict system/fvSchemes system/fvSolution \
    system/decomposeParDict system/blockMeshDict system/setFieldsDict \
    system/topoSetDict system/createPatchDict "$DEST/system/"
cp -a "$TIME" "$DEST/$TIME"
# Drop heavy uniform/time state; the field values are the restart.
rm -rf "$DEST/$TIME/uniform"
cat > "$DEST/README.md" << EOF
# Restart checkpoint $NAME

Reconstructed fields at t = $TIME s. The mesh is the undecomposed
\`constant/polyMesh\`. Copy this directory to a new case, rename \`$TIME\` to
\`0\` if the pin window should start at t = 0, or keep the time name and set
\`startFrom latestTime\`.

Source case: \`$CASE\`.

Recipe that produced it: \`results/calibration/launch_track120.sh\` with
\`TRACK_TAG=$NAME\`. Equal beam powers 246.6667/246.6667/246.6666 W
(740 W total), azimuths 60/−60/180, inclination 15°, plate spots at
0.55 mm from the wire, substrate 1100 K, plate window 10°/40°,
wire inlet 300 K, feed 24 mm/s, scan 4 mm/s.
EOF
echo "packed $DEST"
du -sh "$DEST"
