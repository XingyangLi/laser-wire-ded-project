#!/bin/bash
# progress of a fe_ni case (default: the full run)
C=${1:-/workspace/laser_wire_ded/fe_ni_5strand_invar}
END=$(grep -m1 '^endTime' $C/system/controlDict | awk '{print $2}' | tr -d ';')
T=$(grep '^Time =' $C/log.laserWireDEDFoam | tail -1 | awk '{print $3}')
E=$(grep ExecutionTime $C/log.laserWireDEDFoam | tail -1 | awk '{print $3}')
echo "case $C: t = $T / $END s, wall $E s, running ranks: $(pgrep -c -x laserWireDEDFoa)"
python3 -c "t=float('$T');e=float('$E');end=float('$END');r=e/max(t,1e-9);print(f'avg {r:.0f} s wall per sim-s; remaining ~{(end-t)*r/3600:.1f} h at the average rate')"
grep '^MeltPool\|^Components' $C/log.laserWireDEDFoam | tail -2
