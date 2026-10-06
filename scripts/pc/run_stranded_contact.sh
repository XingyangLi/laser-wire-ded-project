#!/bin/bash
# Production run: Transitional-R, 7-strand wire, wire-pool contact fix (beam focus on the substrate surface z = 0 instead of 0.5 mm up the wire, wire fed from t = 0, no 20 ms preheat).
# Code + case live in ~/laser_wire_ded_stranded (separate from everything else).
# Renders go to C:\Users\dukyo\laser_wire_ded\viz\$CASE (default full_transitional_r_stranded_contact).
# The earlier stranded case (full_transitional_r_stranded) is not touched.
# Status: ~/laser_wire_ded_stranded/$CASE.status   (or run status_stranded_contact.sh)
# Restart-safe: if the case already exists, the solver continues from the latest time.
SRC=/mnt/c/Users/dukyo/laser_wire_ded
W=$HOME/laser_wire_ded_stranded
CASE=${CASE:-full_transitional_r_stranded_contact}
OUT=$SRC/viz/$CASE
NP=${NP:-8}
GENARGS=${GENARGS:-"--focus-height 0 --feed-start 0"}
mkdir -p $W && cd $W || exit 1
tar xzf $SRC/lwded_src_stranded.tgz
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1 || true
ST=$W/$CASE.status
echo "$(date) start (NP=$NP)" >> $ST
(cd solver && ./Allwmake > build.log 2>&1) || { echo "$(date) BUILD FAILED" >> $ST; exit 1; }
mkdir -p $OUT
if [ ! -d $CASE/processor0 ]; then
  python3 generate_case.py --laser-config transitional_r --wire-type stranded $GENARGS --case $CASE --np $NP > gen_$CASE.log 2>&1 \
    || { echo "$(date) GENERATE FAILED" >> $ST; exit 1; }
  cp gen_$CASE.log $OUT/
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
