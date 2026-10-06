#!/bin/bash
C=${1:-/workspace/laser_wire_ded/val3mm_fe_ni_defocus}
END=$(grep -m1 '^endTime' $C/system/controlDict | awk '{print $2}' | tr -d ';')
T=$(grep '^Time =' $C/log.laserWireDEDFoam 2>/dev/null | tail -1 | awk '{print $3}')
E=$(grep ExecutionTime $C/log.laserWireDEDFoam 2>/dev/null | tail -1 | awk '{print $3}')
NR=$(pgrep -c -f 'laserWireDEDFoam' 2>/dev/null || echo 0)
echo "case $C"
echo "  sim t = ${T:-?} / $END s"
echo "  wall  = ${E:-?} s"
echo "  ranks = $NR"
if [ -n "$T" ] && [ -n "$E" ]; then
  python3 -c "t=float('$T');e=float('$E');end=float('$END');r=e/max(t,1e-9);print(f'  avg {r:.0f} s wall / sim-s; remaining ~{(end-t)*r/3600:.1f} h')"
fi
grep '^MeltPool\|^Components\|^T: min' $C/log.laserWireDEDFoam 2>/dev/null | tail -4
echo "  note: analyse unmelted fractions for x > 1.5 mm (exclude start-up)"
echo "  optics: focus -1.5 mm, zR 1.2 mm -> spot Ø plate 1.70 mm (1.70×), at z=+1 mm 2.51 mm"
