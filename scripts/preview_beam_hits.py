#!/usr/bin/env python3
"""Where each beam axis first meets the vertical wire, marching downward."""
import math

R = 0.5e-3
Z_TOP = 3.5e-3


def trace(name, az, th, aim_r, aim_z, radius):
    phi = math.radians(az)
    thb = math.radians(th)
    sx, sy = -math.cos(phi), math.sin(phi)
    d = (math.sin(thb) * sx, math.sin(thb) * sy, -math.cos(thb))
    mag = math.sqrt(sum(c * c for c in d)) or 1.0
    d = tuple(c / mag for c in d)
    aim = (aim_r * sx, aim_r * sy, aim_z)
    s_hi = (Z_TOP - aim[2]) / d[2]
    s_lo = (-0.2e-3 - aim[2]) / d[2]
    if s_lo < s_hi:
        s_hi, s_lo = s_lo, s_hi
    hit_z = None
    prev_out = None
    n = 8000
    for i in range(n + 1):
        s = s_hi + (s_lo - s_hi) * i / n
        p = tuple(aim[k] + s * d[k] for k in range(3))
        outside = math.hypot(p[0], p[1]) > R
        if prev_out is True and not outside and p[2] > 0:
            hit_z = p[2]
            break
        prev_out = outside
    s0 = (0.0 - aim[2]) / d[2]
    p0 = tuple(aim[k] + s0 * d[k] for k in range(3))
    hit = "misses the wire" if hit_z is None else "first hit z = %.2f mm" % (hit_z * 1e3)
    print(
        "%s  th=%g deg  aim r=%.2f z=%.2f mm  w=%.2f mm"
        % (name, th, aim_r * 1e3, aim_z * 1e3, radius * 1e3)
    )
    print("   " + hit)
    print(
        "   axis at z=0: x=%.2f y=%.2f mm"
        % (p0[0] * 1e3, p0[1] * 1e3)
    )


def main():
    # Negative inclination: the beam moves inward as it descends, so the first
    # shadowed hit is low on the wire. "inner"/"outer" shift the axis by one
    # 1/e^2 radius toward / away from the wire.
    rows = [
        ("cal08 front", 30, -26, 0.60e-3, 0.08e-3, 0.26e-3),
        ("cal08 front inner", 30, -26, 0.34e-3, 0.08e-3, 0.26e-3),
        ("cal08 front 2w", 30, -26, 0.08e-3, 0.08e-3, 0.26e-3),
        ("cal08 front outer", 30, -26, 0.86e-3, 0.08e-3, 0.26e-3),
        ("cal08 rear", 180, -38, 0.24e-3, 0.55e-3, 0.26e-3),
        ("cal08 rear inner", 180, -38, -0.02e-3, 0.55e-3, 0.26e-3),
        ("cal08 rear 2w", 180, -38, -0.28e-3, 0.55e-3, 0.26e-3),
        ("cal08 rear outer", 180, -38, 0.50e-3, 0.55e-3, 0.26e-3),
    ]
    for name, az, th, ar, azh, w in rows:
        trace(name, az, th, ar, azh, w)


if __name__ == "__main__":
    main()
