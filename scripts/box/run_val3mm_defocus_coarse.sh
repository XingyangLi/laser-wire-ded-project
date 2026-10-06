#!/bin/bash
exec > /workspace/laser_wire_ded/val3mm_fe_ni_defocus_coarse/nohup_sanity.out 2>&1
set -x
cd /workspace/laser_wire_ded/val3mm_fe_ni_defocus_coarse || exit 11
source /home/box/mamba/envs/of/etc/bashrc
source /tmp/ofenv.sh
export CXX=/home/box/mamba/envs/of/bin/x86_64-conda-linux-gnu-c++
export CC=/home/box/mamba/envs/of/bin/x86_64-conda-linux-gnu-cc
echo "START $(date) binary=$(which laserWireDEDFoam)"
./Allrun 4
echo "EXIT:$? at $(date)"
# quick viz
mkdir -p /workspace/laser_wire_ded_viz/val3mm_fe_ni_defocus_coarse
/workspace/vizenv/bin/python /workspace/laser_wire_ded/visualize.py \
  --case . --out /workspace/laser_wire_ded_viz/val3mm_fe_ni_defocus_coarse \
  --only-latest --wire-closeup-times 0.025 \
  > log.viz 2>&1
echo "VIZ_EXIT:$? at $(date)"
echo "DONE $(date)"
