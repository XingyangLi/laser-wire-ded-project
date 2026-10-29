#!/bin/bash
# Dragged contact line. Gas enters on the trailing wall only after the
# imposed line is below the generated crest by the ppm threshold.
# The 19 um neck (wire_cavity_wall_tip). Nothing is painted.
# MORE=1 is the ppm x feed matrix, only after 300 ppm at 24 mm/s has opened.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/lib.sh"
ROOT="$TAO_ROOT"
SRC="${SLIT_SRC:-$ROOT/cases/wire_cavity_wall_tip}"
NP="${SLIT_NP:-8}"
MORE="${MORE:-0}"

# name ppm feed_mm thetaR thetaA thetaRox thetaAox
if [[ "$MORE" == 1 ]]; then
    JOBS=(
        "drag50f24 50 24 32 78 130 155"
        "drag100f24 100 24 18 98 145 165"
        "drag300f18 300 18 6 120 158 175"
        "drag300f28 300 28 6 120 158 175"
        "drag50f18 50 18 32 78 130 155"
        "drag100f18 100 18 18 98 145 165"
        "drag50f28 50 28 32 78 130 155"
        "drag100f28 100 28 18 98 145 165"
    )
else
    JOBS=(
        "drag300f24 300 24 6 120 158 175"
    )
fi
NJOBS=${#JOBS[@]}
tao_acquire $((NP * NJOBS))
trap 'tao_release '"$((NP * NJOBS))" EXIT
tao_source_foam

prep() {
    local name="$1" ppm="$2" feed_mm="$3" thR="$4" thA="$5" thRo="$6" thAo="$7"
    local dest="$ROOT/cases/wire_cavity_${name}"
    local feed
    feed=$(awk -v m="$feed_mm" 'BEGIN{printf "%.8g", -m/1000}')
    rm -rf "$dest"
    cp -a "$SRC" "$dest"
    rm -rf "$dest"/processor*
    foamDictionary "$dest/constant/meltProperties" -entry surfaceTension/sigmaScale -set 1 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/enabled -set false > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry wire/feedVelocity -set "(0 0 $feed)" > /dev/null
    python3 - "$dest" "$ppm" "$feed" "$thR" "$thA" "$thRo" "$thAo" << 'PY'
import re, sys
from pathlib import Path
dest, ppm, feed, thR, thA, thRo, thAo = sys.argv[1:]
mp = Path(dest) / "constant/meltProperties"
text = mp.read_text()
for key in ("wireSlide", "oxideSkin", "slitEntry"):
    start = text.find("\n%s\n" % key)
    if start < 0:
        continue
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
    // Model assumption. The line is dragged at the feed while it is pinned.
    // Columns: ppm thetaR[deg] thetaA[deg] Kpin[kg/m3/s]
    oxygenTable
    (
        (50  32  78  4e7)
        (100 18  98  1.2e8)
        (300 6   120 4e8)
    );
}}

oxideSkin
{{
    enabled         false;
}}

slitEntry
{{
    enabled         true;
    ppm             {ppm};
    depthSpan       0.00035;
    // Imposed. The pinned line moves at the feed from the generated crest.
    // Gas enters only after the line is this far below that crest.
    // Higher ppm: stronger pin, smaller threshold, faster entry, wider mouth.
    // Columns: ppm threshold[m] entryRate[m/s] gapMouth[m] gapRoot[m]
    oxygenTable
    (
        (50  1.2e-4  0.012  4.5e-5  3.0e-5)
        (100 8.0e-5  0.020  5.5e-5  3.2e-5)
        (300 4.0e-5  0.040  6.5e-5  3.5e-5)
    );
}}
"""
banner = text.rfind("// ************************************************************************* //")
if banner < 0:
    text = text.rstrip() + "\n" + block
else:
    text = text[:banner] + block + "\n" + text[banner:]
mp.write_text(text)

alpha = Path(dest) / "0/alpha.metal"
raw = alpha.read_bytes().decode("latin-1")
i = raw.find("wireWall")
if i < 0:
    raise SystemExit("no wireWall in alpha.metal")
tail = raw[i:]
tail = re.sub(r"thetaA\s+[0-9.eE+-]+\s*;", f"thetaA          {thA};", tail, count=1)
tail = re.sub(r"thetaR\s+[0-9.eE+-]+\s*;", f"thetaR          {thR};", tail, count=1)
if "thetaAox" not in tail.split("}")[0]:
    tail = tail.replace(
        f"thetaR          {thR};",
        f"thetaR          {thR};\n        thetaAox        {thAo};\n        thetaRox        {thRo};",
        1,
    )
else:
    tail = re.sub(r"thetaAox\s+[0-9.eE+-]+\s*;", f"thetaAox        {thAo};", tail, count=1)
    tail = re.sub(r"thetaRox\s+[0-9.eE+-]+\s*;", f"thetaRox        {thRo};", tail, count=1)
alpha.write_bytes((raw[:i] + tail).encode("latin-1"))

u = Path(dest) / "0/U"
ut = u.read_bytes().decode("latin-1")
ui = ut.find("wireWall")
utail = ut[ui:]
utail, n = re.subn(
    r"refValue\s+uniform\s+\(\s*0\s+0\s+[0-9.eE+-]+\s*\)\s*;",
    f"refValue        uniform (0 0 {feed});",
    utail,
    count=1,
)
if n != 1:
    raise SystemExit("could not set the wireWall feed")
u.write_bytes((ut[:ui] + utail).encode("latin-1"))
print(f"angles {thR}/{thA} ox {thRo}/{thAo} feed {feed}")
PY
    if ! grep -q 'div(phi,oxideCoverage)' "$dest/system/fvSchemes"; then
        python3 - "$dest/system/fvSchemes" << 'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
t = p.read_text()
needle = "div(phi,oxideFilm) Gauss upwind;"
add = needle + "\n    div(phi,oxideCoverage) Gauss vanLeer;"
if needle not in t:
    raise SystemExit("divSchemes has no oxideFilm entry to anchor")
p.write_text(t.replace(needle, add, 1))
PY
    fi
    foamDictionary "$dest/system/controlDict" -entry endTime -set 0.012 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry deltaT -set 2e-7 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry writeInterval -set 0.002 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry maxDeltaT -set 2e-6 > /dev/null
    foamDictionary -entry numberOfSubdomains -set "$NP" "$dest/system/decomposeParDict" > /dev/null
    foamDictionary -entry method -set scotch "$dest/system/decomposeParDict" > /dev/null
    (cd "$dest" && decomposePar -force > log.decomposePar 2>&1)
    python3 "$DIR/bake_wire_wall_T.py" "$dest"
    echo "PREPPED $name ppm=$ppm feed=${feed_mm}"
}

for spec in "${JOBS[@]}"; do
    prep $spec
done

for spec in "${JOBS[@]}"; do
    name=${spec%% *}
    (
        cd "$ROOT/cases/wire_cavity_${name}"
        nice -n 10 stdbuf -o0 -e0 mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
        echo "SOLVE_RC_${name} $?"
    ) &
done
wait
echo ALL_DONE
