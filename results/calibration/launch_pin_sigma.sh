#!/bin/bash
# Same pin, mesh and 0.8 s bead as cal105, with a higher surface tension.
#
# sigma0 (1.75 N/m) and the floor sigmaMin (0.525 N/m) are multiplied by
# SIGMA_FACTOR. dSigma/dT is left unchanged. This is an imposed numerical
# enhancement, not a physical surface tension of the alloy.
#
#   SIGMA_TAG      case tag (cal106, cal107, cal108)
#   SIGMA_FACTOR   1.5, 2 or 3
#   SIGMA_NP       ranks (default 4)
#   SIGMA_PARALLEL set to 1 when several of these run together
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
SRC=${SIGMA_SRC:-$ROOT/cases/wire_cavity_cal105}
TAG=${SIGMA_TAG:?set SIGMA_TAG}
FACTOR=${SIGMA_FACTOR:?set SIGMA_FACTOR}
NP=${SIGMA_NP:-4}
END=${SIGMA_END:-0.006}
exec > >(tee -a "$ROOT/results/calibration/pin_sigma_${TAG}.log") 2>&1
if [ "${SIGMA_PARALLEL:-0}" != 1 ] && ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
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

case="$ROOT/cases/wire_cavity_${TAG}"
echo "=== sigma pin ${TAG}: factor ${FACTOR} (imposed, not physical), np ${NP} ==="
rm -rf "$case"
mkdir -p "$case"
cp -a "$SRC/constant" "$SRC/system" "$SRC/0" "$case/"
rm -rf "$case/processor"*
python3 - "$case/constant/meltProperties" "$FACTOR" << 'PY'
import sys
from pathlib import Path
path, factor = Path(sys.argv[1]), float(sys.argv[2])
text = path.read_text()
sigma = 1.75 * factor
floor = 0.525 * factor
# Both sigma entries are the baseline 1.75 (wire block is unused, enabled false).
n = text.count("sigma           1.75;")
if n != 2:
    raise SystemExit(f"expected two sigma 1.75 entries, found {n}")
text = text.replace("sigma           1.75;", f"sigma           {sigma:.6g};", 2)
if "sigmaMin        0.525;" not in text:
    raise SystemExit("sigmaMin 0.525 not found")
text = text.replace("sigmaMin        0.525;", f"sigmaMin        {floor:.6g};", 1)
note = (
    f"// IMPOSED numerical enhancement: sigma0 and sigmaMin x {factor:g} "
    f"({sigma:.4g} / {floor:.4g} N/m). Not a physical surface tension.\n"
)
text = text.replace("surfaceTension\n{", "surfaceTension\n{\n" + note, 1)
path.write_text(text)
print(f"sigma0 {sigma:.6g} N/m, sigmaMin {floor:.6g} N/m, factor {factor:g}")
PY
cd "$case"
foamDictionary system/controlDict -entry endTime -set "$END" > /dev/null
foamDictionary system/decomposeParDict -entry numberOfSubdomains -set "$NP" > /dev/null
if [ "$NP" -ge 4 ] && [ $((NP % 2)) -eq 0 ]; then
    N="($((NP / 2)) 2 1)"
else
    N="($NP 1 1)"
fi
foamDictionary system/decomposeParDict -entry coeffs.n -set "$N" > /dev/null
decomposePar -force > log.decomposePar 2>&1
touch case.foam
nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel \
    > log.laserWireDEDFoam 2>&1
echo "SIGMA_PIN_DONE ${TAG}"
