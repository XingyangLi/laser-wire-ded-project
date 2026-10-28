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


def radial(az, th, aim_r, aim_z, z):
    """Horizontal radius of the beam axis at height z."""
    phi = math.radians(az)
    thb = math.radians(th)
    sx, sy = -math.cos(phi), math.sin(phi)
    d = (math.sin(thb) * sx, math.sin(thb) * sy, -math.cos(thb))
    mag = math.sqrt(sum(c * c for c in d)) or 1.0
    d = tuple(c / mag for c in d)
    s = (z - aim_z) / d[2]
    x = aim_r * sx + s * d[0]
    y = aim_r * sy + s * d[1]
    return math.hypot(x, y)


def inner_ray_on_plate(az, th_deg, aim_r, w):
    """Radius on z = 0 of the ray one 1/e^2 radius toward the wire in the focal plane."""
    phi = math.radians(az)
    th = math.radians(th_deg)
    sx, sy = -math.cos(phi), math.sin(phi)
    d = (math.sin(th) * sx, math.sin(th) * sy, -math.cos(th))
    mag = math.sqrt(sum(c * c for c in d)) or 1.0
    d = tuple(c / mag for c in d)
    inward = (-sx, -sy, 0.0)
    dot = sum(inward[i] * d[i] for i in range(3))
    n = tuple(inward[i] - dot * d[i] for i in range(3))
    nm = math.sqrt(sum(c * c for c in n)) or 1.0
    n = tuple(c / nm for c in n)
    origin = (aim_r * sx + w * n[0], aim_r * sy + w * n[1], w * n[2])
    t = (0.0 - origin[2]) / d[2]
    hit = tuple(origin[i] + t * d[i] for i in range(3))
    return math.hypot(hit[0], hit[1])


def wire_exit_height(az, th_deg, aim_r, w, radius):
    """Height where the inner ray leaves the wire cylinder, marching upward from the plate."""
    # Reuse the plate hit and the same direction by sampling radius vs z.
    phi = math.radians(az)
    th = math.radians(th_deg)
    sx, sy = -math.cos(phi), math.sin(phi)
    d = (math.sin(th) * sx, math.sin(th) * sy, -math.cos(th))
    mag = math.sqrt(sum(c * c for c in d)) or 1.0
    d = tuple(c / mag for c in d)
    inward = (-sx, -sy, 0.0)
    dot = sum(inward[i] * d[i] for i in range(3))
    n = tuple(inward[i] - dot * d[i] for i in range(3))
    nm = math.sqrt(sum(c * c for c in n)) or 1.0
    n = tuple(c / nm for c in n)
    origin = (aim_r * sx + w * n[0], aim_r * sy + w * n[1], w * n[2])

    def r_at(z):
        s = (z - origin[2]) / d[2]
        q = tuple(origin[i] + s * d[i] for i in range(3))
        return math.hypot(q[0], q[1])

    if r_at(0.0) >= radius:
        return None
    lo, hi = 0.0, 3.0e-3
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if r_at(mid) < radius:
            lo = mid
        else:
            hi = mid
    return hi


def check_baseline():
    """Triple defaults: 120 deg apart, centre on the substrate, inner edge on the wire."""
    rows = [
        ("front", 60.0, -32.0, 1.05e-3, 0.70e-3),
        ("front", -60.0, -32.0, 1.05e-3, 0.70e-3),
        ("rear", 180.0, -22.0, 0.90e-3, 0.55e-3),
    ]
    az = [r[1] for r in rows]
    gaps = []
    for i in range(3):
        dlt = abs(az[(i + 1) % 3] - az[i])
        gaps.append(min(dlt, 360.0 - dlt))
    if any(abs(g - 120.0) > 1e-6 for g in gaps):
        raise SystemExit(f"azimuths are not 120 deg apart: {gaps}")
    R = 0.5e-3
    for name, azi, th, aim_r, w in rows:
        r0 = radial(azi, th, aim_r, 0.0, 0.0)
        r_hi = radial(azi, th, aim_r, 0.0, 2.0e-3)
        r_in = inner_ray_on_plate(azi, th, aim_r, w)
        z_leave = wire_exit_height(azi, th, aim_r, w, R)
        if not (r0 > R):
            raise SystemExit(f"{name} centre at the plate is inside the wire ({r0*1e3:.3f} mm)")
        if not (r_hi > r0 + 0.2e-3):
            raise SystemExit(f"{name} centre does not clear the wire above the plate")
        if not (r_in < R):
            raise SystemExit(f"{name} inner 1/e^2 ray misses the wire ({r_in*1e3:.3f} mm)")
        if z_leave is None or not (0.2e-3 < z_leave < 1.0e-3):
            raise SystemExit(f"{name} inner ray does not meet the wire tip ({z_leave})")
        print(
            "%s az %+g: plate centre %.2f mm, 2 mm up %.2f mm, "
            "inner ray plate r %.2f mm, meets wire up to %.2f mm"
            % (name, azi, r0 * 1e3, r_hi * 1e3, r_in * 1e3, z_leave * 1e3)
        )
    print("baseline geometry ok")


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
    print()
    check_baseline()


if __name__ == "__main__":
    main()
