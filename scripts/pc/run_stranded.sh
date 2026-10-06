#!/bin/bash
# Production run: Transitional-R with a 7-strand twisted wire (Invar 36 on SS304), Dukyong_PC / WSL.
# Code + case live in ~/laser_wire_ded_stranded (separate from everything else).
# Renders go to C:\Users\dukyo\laser_wire_ded\viz\full_transitional_r_stranded.
# Status: ~/laser_wire_ded_stranded/stranded.status   (or run status_stranded.sh)
# Restart-safe: if the case already exists, the solver continues from the latest time.
SRC=/mnt/c/Users/dukyo/laser_wire_ded
W=$HOME/laser_wire_ded_stranded
CASE=full_transitional_r_stranded
OUT=$SRC/viz/$CASE
NP=${NP:-8}
mkdir -p $W && cd $W || exit 1
tar xzf $SRC/lwded_src_stranded.tgz
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1 || true
ST=$W/stranded.status
echo "$(date) start (NP=$NP)" >> $ST
(cd solver && ./Allwmake > build.log 2>&1) || { echo "$(date) BUILD FAILED" >> $ST; exit 1; }
mkdir -p $OUT
if [ ! -d $CASE/processor0 ]; then
  python3 generate_case.py --laser-config transitional_r --wire-type stranded --case $CASE --np $NP > gen_stranded.log 2>&1 \
    || { echo "$(date) GENERATE FAILED" >> $ST; exit 1; }
  cp gen_stranded.log $OUT/
  (cd $CASE && MESH_ONLY=1 ./Allrun $NP) || { echo "$(date) MESH FAILED" >> $ST; exit 1; }
  echo "$(date) mesh done: $(grep -m1 'cells:' $CASE/log.checkMesh)" >> $ST
  ~/vizenv/bin/python visualize.py --case $CASE --out $OUT --wire-closeup-times 0 --wire-closeup-only > $CASE/log.viz0 2>&1
  cp $CASE/case_params.json $OUT/
  cd $CASE && mpirun -np $NP laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1; rc=$?; cd ..
else
  cd $CASE && mpirun -np $NP laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1; rc=$?; cd ..
fi
echo "$(date) solver finished rc=$rc" >> $ST
~/vizenv/bin/python visualize.py --case $CASE --out $OUT --wire-closeup-times 0.05,0.2,0.4,0.6,0.862 > $CASE/log.visualize 2>&1
echo "$(date) rendered rc=$?" >> $ST
cp $CASE/postProcessing/meltPool/meltPool.dat $OUT/ 2>/dev/null
echo "$(date) ALL DONE" >> $ST
