#!/bin/bash
# track10mm_fe_ni: 10 mm Fe+Ni stranded-Invar validation track on the PC (8 ranks), restart-safe.
#  - generates the case (first call only) from the COMMITTED generator (git index version, so local
#    uncommitted edits of generate_case.py do not leak in) with recipe_track10mm_fe_ni.sh
#  - runs ./Allrun 8, or continues from the latest time if processor0 exists (startFrom latestTime)
#  - afterwards: bead-volume audit, renders and the experiment comparison -> viz\track10mm_fe_ni
# Launch hidden + keep-awake from Windows: Track10mm_Start.bat (or launch_wsl_job.ps1 -Script <this file>)
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1
export PATH=$HOME/lwded_bin_track10mm:$PATH      # solver with conservativeTracers / tracerBudget
NAME=${NAME:-track10mm_fe_ni}
REPO=/mnt/c/Users/dukyo/laser_wire_ded_project
C=$HOME/laser_wire_ded_stranded/$NAME
OUT=/mnt/c/Users/dukyo/laser_wire_ded/viz/$NAME
ST=$C/run.status
mkdir -p $OUT
if [ ! -f $C/Allrun ]; then
    G=$(mktemp -d)
    (cd $REPO && git show :generate_case.py > $G/generate_case.py && git show :materials.py > $G/materials.py) || exit 1
    python3 $G/generate_case.py $(bash $REPO/scripts/pc/recipe_track10mm_fe_ni.sh $C) > $OUT/gen.log 2>&1 || { echo "GENERATE FAILED"; cat $OUT/gen.log; exit 1; }
    rm -rf $G
    cp -f $REPO/cases/$NAME/FIXES.md $C/ 2>/dev/null
    cp -f $REPO/scripts/pc/check_below_plate.py $REPO/scripts/pc/bead_volume_audit.py $C/ 2>/dev/null
fi
cd $C || exit 1
echo "$(date) START binary=$(which laserWireDEDFoam)" >> $ST
if [ ! -d processor0 ]; then
    ./Allrun 8; rc=$?
else
    echo "$(date) restart from latest time" >> $ST
    mpirun -np 8 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1; rc=$?
fi
echo "$(date) SOLVER_EXIT rc=$rc" >> $ST
END=$(foamDictionary -entry endTime -value system/controlDict 2>/dev/null)
LAST=$(ls -d processor0/[0-9]* 2>/dev/null | xargs -n1 basename | sort -g | tail -1)
if [ "$rc" != 0 ] || ! python3 -c "import sys; sys.exit(0 if float('$LAST') >= float('$END') - 1e-3 else 1)"; then
    echo "$(date) solver stopped before the end time (latest $LAST of $END): no renders; restart with Track10mm_Start.bat" >> $ST
    exit $rc
fi
reconstructPar -newTimes > log.reconstructPar 2>&1
cp case_params.json FIXES.md postProcessing/meltPool/*.dat $OUT/ 2>/dev/null
cp postProcessing/wireTransfer/wireTransfer.dat $OUT/ 2>/dev/null
python3 $REPO/scripts/pc/status_track10mm.py $NAME > $OUT/final_status.txt 2>&1
~/vizenv/bin/python $REPO/scripts/pc/bead_volume_audit.py $C 0,1,2,3,$END > $OUT/bead_volume_audit.txt 2>&1
~/vizenv/bin/python $C/check_below_plate.py $C 1,2,3,$END > $OUT/below_plate.txt 2>&1
~/vizenv/bin/python $REPO/visualize_multicomp.py --case . --out $OUT --build-xs 0.5,1.5,3,4.5,6 > log.viz 2>&1
echo "$(date) viz multicomp rc=$?" >> $ST
~/vizenv/bin/python $REPO/visualize.py --case . --out $OUT/standard --only-latest >> log.viz 2>&1
echo "$(date) viz standard rc=$?" >> $ST
~/vizenv/bin/python $REPO/scripts/pc/compare_track10mm.py --case $C --viz $OUT --validation $REPO/validation >> log.viz 2>&1
echo "$(date) comparison rc=$?" >> $ST
echo "$(date) ALL DONE" >> $ST
