#!/bin/bash
# Box: full fe_ni_5strand_invar run (8 ranks) + renders into /workspace/laser_wire_ded_viz/fe_ni_5strand_invar
# Restart-safe: controlDict startFrom latestTime -> re-running continues from the last written time.
cd /workspace/laser_wire_ded/fe_ni_5strand_invar || exit 1
source /workspace/laser_wire_ded/box_ofenv.sh
if [ ! -d processor0 ]; then
    ./Allrun 8
else
    mpirun -np 8 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1
fi
/workspace/vizenv/bin/python /workspace/laser_wire_ded/visualize_multicomp.py --case . \
    --out /workspace/laser_wire_ded_viz/fe_ni_5strand_invar > log.viz 2>&1
/workspace/vizenv/bin/python /workspace/laser_wire_ded/visualize.py --case . \
    --out /workspace/laser_wire_ded_viz/fe_ni_5strand_invar/standard --only-latest >> log.viz 2>&1
