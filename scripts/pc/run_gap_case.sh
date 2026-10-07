#!/bin/bash
# Run (or continue) one gap-study case, then the post-run renders.
# Usage: run_gap_case.sh <caseDir> <nRanks> <vizOutDir> [all|solve|render]
#   - restart-safe: continues from the latest time (startFrom latestTime); a case whose run.status
#     has "ALL DONE" is skipped; an existing decomposition with time steps is kept as it is
#   - nRanks only matters for a fresh start (re-decomposes if processor* has another count)
#   - solve = solver only, render = renders only, all (default) = both
# Uses the gap-study solver build ~/lwded_bin_gap (stubbing model).
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1
export PATH=$HOME/lwded_bin_gap:$PATH
REPO=/mnt/c/Users/dukyo/laser_wire_ded_project
C=${1:?case dir}; NP=${2:-8}; OUT=${3:?viz out dir}; WHAT=${4:-all}
cd $C || exit 1
ST=$C/run.status
if grep -q "ALL DONE" $ST 2>/dev/null; then echo "$(date) $C already ALL DONE"; exit 0; fi
END=$(foamDictionary -entry endTime -value system/controlDict 2>/dev/null)
latest() { ls -d processor0/[0-9]* 2>/dev/null | sed 's#processor0/##' | sort -g | tail -1; }
nproc_dirs() { ls -d processor[0-9]* 2>/dev/null | wc -l; }
done_run() { python3 -c "import sys; sys.exit(0 if float('${1:-0}') >= float('$END') - 1e-6 else 1)"; }

render() {
    mkdir -p $OUT
    cp case_params.json FIXES.md postProcessing/meltPool/meltPool.dat postProcessing/meltPool/components.dat \
       postProcessing/wireTransfer/wireTransfer.dat $OUT/ 2>/dev/null
    ~/vizenv/bin/python $REPO/scripts/pc/check_below_plate.py $C > $OUT/below_plate.txt 2>&1
    ~/vizenv/bin/python $REPO/visualize_multicomp.py --case . --out $OUT > log.viz 2>&1
    echo "$(date) viz multicomp rc=$?" >> $ST
    ~/vizenv/bin/python $REPO/visualize.py --case . --out $OUT/standard --only-latest >> log.viz 2>&1
    echo "$(date) viz standard rc=$?" >> $ST
    if done_run "$(latest)"; then echo "$(date) ALL DONE" >> $ST; else echo "$(date) RENDERED (unfinished run)" >> $ST; fi
}
if [ "$WHAT" = "render" ]; then render; exit 0; fi

echo "$(date) START binary=$(which laserWireDEDFoam) np=$NP host=$(hostname)" >> $ST
# mesh + fields (once)
if [ ! -f constant/polyMesh/owner ] || [ ! -d 0 ]; then
    echo "$(date) meshing" >> $ST
    MESH_ONLY=1 ./Allrun $NP > log.Allrun 2>&1 || { echo "$(date) MESH FAILED" >> $ST; exit 1; }
fi
# decomposition: keep it if the run has started, else match NP
L=$(latest)
if [ "$(nproc_dirs)" -ne "$NP" ] && { [ -z "$L" ] || [ "$L" = "0" ]; }; then
    echo "$(date) decomposing for $NP ranks" >> $ST
    rm -rf processor*
    foamDictionary -entry numberOfSubdomains -set $NP system/decomposeParDict > /dev/null
    if [ "$NP" -ge 4 ] && [ $((NP % 2)) -eq 0 ]; then N="($((NP/2)) 2 1)"; else N="($NP 1 1)"; fi
    foamDictionary -entry coeffs.n -set "$N" system/decomposeParDict > /dev/null
    decomposePar -force > log.decomposePar 2>&1 || { echo "$(date) DECOMPOSE FAILED" >> $ST; exit 1; }
fi
N=$(nproc_dirs)
for attempt in 1 2; do
    L=$(latest)
    if done_run "$L"; then break; fi
    echo "$(date) solver attempt $attempt from t=${L:-0} on $N ranks" >> $ST
    mpirun -np $N --bind-to none laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1; rc=$?
    echo "$(date) SOLVER_EXIT rc=$rc latest=$(latest)" >> $ST
    [ $rc -eq 0 ] && break
done
if ! done_run "$(latest)"; then
    echo "$(date) NOT FINISHED (latest $(latest) < $END): renders anyway; re-run the queue to continue" >> $ST
fi

[ "$WHAT" = "solve" ] && exit 0
render
