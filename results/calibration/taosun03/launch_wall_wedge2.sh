#!/bin/bash
# Mouth at the centre-plane bead top (1.58 mm), not the dry-wire coating.
# Throat gas, slope opens upward, cell outside the slope held as metal.
# Speed ceiling 1.5 m/s. Alloy sigma. 18 ms, 6 ranks.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/lib.sh"
ROOT="$TAO_ROOT"
SRC="$ROOT/cases/wire_cavity_wall_tip"
NP=6
NJOBS=2
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
    foamDictionary "$dest/constant/meltProperties" -entry linePin/z0 -set 0.00158 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/uMax -set 1.5 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry endTime -set 0.018 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry deltaT -set 2e-7 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry writeInterval -set 0.002 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry maxDeltaT -set 2e-6 > /dev/null
    foamDictionary -entry numberOfSubdomains -set "$NP" "$dest/system/decomposeParDict" > /dev/null
    foamDictionary -entry coeffs.n -set "($NP 1 1)" "$dest/system/decomposeParDict" > /dev/null
    (cd "$dest" && decomposePar -force > log.decomposePar 2>&1)
    echo "PREPPED $name wBottom=$wbot wTop=$wtop z0=0.00158"
}

prep wall_wD 4.5e-5 1.6e-4
prep wall_wE 4.0e-5 2.0e-4

runone() {
    local name="$1"
    (
        cd "$ROOT/cases/wire_cavity_${name}"
        nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
        echo "SOLVE_RC_${name} $?"
    ) &
}
runone wall_wD
runone wall_wE
wait
echo ALL_DONE
