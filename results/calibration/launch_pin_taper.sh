#!/bin/bash
# Crest mesh and true wall from cal109. The imposed shell is a slope:
# thickness at the feed-following line, thicknessTop at the crest.
# Metal outside that shell is not cleared and not forced. sigma is 1.75 N/m.
# No oxygen dependence.
#
#   TAPER_TAG   case tag
#   TAPER_T0    shell offset at the line [m] (default 4e-5)
#   TAPER_T1    shell offset at the crest [m] (default 9e-5)
#   TAPER_END   end time (default 0.016)
#   TAPER_NP    ranks (default 4)
#   TAPER_PARALLEL / TAPER_SKIP_BUILD
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
SRC=${TAPER_SRC:-$ROOT/cases/wire_cavity_cal109}
TAG=${TAPER_TAG:-cal111}
T0=${TAPER_T0:-4e-5}
T1=${TAPER_T1:-9e-5}
END=${TAPER_END:-0.016}
NP=${TAPER_NP:-4}
exec > >(tee -a "$ROOT/results/calibration/pin_taper_${TAG}.log") 2>&1
if [ "${TAPER_PARALLEL:-0}" != 1 ] && ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
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
if [ "${TAPER_SKIP_BUILD:-0}" != 1 ]; then
    (cd "$ROOT/solver" && ./Allwmake)
fi

case="$ROOT/cases/wire_cavity_${TAG}"
echo "=== slope pin ${TAG}: t0 ${T0} t1 ${T1}, end ${END}, np ${NP}, sigma 1.75 ==="
rm -rf "$case"
mkdir -p "$case"
cp -a "$SRC/constant" "$SRC/system" "$SRC/0" "$case/"
rm -rf "$case/processor"*
python3 - "$case/constant/meltProperties" "$T0" "$T1" << 'PY'
from pathlib import Path
import sys
path, t0s, t1s = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
t0, t1 = float(t0s), float(t1s)
text = path.read_text()
start = text.find("\nlinePin\n")
end = text.find("\n// ************************************************************************* //", start)
if start < 0 or end < 0:
    raise SystemExit("linePin block not found")
block = f"""
linePin
{{
    enabled         true;
    nCells          2;
    // Imposed shell. Offset from the wire face, narrow at the line
    // and wider at the crest. Metal outside this radius is not changed.
    // sigma stays 1.75 N/m. No oxygen dependence.
    thickness       {t0:.8g};
    thicknessTop    {t1:.8g};
    lineBand        8e-5;
    holdFade        0;
    ppmRef          300;
    Kpin            1e12;
    tau             0.0005;
}}
"""
path.write_text(text[:start] + "\n" + block + text[end:])
print(f"imposed shell {t0*1e3:.3f} mm at the line, {t1*1e3:.3f} mm at the crest")
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
echo "TAPER_PIN_DONE ${TAG}"
