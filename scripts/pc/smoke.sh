#!/bin/bash
# timing smoke test of the fine 3D case (8 ranks); output -> ~/laser_wire_ded/smoke_fine.out
exec > ~/laser_wire_ded/smoke_fine.out 2>&1
mkdir -p ~/laser_wire_ded && cd ~/laser_wire_ded && tar xzf /mnt/c/Users/dukyo/lwded_src.tgz
source /usr/lib/openfoam/openfoam2406/etc/bashrc || true
(cd solver && ./Allwmake > build.log 2>&1) && echo build_ok
python3 generate_case.py --case smoke_fine --resolution fine --np 8 --end-time 0.004
cd smoke_fine
./Allrun 8 || true
grep -c "^Time =" log.laserWireDEDFoam
grep "ExecutionTime" log.laserWireDEDFoam | tail -1
grep "deltaT\|MeltPool" log.laserWireDEDFoam | tail -2
grep -A3 FATAL log.* | head
echo SMOKE_DONE
