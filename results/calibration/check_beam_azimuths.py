#!/usr/bin/env python3
"""Three beam axes, 120 deg apart around the wire, including the half domain.

Azimuth 0 is the travel direction (-x). 180 is behind the wire (+x).
A half-domain case sets symmetryY. Rays with y < 0 are folded to |y| and
each beam is given half its listed power, so the mirror half of the domain
is the other half of that power. All three axes have to be in the
dictionary. Leaving out the negative-y beam would put only half a side
beam in the mesh, and the spacing would no longer be equilateral.
"""
import math
import re
import sys
from pathlib import Path


def parse_beams(text):
    beams = []
    for m in re.finditer(
        r"([\w-]+)\s*\{\s*power\s+([-\d.eE+]+)\s*;\s*focus\s+\(([^)]+)\)\s*;\s*"
        r"direction\s+\(([^)]+)\)\s*;\s*radius\s+([-\d.eE+]+)\s*;",
        text,
    ):
        focus = tuple(float(v) for v in m.group(3).split())
        direction = tuple(float(v) for v in m.group(4).split())
        beams.append(
            {
                "name": m.group(1),
                "power": float(m.group(2)),
                "focus": focus,
                "direction": direction,
                "radius": float(m.group(5)),
            }
        )
    return beams


def azimuth_deg(x, y):
    """Degrees, 0 along -x, 180 along +x, matching generate_case.py."""
    return math.degrees(math.atan2(y, -x)) % 360.0


def gaps(angles):
    s = sorted(a % 360.0 for a in angles)
    return [
        (s[1] - s[0]) % 360.0,
        (s[2] - s[1]) % 360.0,
        (s[0] + 360.0 - s[2]) % 360.0,
    ]


def plate_hit(beam):
    """Where the beam axis meets the plate z = 0."""
    f = beam["focus"]
    d = beam["direction"]
    if abs(d[2]) < 1e-12:
        return None
    t = (0.0 - f[2]) / d[2]
    return tuple(f[i] + t * d[i] for i in range(3))


def check(case):
    path = Path(case) / "constant/meltProperties"
    text = path.read_text()
    if not re.search(r"symmetryY\s+true\s*;", text):
        raise SystemExit("symmetryY is not true; a half domain must fold the beams")
    beams = parse_beams(text)
    if len(beams) != 3:
        raise SystemExit(f"expected 3 beams, found {len(beams)}")
    print("symmetryY true: y < 0 rays fold to |y|, each beam carries half its listed power")
    angles = []
    for b in beams:
        fx, fy, fz = b["focus"]
        ang = azimuth_deg(fx, fy)
        angles.append(ang)
        hit = plate_hit(b)
        hit_s = (
            f"plate ({hit[0]*1e3:.3f}, {hit[1]*1e3:.3f}) mm"
            if hit else "no plate hit"
        )
        print(
            f"  {b['name']}: P {b['power']:.0f} W  "
            f"focus ({fx*1e3:.3f}, {fy*1e3:.3f}, {fz*1e3:.3f}) mm  "
            f"azimuth {ang:.1f} deg  {hit_s}"
        )
    d = gaps(angles)
    print(f"  gaps {d[0]:.1f}, {d[1]:.1f}, {d[2]:.1f} deg")
    if any(abs(g - 120.0) > 1.0 for g in d):
        raise SystemExit("beam azimuths are not 120 deg apart")
    ys = [b["focus"][1] for b in beams]
    if not any(y < -1e-6 for y in ys):
        raise SystemExit("no beam has focus y < 0; the half-domain mirror was dropped")
    if not any(y > 1e-6 for y in ys):
        raise SystemExit("no beam has focus y > 0")
    if not any(abs(y) <= 1e-6 for y in ys):
        raise SystemExit("no beam sits on the symmetry plane")
    for b in beams:
        hit = plate_hit(b)
        if hit is None:
            raise SystemExit(f"{b['name']} does not meet the plate")
        r = math.hypot(hit[0], hit[1])
        # Wire radius 0.50 mm, spot radius 0.26 mm. A centre near 0.55 mm
        # puts most of the power on the substrate and the inner wing on the wire.
        if r < 0.52e-3 or r > 0.85e-3:
            raise SystemExit(
                f"{b['name']} plate hit is {r*1e3:.2f} mm from the axis; "
                "the spot should sit just outside the wire"
            )
        print(f"  {b['name']} plate radius {r*1e3:.2f} mm")
    print("equilateral: three axes, negative-y beam kept, spots outside the wire")
    return beams


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_beam_azimuths.py CASE")
    check(sys.argv[1])


if __name__ == "__main__":
    main()
