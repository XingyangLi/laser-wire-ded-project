#!/bin/bash
# Production runs of the three Gao et al. (2026) laser configurations on Dukyong_PC (WSL).
# Invar36 wire on SS304 substrate, 3D half domain, medium mesh (100 um), 5 MPI ranks each,
# all three in parallel; then automatic rendering to C:\Users\dukyo\laser_wire_ded\viz\<case>.
# Status: ~/laser_wire_ded/production.status
SRC=/mnt/c/Users/dukyo/laser_wire_ded
WIN_VIZ=$SRC/viz
NP=${NP:-5}
RES=${RES:-medium}
CONFIGS=${CONFIGS:-"normal lof transitional_r"}
cd ~/laser_wire_ded || exit 1
tar xzf $SRC/lwded_src.tgz
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1 || true
ST=~/laser_wire_ded/production.status
echo "$(date) start (NP=$NP RES=$RES)" > $ST
(cd solver && ./Allwmake > build.log 2>&1) || { echo "$(date) BUILD FAILED" >> $ST; exit 1; }
rm -rf smoke_fine
for c in $CONFIGS; do
  (
    case=full_$c
    if [ ! -d $case/processor0 ]; then
      python3 generate_case.py --laser-config $c --case $case --resolution $RES --np $NP > gen_$c.log 2>&1
      cd $case && ./Allrun $NP; rc=$?; cd ..
    else
      cd $case && mpirun -np $NP laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1; rc=$?; cd ..
    fi
    echo "$(date) $case solver finished rc=$rc" >> $ST
    mkdir -p $WIN_VIZ/$case
    ~/vizenv/bin/python visualize.py --case $case --out $WIN_VIZ/$case > $case/log.visualize 2>&1
    echo "$(date) $case rendered rc=$?" >> $ST
  ) &
  sleep 5
done
wait
echo "$(date) ALL DONE" >> $ST
