#!/bin/bash
# Cut the solid wire out of a formed equilateral-beam track and impose the
# trailing line pin. The pool and the bead stay as they were. Lasers stay on.
#
#   PIN_SRC    track case (default cases/wire_cavity_cal90)
#   PIN_TIME   time directory to continue from (default: latest)
#   PIN_TAG    new case tag (default cal91)
#   PIN_EXTRA  seconds to run after the cut (default 0.02)
#   PIN_SKIP_BUILD
#
# 12 ranks, nice 10. Feed 0.024. linePin on, pinWire off.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/pin_on_track_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
SRC=${PIN_SRC:-$ROOT/cases/wire_cavity_cal95b}
TAG=${PIN_TAG:-cal96}
EXTRA=${PIN_EXTRA:-0.01}
FEED=${PIN_FEED:-0.024}
PPM=${PIN_PPM:-300}
NP=${PIN_NP:-12}
if [ "${PIN_PARALLEL:-0}" != 1 ] && ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
    echo "a solver is already running" >&2
    exit 1
fi
set +e
set +u
set +o pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -e
set -u
set -o pipefail
export PATH="${FOAM_USER_APPBIN}:$PATH"
hash -r
if [ "${PIN_SKIP_BUILD:-0}" != 1 ]; then
    cd "$ROOT/solver"
    ./Allwmake
    cd "$ROOT"
fi

if [ -z "${PIN_TIME:-}" ]; then
    PIN_TIME=$(python3 - << PY
from pathlib import Path
root = Path("$SRC") / "processor0"
names = []
for p in root.iterdir():
    if p.is_dir() and (p / "alpha.metal").is_file():
        try:
            names.append((float(p.name), p.name))
        except ValueError:
            pass
if not names:
    raise SystemExit("no solver time in $SRC/processor0")
names.sort()
print(names[-1][1])
PY
)
fi

case="$ROOT/cases/wire_cavity_${TAG}"
log="$ROOT/results/calibration/${TAG}_launch.log"
{
    echo "=== true-wall pin ${TAG} from ${SRC} time ${PIN_TIME}, extra ${EXTRA} s ==="
    cd "$SRC"
    reconstructPar -time "$PIN_TIME" > "$ROOT/results/calibration/${TAG}_reconstruct.log" 2>&1
    rm -rf "$case"
    mkdir -p "$case/0"
    cp -a "$SRC/constant" "$SRC/system" "$case/"
    rm -rf "$case/processor"*
    cp -a "$SRC/$PIN_TIME/." "$case/0/"
    # The cut reads 0/. The track time is the new initial field.
    cd "$case"
    python3 "$ROOT/results/calibration/check_beam_azimuths.py" "$case"
    python3 "$ROOT/results/calibration/cut_wire_wall.py" --case "$case" --write-dict
    # topoSet of the wire cylinder uses the dict written above.
    topoSet -dict system/topoSetDict.wireCut > log.topoSet.wireCut 2>&1
    subsetMesh -overwrite -patch wireWall keepCells > log.subsetMesh 2>&1
    python3 "$ROOT/results/calibration/cut_wire_wall.py" \
        --case "$case" --apply --line-pin --feed "$FEED" \
        --theta-a 140 --theta-r 40
    python3 - << 'PY'
from pathlib import Path
import re
p = Path("constant/meltProperties")
text = p.read_text()
text2, n = re.subn(r"(pinWire\s+)true", r"\1false", text, count=1)
if n != 1:
    raise SystemExit("pinWire true was not in meltProperties")
p.write_text(text2)
print("pinWire set false")
PY
    grep -Eq 'pinWire[[:space:]]+false' constant/meltProperties
    grep -q "linePin" constant/meltProperties
    # Fields live in 0/, so the pin window starts at t = 0 on the formed bead.
    # Feed starts immediately. The listed extra time is that window.
    foamDictionary constant/meltProperties -entry wire/tFeedStart -set 0 > /dev/null
    foamDictionary constant/meltProperties -entry wire/feedVelocity -set "(0 0 -$FEED)" > /dev/null
    foamDictionary constant/meltProperties -entry surfaceTension/oxygenDependent -set true > /dev/null
    foamDictionary constant/meltProperties -entry surfaceTension/chamberOxygenPpm -set "$PPM" > /dev/null
    foamDictionary system/controlDict -entry startFrom -set startTime > /dev/null
    foamDictionary system/controlDict -entry startTime -set 0 > /dev/null
    foamDictionary system/controlDict -entry endTime -set "$EXTRA" > /dev/null
    foamDictionary system/controlDict -entry writeInterval -set 0.002 > /dev/null
    # simple decomposition, no z cut. Prefer (nx 2 1) when np is even and >= 4.
    if [ "$NP" -ge 4 ] && [ $((NP % 2)) -eq 0 ]; then
        N="($((NP / 2)) 2 1)"
    else
        N="($NP 1 1)"
    fi
    foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
    foamDictionary -entry coeffs.n -set "$N" system/decomposeParDict > /dev/null
    decomposePar -force > log.decomposePar 2>&1
    touch case.foam
    nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel \
        > log.laserWireDEDFoam 2>&1
    echo "PIN_ON_TRACK_DONE ${TAG}"
} > "$log" 2>&1
echo "PIN_ON_TRACK_WAIT_DONE ${TAG}"
