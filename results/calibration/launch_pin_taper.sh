#!/bin/bash
# Crest mesh and true wall from cal109, with a graded contact line.
#
# The narrow shell at the line is imposed (thickness). Toward the crest the
# gas bias widens (thicknessTop) and the hold fades (holdFade). The cell
# outside that bias is not forced to metal, so the meniscus can open.
# sigma stays 1.75 N/m. No oxygen dependence.
#
#   TAPER_TAG   case tag (default cal110)
#   TAPER_END   end time (default 0.020)
#   TAPER_NP    ranks (default 12)
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
SRC=${TAPER_SRC:-$ROOT/cases/wire_cavity_cal109}
TAG=${TAPER_TAG:-cal110}
END=${TAPER_END:-0.020}
NP=${TAPER_NP:-12}
exec > >(tee -a "$ROOT/results/calibration/pin_taper_${TAG}.log") 2>&1
if ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
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
(cd "$ROOT/solver" && ./Allwmake)

case="$ROOT/cases/wire_cavity_${TAG}"
echo "=== taper pin ${TAG}: end ${END}, np ${NP}, sigma 1.75 ==="
rm -rf "$case"
mkdir -p "$case"
cp -a "$SRC/constant" "$SRC/system" "$SRC/0" "$case/"
rm -rf "$case/processor"*
python3 - "$case/constant/meltProperties" << 'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
old = """linePin
{
    enabled         true;
    nCells          2;
    thickness       3.75e-05;
    ppmRef          300;
    Kpin            1e+12;
    tau             0.0005;
}"""
new = """linePin
{
    enabled         true;
    nCells          2;
    // Narrow shell at the line: imposed. thicknessTop is a fading bias
    // toward the crest, not a painted outer wall. sigma stays 1.75 N/m.
    thickness       4e-5;
    thicknessTop    9e-5;
    lineBand        8e-5;
    // 0: the graded bias is held. The cell outside it is still free.
    holdFade        0;
    ppmRef          300;
    Kpin            1e12;
    tau             0.0005;
}"""
if old not in text:
    raise SystemExit("cal109 linePin block not found")
path.write_text(text.replace(old, new, 1))
print("linePin taper: 0.040 mm at the line, 0.090 mm at the crest, hold does not fade")
PY
cd "$case"
foamDictionary system/controlDict -entry endTime -set "$END" > /dev/null
foamDictionary system/decomposeParDict -entry numberOfSubdomains -set "$NP" > /dev/null
foamDictionary system/decomposeParDict -entry coeffs.n -set "(6 2 1)" > /dev/null
decomposePar -force > log.decomposePar 2>&1
touch case.foam
nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel \
    > log.laserWireDEDFoam 2>&1
echo "TAPER_PIN_DONE ${TAG}"
