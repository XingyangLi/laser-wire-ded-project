#!/bin/bash
# Hysteresis on the solid wire wall. No painted shell.
# First job is 300 ppm at 24 mm/s. Pass MORE=1 to add the ppm/feed matrix
# once that job is already running (ranks stay within 32).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/lib.sh"
ROOT="$TAO_ROOT"
SRC="$ROOT/cases/wire_cavity_wall_tip"
NP=4
MORE="${MORE:-0}"

# name ppm feed_mm_s thetaR thetaA
if [[ "$MORE" == 1 ]]; then
    # 300 ppm at 24 mm/s is already running. These seven fill the rest of the cap.
    JOBS=(
        "slide50f24 50 24 32 78"
        "slide100f24 100 24 18 98"
        "slide300f18 300 18 6 120"
        "slide300f28 300 28 6 120"
        "slide50f18 50 18 32 78"
        "slide100f18 100 18 18 98"
        "slide100f28 100 28 18 98"
    )
else
    JOBS=(
        "slide300f24 300 24 6 120"
    )
fi
NJOBS=${#JOBS[@]}
tao_acquire $((NP * NJOBS))
trap 'tao_release '"$((NP * NJOBS))" EXIT
tao_source_foam

prep() {
    local name="$1" ppm="$2" feed_mm="$3" thR="$4" thA="$5"
    local dest="$ROOT/cases/wire_cavity_${name}"
    local feed
    feed=$(awk -v m="$feed_mm" 'BEGIN{printf "%.8g", -m/1000}')
    rm -rf "$dest"
    cp -a "$SRC" "$dest"
    rm -rf "$dest"/processor*
    foamDictionary "$dest/constant/meltProperties" -entry surfaceTension/sigmaScale -set 1 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/enabled -set false > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry wire/feedVelocity -set "(0 0 $feed)" > /dev/null
    python3 - "$dest" "$ppm" "$feed" "$thR" "$thA" << 'PY'
import sys
from pathlib import Path
dest, ppm, feed, thR, thA = sys.argv[1:]
mp = Path(dest) / "constant/meltProperties"
text = mp.read_text()
start = text.find("\nwireSlide\n")
if start >= 0:
    # drop an existing block up to the next top-level key or the banner
    rest = text[start+1:]
    end_rel = rest.find("\n// ****")
    if end_rel < 0:
        end_rel = len(rest)
    text = text[:start] + text[start+1+end_rel:]
block = f"""
wireSlide
{{
    enabled         true;
    ppm             {ppm};
    tau             0.001;
    gradMin         0.25;
    // Model assumption, not a measured isotherm. Higher ppm is a stronger
    // oxide skin: lower receding angle, wider window, larger Kpin.
    // Columns: ppm thetaR[deg] thetaA[deg] Kpin[kg/m3/s]
    oxygenTable
    (
        (50  32  78  4e7)
        (100 18  98  1.2e8)
        (300 6   120 4e8)
    );
}}
"""
banner = text.rfind("// ************************************************************************* //")
if banner < 0:
    text = text.rstrip() + "\n" + block
else:
    text = text[:banner] + block + "\n" + text[banner:]
mp.write_text(text)

# Angle condition on the wall matches the table row. Value stays uniform.
alpha = Path(dest) / "0/alpha.metal"
raw = alpha.read_bytes().decode("latin-1")
key = "wireWall"
i = raw.find(key)
if i < 0:
    raise SystemExit("no wireWall in alpha.metal")
j = raw.find("thetaA", i)
k = raw.find("thetaR", i)
if j < 0 or k < 0:
    raise SystemExit("wireWall alpha is missing thetaA/thetaR")
import re
raw2 = raw[:i] + re.sub(
    r"thetaA\s+[0-9.eE+-]+\s*;",
    f"thetaA          {thA};",
    raw[i:],
    count=1,
)
raw2 = raw2[:i] + re.sub(
    r"thetaR\s+[0-9.eE+-]+\s*;",
    f"thetaR          {thR};",
    raw2[i:],
    count=1,
)
# The slice logic above double-applies. Do it on the whole tail once.
tail = raw[i:]
tail = re.sub(r"thetaA\s+[0-9.eE+-]+\s*;", f"thetaA          {thA};", tail, count=1)
tail = re.sub(r"thetaR\s+[0-9.eE+-]+\s*;", f"thetaR          {thR};", tail, count=1)
raw = raw[:i] + tail
alpha.write_bytes(raw.encode("latin-1"))

u = Path(dest) / "0/U"
ut = u.read_bytes().decode("latin-1")
ui = ut.find("wireWall")
if ui < 0:
    raise SystemExit("no wireWall in U")
utail = ut[ui:]
utail2, n = re.subn(
    r"refValue\s+uniform\s+\(\s*0\s+0\s+[0-9.eE+-]+\s*\)\s*;",
    f"refValue        uniform (0 0 {feed});",
    utail,
    count=1,
)
if n != 1:
    raise SystemExit("could not set the wireWall feed")
u.write_bytes((ut[:ui] + utail2).encode("latin-1"))
print(f"angles {thR}/{thA} feed {feed}")
PY
    foamDictionary "$dest/system/controlDict" -entry endTime -set 0.018 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry deltaT -set 2e-7 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry writeInterval -set 0.002 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry maxDeltaT -set 2e-6 > /dev/null
    foamDictionary -entry numberOfSubdomains -set "$NP" "$dest/system/decomposeParDict" > /dev/null
    foamDictionary -entry coeffs.n -set "($NP 1 1)" "$dest/system/decomposeParDict" > /dev/null
    (cd "$dest" && decomposePar -force > log.decomposePar 2>&1)
    echo "PREPPED $name ppm=$ppm feed=${feed_mm} mm/s theta ${thR}/${thA}"
}

for spec in "${JOBS[@]}"; do
    # shellcheck disable=SC2086
    prep $spec
done

for spec in "${JOBS[@]}"; do
    name=${spec%% *}
    (
        cd "$ROOT/cases/wire_cavity_${name}"
        nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
        echo "SOLVE_RC_${name} $?"
    ) &
done
wait
echo ALL_DONE
