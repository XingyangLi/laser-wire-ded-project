#!/bin/bash
# Alloy sigma. Sloped pin: narrow throat, wider mouth. 14 ms, 4 ranks.
# uMax is the numerical ceiling that stops the 7 ms Courant spiral.
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
    local name="$1" wbot="$2" wtop="$3"
    local dest="$ROOT/cases/wire_cavity_${name}"
    rm -rf "$dest"
    cp -a "$SRC" "$dest"
    rm -rf "$dest"/processor*
    foamDictionary "$dest/constant/meltProperties" -entry surfaceTension/sigmaScale -set 1 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/Kpin -set 1e7 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/tau -set 0.001 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/wBottom -set "$wbot" > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/wTop -set "$wtop" > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/uMax -set 1.5 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry endTime -set 0.014 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry deltaT -set 2e-7 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry writeInterval -set 0.002 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry maxDeltaT -set 2e-6 > /dev/null
    foamDictionary -entry numberOfSubdomains -set "$NP" "$dest/system/decomposeParDict" > /dev/null
    foamDictionary -entry coeffs.n -set "($NP 1 1)" "$dest/system/decomposeParDict" > /dev/null
    (cd "$dest" && decomposePar -force > log.decomposePar 2>&1)
    echo "PREPPED $name wBottom=$wbot wTop=$wtop"
}

prep wall_wA 4e-5 1.4e-4
prep wall_wB 5e-5 1.8e-4
prep wall_wC 3.5e-5 2.2e-4

runone() {
    local name="$1"
    (
        cd "$ROOT/cases/wire_cavity_${name}"
        nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
        echo "SOLVE_RC_${name} $?"
    ) &
}
runone wall_wA
runone wall_wB
runone wall_wC
wait
echo ALL_DONE
