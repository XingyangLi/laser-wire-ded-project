#!/bin/bash
# val3mm_fe_ni_v2: 3 mm Fe+Ni validation on the PC (8 ranks), defocused optics as val3mm_fe_ni_defocus
# + rigidSubstrate (Kmushy x100 in the solid plate) + stubFloorZ (no strands driven below the plate line).
# Feed scale 1.0 (the defocus run delivered 99% of the fed metal; see FIXES.md).
# Restart-safe: if processor0 exists the solver continues from the latest time (startFrom latestTime).
# Launch hidden + keep-awake from Windows:
#   Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',
#     'C:\Users\dukyo\laser_wire_ded_project\scripts\pc\launch_wsl_job.ps1','-Script','/home/dukyong/laser_wire_ded_stranded/val3mm_fe_ni_v2/run_v2.sh'
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1
export PATH=$HOME/lwded_bin:$PATH          # solver built from the repo (new options)
REPO=/mnt/c/Users/dukyo/laser_wire_ded_project
C=$HOME/laser_wire_ded_stranded/val3mm_fe_ni_v2
OUT=/mnt/c/Users/dukyo/laser_wire_ded/viz/val3mm_fe_ni_v2
cd $C || exit 1
ST=$C/run.status
echo "$(date) START binary=$(which laserWireDEDFoam)" >> $ST
if [ ! -d processor0 ]; then
    ./Allrun 8; rc=$?
else
    echo "$(date) restart from latest time" >> $ST
    mpirun -np 8 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1; rc=$?
fi
echo "$(date) SOLVER_EXIT rc=$rc" >> $ST
mkdir -p $OUT
cp case_params.json FIXES.md postProcessing/meltPool/meltPool.dat postProcessing/meltPool/components.dat $OUT/ 2>/dev/null
~/vizenv/bin/python $C/check_below_plate.py $C >> $OUT/below_plate.txt 2>&1
~/vizenv/bin/python $REPO/visualize_multicomp.py --case . --out $OUT > log.viz 2>&1
echo "$(date) viz multicomp rc=$?" >> $ST
~/vizenv/bin/python $REPO/visualize.py --case . --out $OUT/standard --only-latest >> log.viz 2>&1
echo "$(date) viz standard rc=$?" >> $ST
echo "$(date) ALL DONE" >> $ST