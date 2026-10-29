#!/bin/bash
# Narrow neck. Mouth at the centre-plane bead top (1.58 mm).
# nF is a constant 0.047 mm notch (the cal109 width that kept the crest).
# nG and nH open only to 0.075-0.080 mm. Speed ceiling 4 or 5 m/s.
# Alloy sigma. 18 ms so a 0.3 mm depth can hold for 4 ms. 4 ranks each.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/lib.sh"
ROOT="$TAO_ROOT"
SRC="$ROOT/cases/wire_cavity_wall_tip"
NP=4
NJOBS=3
tao_acquire $((NP * NJOBS))
trap 'tao_release '"$((NP * NJOBS))" EXIT
tao_source_foam

prep() {
    local name="$1" wbot="$2" wtop="$3" umax="$4"
    local dest="$ROOT/cases/wire_cavity_${name}"
    rm -rf "$dest"
    cp -a "$SRC" "$dest"
    rm -rf "$dest"/processor*
    foamDictionary "$dest/constant/meltProperties" -entry surfaceTension/sigmaScale -set 1 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/Kpin -set 1e7 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/tau -set 0.001 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/wBottom -set "$wbot" > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/wTop -set "$wtop" > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/z0 -set 0.00158 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/uMax -set "$umax" > /dev/null
    foamDictionary "$dest/system/controlDict" -entry endTime -set 0.018 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry deltaT -set 2e-7 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry writeInterval -set 0.002 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry maxDeltaT -set 2e-6 > /dev/null
    foamDictionary -entry numberOfSubdomains -set "$NP" "$dest/system/decomposeParDict" > /dev/null
    foamDictionary -entry coeffs.n -set "($NP 1 1)" "$dest/system/decomposeParDict" > /dev/null
    (cd "$dest" && decomposePar -force > log.decomposePar 2>&1)
    echo "PREPPED $name wBottom=$wbot wTop=$wtop uMax=$umax"
}

prep wall_nF 4.7e-5 4.7e-5 4
prep wall_nG 4.5e-5 7.5e-5 4
prep wall_nH 5.0e-5 8.0e-5 5

runone() {
    local name="$1"
    (
        cd "$ROOT/cases/wire_cavity_${name}"
        nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
        echo "SOLVE_RC_${name} $?"
    ) &
}
runone wall_nF
runone wall_nG
runone wall_nH
wait
echo ALL_DONE
