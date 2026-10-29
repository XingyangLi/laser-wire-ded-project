#!/bin/bash
# Oxide skin on the free surface, plus the hysteresis drag.
# Nothing is painted: coverage starts at 0. First case is 300 ppm, 24 mm/s.
# MORE=1 adds the ppm/feed matrix only after this one has opened a slit.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/lib.sh"
ROOT="$TAO_ROOT"
SRC="${SKIN_SRC:-$ROOT/cases/wire_cavity_wall_tip}"
NP="${SKIN_NP:-4}"
MORE="${MORE:-0}"

# name ppm feed_mm thetaR thetaA thetaRox thetaAox
if [[ "$MORE" == 1 ]]; then
    JOBS=(
        "skin50f24 50 24 32 78 130 155"
        "skin100f24 100 24 18 98 145 165"
        "skin300f18 300 18 6 120 158 175"
        "skin300f28 300 28 6 120 158 175"
        "skin50f18 50 18 32 78 130 155"
        "skin100f18 100 18 18 98 145 165"
        "skin50f28 50 28 32 78 130 155"
        "skin100f28 100 28 18 98 145 165"
    )
else
    JOBS=(
        "skin300f24 300 24 6 120 158 175"
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
for key in ("wireSlide", "oxideSkin"):
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
    // Model assumption. Higher ppm: lower receding angle, stronger drag.
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
    enabled         true;
    dynamic         true;
    ppm             {ppm};
    genTime         0.001;
    leaveTime       0.0005;
    Kskin           0;
    // Imposed numerical skin, not a measured oxide isotherm.
    // Columns: ppm strength mu[Pa.s] sigmaExtra[N/m] thetaRox thetaAox
    //          E[N/m] bendLength[m] epsRupture
    // Imposed elastic membrane. E and the bending length scale with ppm.
    // Past epsRupture the skin breaks and that patch is a free surface.
    // Alloy sigma stays 1.75 N/m. sigmaExtra is only the skin addition.
    oxygenTable
    (
        (50  0.35  4  0.6  130 155  0.6  4e-5  0.45)
        (100 0.65  10 1.4  145 165  1.2  6e-5  0.8)
        (300 1    18 2.5  158 175  2.5  8e-5  1.2)
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
    # The copied scheme file may already contain this. Set it anyway.
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
    foamDictionary -entry coeffs.n -set "($NP 1 1)" "$dest/system/decomposeParDict" > /dev/null
    (cd "$dest" && decomposePar -force > log.decomposePar 2>&1)
    echo "PREPPED $name ppm=$ppm feed=${feed_mm}"
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
