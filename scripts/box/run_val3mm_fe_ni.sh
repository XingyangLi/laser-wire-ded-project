#!/bin/bash
# Detached 3 mm Fe+Ni validation run with melting/absorptivity fixes.
# Restart-safe: continues from latestTime if processor dirs exist.
exec > >(tee -a /workspace/laser_wire_ded/val3mm_fe_ni/nohup_full.out) 2>&1
set -x
cd /workspace/laser_wire_ded/val3mm_fe_ni || exit 1
source /home/box/mamba/envs/of/etc/bashrc
source /tmp/ofenv.sh
export CXX=/home/box/mamba/envs/of/bin/x86_64-conda-linux-gnu-c++
export CC=/home/box/mamba/envs/of/bin/x86_64-conda-linux-gnu-cc
echo "START $(date)  binary=$(which laserWireDEDFoam)"
if [ ! -d processor0 ]; then
    ./Allrun 8
else
    echo "Restarting from latestTime..."
    mpirun -np 8 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1
fi
echo "SOLVER_EXIT:$? at $(date)"
mkdir -p /workspace/laser_wire_ded_viz/val3mm_fe_ni
/workspace/vizenv/bin/python /workspace/laser_wire_ded/visualize_multicomp.py \
    --case . --out /workspace/laser_wire_ded_viz/val3mm_fe_ni \
    > log.viz 2>&1
/workspace/vizenv/bin/python /workspace/laser_wire_ded/visualize.py \
    --case . --out /workspace/laser_wire_ded_viz/val3mm_fe_ni/standard --only-latest \
    >> log.viz 2>&1
echo "VIZ_EXIT:$? at $(date)"
echo "DONE $(date)"
