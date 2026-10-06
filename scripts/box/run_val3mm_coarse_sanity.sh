#!/bin/bash
exec > /workspace/laser_wire_ded/val3mm_fe_ni_coarse_sanity/nohup_sanity.out 2>&1
set -x
cd /workspace/laser_wire_ded/val3mm_fe_ni_coarse_sanity || exit 11
echo "cwd=$(pwd)"
source /home/box/mamba/envs/of/etc/bashrc
echo "after mamba bashrc"
source /tmp/ofenv.sh
echo "after ofenv PATH=$PATH"
export CXX=/home/box/mamba/envs/of/bin/x86_64-conda-linux-gnu-c++
export CC=/home/box/mamba/envs/of/bin/x86_64-conda-linux-gnu-cc
which laserWireDEDFoam || echo "NO BINARY"
which blockMesh || echo "NO blockMesh"
echo "start $(date)"
./Allrun 4
echo "EXIT:$?"
echo "done $(date)"
