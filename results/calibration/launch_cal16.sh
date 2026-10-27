#!/bin/bash
# cal16. cal15 kept the fused dome, and the steeper trailing window did not
# hold the notch open: the Young force was already at its cap. Oxygen now
# lowers sigma through the Sahoo-Belton law (500 ppm) so the cooler neck can
# pinch. The oxygen angle table is deleted so the plate stays 10/40 and the
# trailing wire window stays 60/140. Marangoni stays off. Hot plate, cold wire,
# scan 4 mm/s, as in cal14. Twelve ranks, nice 10. End 0.60 s.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/cal16_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal16"
if ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
    echo "a solver is already running" >&2
    exit 1
fi
cd "$ROOT/solver"
set +euo pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -euo pipefail
./Allwmake
export PATH="${FOAM_USER_APPBIN}:$PATH"
hash -r
cd "$ROOT"
python3 generate_case.py --case "$CASE" --laser-config triple \
    --wire-type solid --material 316L --resolution coarse --domain-y half \
    --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
    --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
    --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0.05 \
    --scan-speed 0.004 --wire-feed-speed 0.020 \
    --beam-azimuths 30,-30,180 \
    --beam-inclinations=-26,-26,-38 \
    --beam-powers 160,160,420 \
    --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
    --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
    --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
    --end-time 0.60 --write-interval 0.10 --np 12 --laser-ramp 2e-3 \
    --wire-refine 2 \
    --contact-pinning --pin-wire --porosity --wire-cavity \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 60 --theta-advancing-wire-trail 140 \
    --wire-sector-half-angle 90 --wire-sector-blend 30 \
    --contact-force-factor 6 \
    --no-marangoni \
    --wire-pin-frame head \
    --rigid-substrate 100 \
    --oxygen-ppm 500
cd "$CASE"
python3 - << 'PY'
from pathlib import Path
p = Path("system/setFieldsDict")
s = p.read_text()
old = "            volScalarFieldValue alpha.metal 1\n        );"
new = "            volScalarFieldValue alpha.metal 1\n            volScalarFieldValue T 1100\n        );"
n = s.count(old)
if n != 1:
    raise SystemExit(f"substrate block count {n}")
p.write_text(s.replace(old, new, 1))
mp = Path("constant/meltProperties")
t = mp.read_text()
start = t.find("    // PLACEHOLDER.")
table = t.find("oxygenAngleTable")
if start < 0 or table < 0 or start > table:
    raise SystemExit("oxygen angle table not found")
close = t.find("\n", t.find("    );", table)) + 1
t = t[:start] + t[close:]
if "oxygenAngleTable" in t:
    raise SystemExit("angle table still present")
if "oxygenDependent  true" not in t or "chamberOxygenPpm 500" not in t:
    raise SystemExit("oxygen model missing")
if "thetaReceding   10" not in t or "thetaRecedingWireTrail 60" not in t:
    raise SystemExit("plate or trailing window lost")
mp.write_text(t)
print("removed oxygenAngleTable; sigma(T, 500 ppm) kept; plate 10/40 kept")
PY
foamDictionary 0.orig/T -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
echo "--- checks ---"
grep -n "oxygenDependent\|chamberOxygenPpm\|oxygenAngleTable\|thetaReceding   10\|thetaRecedingWireTrail" constant/meltProperties
foamDictionary 0.orig/T -entry boundaryField/inletSubstrate/value
foamDictionary 0.orig/T -entry boundaryField/wireInlet/value
./Allclean >/dev/null 2>&1 || true
grep -q "volScalarFieldValue T 1100" system/setFieldsDict
grep -q "oxygenDependent  true" constant/meltProperties
grep -q "chamberOxygenPpm 500" constant/meltProperties
if grep -q oxygenAngleTable constant/meltProperties; then
    echo "angle table survived Allclean" >&2
    exit 1
fi
foamDictionary 0.orig/T -entry boundaryField/inletSubstrate/value | grep -q "1100"
foamDictionary 0.orig/T -entry boundaryField/wireInlet/value | grep -q "300"
nice -n 10 ./Allrun 12
python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" || true
echo "CAL16_DONE"
