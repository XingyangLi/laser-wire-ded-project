#!/bin/bash
cd ~/laser_wire_ded; date; cat production.status
for c in normal lof transitional_r; do
  d=full_$c; echo "== $d"
  grep "^Time =" $d/log.laserWireDEDFoam 2>/dev/null | tail -1
  grep "^ExecutionTime" $d/log.laserWireDEDFoam 2>/dev/null | tail -1
  tail -n 1 $d/postProcessing/meltPool/meltPool.dat 2>/dev/null | awk '{printf "t=%s L=%.2fmm W=%.2fmm Tmax=%.0f beadH=%.3fmm beadW=%.3fmm pen=%.3fmm dilG=%.3f dilC=%.3f\n",$1,$2*1e3,$3*1e3,$6,$13*1e3,$14*1e3,$19*1e3,$20,$21}'
  grep -iE "error|fatal" $d/log.* 2>/dev/null | head -3
done
