#!/bin/bash
# Status of val3mm_fe_ni_v2: sim time, speed, ETA (CT), pool / bead from meltPool.dat
C=${1:-$HOME/laser_wire_ded_stranded/val3mm_fe_ni_v2}
L=$C/log.laserWireDEDFoam
END=$(grep -m1 '^endTime' $C/system/controlDict | awk '{print $2}' | tr -d ';')
T=$(grep '^Time =' $L 2>/dev/null | tail -1 | awk '{print $3}')
E=$(grep ExecutionTime $L 2>/dev/null | tail -1 | awk '{print $3}')
NR=$(pgrep -c -f 'laserWireDEDFoam -parallel' 2>/dev/null || echo 0)
echo "case $C"
echo "  sim t = ${T:-?} / $END s   wall = ${E:-?} s   solver processes = $NR"
tail -3 $C/run.status 2>/dev/null | sed 's/^/  status: /'
MP=$C/postProcessing/meltPool/meltPool.dat
python3 - "$L" "$END" "$MP" <<'PY'
import sys, re, time, datetime, os
log, end, mp = sys.argv[1], float(sys.argv[2]), sys.argv[3]
ts, es = [], []
t = None
try:
    with open(log, errors='ignore') as fh:
        for line in fh:
            if line.startswith('Time = '):
                t = float(line.split()[2])
            elif line.startswith('ExecutionTime') and t is not None:
                ts.append(t); es.append(float(line.split()[2]))
except FileNotFoundError:
    pass
if len(ts) > 2:
    t1, e1 = ts[-1], es[-1]
    # recent rate over the last ~10% of wall time (falls back to the average)
    j = max(0, next((i for i in range(len(es)) if es[i] >= 0.9*e1), 0) - 1)
    rr = (e1 - es[j])/max(t1 - ts[j], 1e-12) if t1 > ts[j] else e1/max(t1, 1e-12)
    ra = e1/max(t1, 1e-12)
    rem = (end - t1)*rr
    age = time.time() - os.path.getmtime(log)
    eta = datetime.datetime.now() + datetime.timedelta(seconds=rem - age)
    print(f"  rate: recent {rr/3600:.2f} h wall per sim-s (avg {ra/3600:.2f});  {100*t1/end:.1f}% done")
    print(f"  remaining ~{rem/3600:.1f} h  ->  ETA {eta:%a %b %d %H:%M} CT  (log updated {age:.0f} s ago)")
try:
    with open(mp) as fh:
        hdr = fh.readline().lstrip('#').split()
        last = None
        for line in fh:
            if line.strip(): last = line
    if last:
        v = dict(zip([h.split('[')[0] for h in hdr], map(float, last.split())))
        mm = lambda k: v.get(k, float('nan'))*1e3
        print(f"  t={v['time']:.4f} s: pool L {mm('poolLength'):.2f} W {mm('poolWidth'):.2f} D {mm('poolDepth'):.3f} mm, "
              f"Tmax {v['Tmax']:.0f} K, wire tip z {mm('wireTipZ'):.2f} mm")
        print(f"  bead h {mm('beadHeight'):.3f} mm, w {mm('beadWidth'):.2f} mm, area {v['beadArea']*1e6:.3f} mm2, "
              f"penetration {mm('penetration'):.3f} mm  (probe x {mm('probeX'):.2f} mm)")
        print(f"  metal volume {v['metalVolume']*1e9:.3f} mm3, laser absorbed {v['laserAbsorbed']:.0f} W")
except FileNotFoundError:
    print("  (no meltPool.dat yet)")
PY
grep '^Components' $L 2>/dev/null | tail -1 | sed 's/^/  /'
echo "  sinking check (needs a written time): ~/vizenv/bin/python $C/check_below_plate.py $C"