#!/bin/bash
# Generic status: uses dedicated status script if present, else a short summary.
CASE_NAME="${1:-val3mm_fe_ni_v2}"
if [[ "$CASE_NAME" == /* ]]; then
  C="$CASE_NAME"
else
  C="$HOME/laser_wire_ded_stranded/$CASE_NAME"
fi
REPO=/mnt/c/Users/dukyo/laser_wire_ded_project
if [ -x "$C/status_${CASE_NAME}.sh" ]; then
  bash "$C/status_${CASE_NAME}.sh" "$C"
  exit $?
fi
if [ -x "$REPO/scripts/pc/status_${CASE_NAME}.sh" ]; then
  bash "$REPO/scripts/pc/status_${CASE_NAME}.sh" "$C"
  exit $?
fi
# Fallback short status (same idea as status_val3mm_fe_ni_v2.sh)
L=$C/log.laserWireDEDFoam
END=$(grep -m1 '^endTime' $C/system/controlDict 2>/dev/null | awk '{print $2}' | tr -d ';')
T=$(grep '^Time =' $L 2>/dev/null | tail -1 | awk '{print $3}')
E=$(grep ExecutionTime $L 2>/dev/null | tail -1 | awk '{print $3}')
NR=$(pgrep -c -f 'laserWireDEDFoam -parallel' 2>/dev/null || echo 0)
echo "case $C"
echo "  sim t = ${T:-?} / ${END:-?} s   wall = ${E:-?} s   solver processes = $NR"
tail -5 $C/run.status 2>/dev/null | sed 's/^/  status: /' || true
tail -3 ${C}.status 2>/dev/null | sed 's/^/  status: /' || true
if [ -f "$L" ] && [ -n "$END" ]; then
  python3 - "$L" "$END" <<'PY'
import sys, time, datetime, os
log, end = sys.argv[1], float(sys.argv[2])
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
    j = max(0, next((i for i in range(len(es)) if es[i] >= 0.9*e1), 0) - 1)
    rr = (e1 - es[j])/max(t1 - ts[j], 1e-12) if t1 > ts[j] else e1/max(t1, 1e-12)
    rem = (end - t1)*rr
    age = time.time() - os.path.getmtime(log)
    eta = datetime.datetime.now() + datetime.timedelta(seconds=rem - age)
    print(f"  rate: recent {rr/3600:.2f} h wall per sim-s;  {100*t1/end:.1f}% done")
    print(f"  remaining ~{rem/3600:.1f} h  ->  ETA {eta:%a %b %d %H:%M} CT  (log updated {age:.0f} s ago)")
PY
fi
echo "  binary PATH tip: which laserWireDEDFoam after 'export PATH=$HOME/lwded_bin:\$PATH'"
pgrep -af laserWireDEDFoam 2>/dev/null | head -3 | sed 's/^/  proc: /' || true
