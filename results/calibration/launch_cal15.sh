#!/bin/bash
# cal15. cal14 fused and wetted the plate and kept a trailing-tall dome, but
# the notch behind the wire did not pinch into a lasting bubble.
# Trailing wire window 110/160 (was 60/140) and blend 10 deg (was 30) so the
# face behind the wire is held at a steeper angle. Scan 5 mm/s (was 4) so the
# notch is carried into the pool before it refills. Plate stays 1100 K and
# 10/40. Oxygen stays off so the angle table cannot replace that plate window.
# Twelve ranks, nice 10. End 0.70 s.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/cal15_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal15"
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
    --scan-speed 0.005 --wire-feed-speed 0.020 \
    --beam-azimuths 30,-30,180 \
    --beam-inclinations=-26,-26,-38 \
    --beam-powers 160,160,420 \
    --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
    --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
    --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
    --end-time 0.70 --write-interval 0.10 --np 12 --laser-ramp 2e-3 \
    --wire-refine 2 \
    --contact-pinning --pin-wire --porosity --wire-cavity \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 110 --theta-advancing-wire-trail 160 \
    --wire-sector-half-angle 90 --wire-sector-blend 10 \
    --contact-force-factor 6 \
    --no-marangoni \
    --wire-pin-frame head \
    --rigid-substrate 100
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
print("substrate T set to 1100 in setFieldsDict")
PY
foamDictionary 0.orig/T -entry boundaryField/inletSubstrate/value -set "uniform 1100" > /dev/null
echo "--- plate check ---"
grep -n "T 1100" system/setFieldsDict
grep -n -E "thetaReceding |thetaAdvancing |thetaRecedingWireTrail|thetaAdvancingWireTrail|wireSectorBlend" constant/meltProperties
foamDictionary 0.orig/T -entry boundaryField/inletSubstrate/value
foamDictionary 0.orig/T -entry boundaryField/wireInlet/value
grep -n "Tambient" constant/meltProperties
./Allclean >/dev/null 2>&1 || true
grep -q "volScalarFieldValue T 1100" system/setFieldsDict
foamDictionary 0.orig/T -entry boundaryField/wireInlet/value | grep -q "300"
foamDictionary 0.orig/T -entry boundaryField/inletSubstrate/value | grep -q "1100"
grep -q "thetaRecedingWireTrail 110" constant/meltProperties
grep -q "wireSectorBlend 10" constant/meltProperties
grep -q "thetaReceding   10" constant/meltProperties
nice -n 10 ./Allrun 12
python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" || true
echo "CAL15_DONE"
