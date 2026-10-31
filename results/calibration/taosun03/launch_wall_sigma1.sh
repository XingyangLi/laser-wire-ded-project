#!/bin/bash
# Normal alloy sigma. Two shell widths, same cal95b wall and tip melt.
# Pin ramps over 1 ms. Kpin is 1e7, not 1e12. 16 ms, 4 ranks each.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/lib.sh"
ROOT="$TAO_ROOT"
SRC="$ROOT/cases/wire_cavity_wall_tip"
NP=4
tao_acquire $((NP * 2))
trap 'tao_release '"$((NP * 2))" EXIT
tao_source_foam

prep() {
    local name="$1" ncells="$2"
    local dest="$ROOT/cases/wire_cavity_${name}"
    rm -rf "$dest"
    cp -a "$SRC" "$dest"
    rm -rf "$dest"/processor*
    foamDictionary "$dest/constant/meltProperties" -entry surfaceTension/sigmaScale -set 1 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/Kpin -set 1e7 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/tau -set 0.001 > /dev/null
    foamDictionary "$dest/constant/meltProperties" -entry linePin/nCells -set "$ncells" > /dev/null
    foamDictionary "$dest/system/controlDict" -entry endTime -set 0.016 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry deltaT -set 2e-7 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry writeInterval -set 0.002 > /dev/null
    foamDictionary "$dest/system/controlDict" -entry maxDeltaT -set 2e-6 > /dev/null
    foamDictionary -entry numberOfSubdomains -set "$NP" "$dest/system/decomposeParDict" > /dev/null
    foamDictionary -entry coeffs.n -set "($NP 1 1)" "$dest/system/decomposeParDict" > /dev/null
    (cd "$dest" && decomposePar -force > log.decomposePar 2>&1)
    echo "PREPPED $name nCells=$ncells sigmaScale=1"
}

prep wall_n2 2
prep wall_n3 3

(
    cd "$ROOT/cases/wire_cavity_wall_n2"
    nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
        laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
    echo SOLVE_RC_n2 $?
) &
(
    cd "$ROOT/cases/wire_cavity_wall_n3"
    nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
        laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
    echo SOLVE_RC_n3 $?
) &
wait
echo ALL_DONE
