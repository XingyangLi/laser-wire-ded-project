#!/usr/bin/env python3
"""Where the 0.5 mm and 1.0 mm wiggle tracks are. Read-only."""
import os, re
HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, "laser_wire_ded_stranded")

def latest_time(case):
    log = os.path.join(case, "log.laserWireDEDFoam")
    end = None
    cd = os.path.join(case, "system", "controlDict")
    if os.path.isfile(cd):
        txt = open(cd, errors="replace").read()
        m = re.search(r"endTime\s+([0-9.eE+-]+)\s*;", txt)
        if m:
            end = float(m.group(1))
    t = None
    if os.path.isfile(log):
        # the log is huge; read the tail
        with open(log, "rb") as f:
            f.seek(0, 2)
            n = f.tell()
            f.seek(max(0, n - 200_000))
            tail = f.read().decode("utf-8", "replace")
        times = re.findall(r"^Time = ([0-9.eE+-]+)", tail, re.M)
        if times:
            t = float(times[-1])
    proc = os.path.isdir(os.path.join(case, "processor0"))
    return t, end, proc, os.path.isfile(log)

def main():
    for name, label in (("wiggle05mm_10mm", "0.5 mm wiggle, 10 mm track"), ("wiggle10mm_10mm", "1.0 mm wiggle, 10 mm track")):
        case = os.path.join(ROOT, name)
        print(f"--- {label}  ({name}) ---")
        if not os.path.isdir(case):
            print("  not started")
            continue
        t, end, proc, haslog = latest_time(case)
        if t is None:
            print("  case is on disk; the solver has not written a time step yet" if proc or haslog else "  generated, not meshed")
        else:
            if end:
                pct = 100.0 * t / end
                print(f"  simulation clock {t*1e3:.1f} ms of {end*1e3:.0f} ms  ({pct:.1f}%)")
            else:
                print(f"  simulation clock {t*1e3:.1f} ms")
        st = os.path.join(case, "run.status")
        if os.path.isfile(st):
            lines = open(st, errors="replace").read().strip().splitlines()
            if lines:
                print("  " + lines[-1])
        print()

if __name__ == "__main__":
    main()
