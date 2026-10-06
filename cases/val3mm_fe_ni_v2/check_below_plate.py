#!/usr/bin/env python3
"""Wire material / never-melted wire below the original plate surface (z < 0), per written time.
Usage: ~/vizenv/bin/python check_below_plate.py <case> [t1,t2,...]   (default: all written times)
Reference (val3mm_fe_ni_defocus, no rigidSubstrate/stubFloor): wire material below plate
0.019 mm3 @0.02 s, 0.076 @0.04, 0.39 @0.10, 0.75 @0.20, ~0.9 mm3 from 0.3 s on (unmelted, z down to -0.51 mm)."""
import sys, os, glob
import numpy as np, pyvista as pv
case = sys.argv[1] if len(sys.argv) > 1 else '.'
foam = os.path.join(case, 'case.foam')
if not os.path.exists(foam):
    open(foam, 'a').close()
r = pv.POpenFOAMReader(foam)
r.case_type = 'decomposed' if os.path.isdir(os.path.join(case, 'processor0')) else 'reconstructed'
r.enable_all_cell_arrays()
times = [float(t) for t in sys.argv[2].split(',')] if len(sys.argv) > 2 else [t for t in r.time_values if t > 0]
for t in times:
    r.set_active_time_value(t)
    m = r.read()['internalMesh'].compute_cell_sizes()
    V = m['Volume']; z = m.cell_centers().points[:, 2]
    a = m['alpha.metal']; cW = m['cFe'] + m['cNi']; uS = m['uFe'] + m['uNi']
    b = z < 0
    s = b & (a*cW > 0.3)
    print(f"t={t:.3f}: wire material below plate {(a*cW*V)[b].sum()*1e9:.4f} mm3, never-melted below "
          f"{(a*uS*V)[b].sum()*1e9:.4f} mm3, deepest cW>0.3 {z[s].min()*1e3 if s.any() else 0:.3f} mm, "
          f"wire material total {(a*cW*V).sum()*1e9:.3f} mm3, metal {(a*V).sum()*1e9:.3f} mm3", flush=True)