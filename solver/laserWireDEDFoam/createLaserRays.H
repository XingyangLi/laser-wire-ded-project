// ---------------------------------------------------------------------------
// Multi-beam laser, ray tracing set-up.
//
// laser
// {
//     beams ( name { power P; focus (x y z); direction (dx dy dz); radius w;
//                    profile gaussian|tophat; } ... );
//     raySpacingFactor 0.5;   // ray spacing / dx_min (beam cross-section grid)
//     rayStepFactor    0.33;  // march step / dx_min
//     planar2D false; width2D w2;   // quasi-2D: rays in the x-z plane only
// }
// Each beam is a bundle of parallel rays on a square grid in the plane normal
// to the beam axis through the focus. Gaussian: I = 2P/(pi w^2) exp(-2 r^2/w^2)
// (w = 1/e^2 radius), truncated at 2w and renormalised; top-hat: r <= w.
// Optional rayleighLength zR: the sampling radius is expanded to
//   w_eff = w0 * sqrt(1 + (z_plate/zR)^2)
// where z_plate is the distance along the beam from the focus to the plane
// the spot is evaluated on. Without trackSurface that plane is the substrate
// top (z = 0), so a waist below the plate illuminates a larger spot (paraxial
// / collimated-ray approximation of a caustic). With trackSurface the focus
// sits on the free surface and z_plate is zero, so the waist is the spot.
// Each ray carries a fixed power. The cells crossed (in order) are stored per
// processor. A weave rebuilds the rays when the head has moved sideways by
// about a quarter of a fine cell (retraceLaser, called from updateWeave.H).
// trackSurface (see trackLaserSurface.H) rebuilds them when the free-surface
// height at an aim moves by about the same amount. The dictionary focus is
// the starting value; its (x, y) stays the aim and its z is the fallback if
// the aim is off the mesh. The focus (x, y) is shifted by weaveY.
// ---------------------------------------------------------------------------
DynamicList<scalar> rayPower;          // W (full ray power, before ramp/absorption)
DynamicList<label>  rayBeam;
List<DynamicList<label>> rayCellsDyn;  // local cells along ray (in order)
List<DynamicList<label>> raySampDyn;   // global sample index of each local cell
wordList beamNames;
scalarList beamPower;
List<labelList> rayCells, raySamp;
List<point> beamFocus;          // runtime focus; z tracks the free surface
bool trackLaserSurface = false;
scalar laserTrackDz = 0;
{
    const dictionary& ld0 = meltProperties.subDict("laser");
    trackLaserSurface = ld0.getOrDefault<bool>("trackSurface", false);
    if (trackLaserSurface)
    {
        Info<< "Laser trackSurface: each focus height follows the free surface"
            << " at that beam's aim" << nl << endl;
    }
}
retraceLaser = [&]()
{
    const dictionary& ld = meltProperties.subDict("laser");
    const bool planar = ld.getOrDefault<bool>("planar2D", false);
    const scalar width2D = ld.getOrDefault<scalar>("width2D", 1e-3);
    const scalar dxMin = 1.0/max(gMax(mesh.deltaCoeffs().primitiveField()), SMALL);
    const scalar hRay = ld.getOrDefault<scalar>("raySpacingFactor", 0.5)*dxMin;
    const scalar dsRay = ld.getOrDefault<scalar>("rayStepFactor", 0.33)*dxMin;

    // symmetryY: the mesh is the half y >= 0 of a domain symmetric about y = 0.
    // Rays are traced in the full (mirrored) domain and folded back with
    // y -> |y|; each ray then carries half its power (the mirror half of the
    // domain receives the other half).
    const bool symY = ld.getOrDefault<bool>("symmetryY", false);
    boundBox bb(mesh.points(), true);    // global bounds
    point bmin = bb.min();
    const point bmax = bb.max();
    if (symY) bmin.y() = -bmax.y();
    const scalar yMid = 0.5*(bmin.y() + bmax.y());
    const scalar dyMesh = bmax.y() - bmin.y();

    const PtrList<entry> beamEntries(ld.lookup("beams"));
    beamNames.setSize(beamEntries.size());
    beamPower.setSize(beamEntries.size());
    rayPower.clear();
    rayBeam.clear();
    // Keep a focus z written by trackLaserSurface. The dictionary value is
    // only the initial height.
    if (beamFocus.size() != beamEntries.size())
    {
        beamFocus.setSize(beamEntries.size());
        forAll(beamEntries, bi)
        {
            beamFocus[bi] = beamEntries[bi].dict().get<point>("focus");
        }
    }

    DynamicList<List<label>> cellsAll, sampAll;
    label nSamplesTot = 0;
    forAll(beamEntries, bi)
    {
        const dictionary& bd = beamEntries[bi].dict();
        beamNames[bi] = beamEntries[bi].keyword();
        const scalar P = bd.get<scalar>("power");
        beamPower[bi] = P;
        point F = beamFocus[bi];
        F.y() += weaveY;   // head zigzag (0 when the weave is off)
        vector d(bd.get<vector>("direction"));
        if (planar) { d.y() = 0; F.y() = yMid; }
        d /= mag(d) + VSMALL;
        const scalar w0 = bd.get<scalar>("radius");   // 1/e^2 waist at focus
        const scalar zR = bd.getOrDefault<scalar>("rayleighLength", -1.0);
        // Distance along the beam from the focus to the plane the spot is
        // sized on. trackSurface puts the focus on the free surface, so the
        // waist is the spot there. Otherwise the plane is the substrate top.
        const scalar zRef = trackLaserSurface ? F.z() : 0.0;
        scalar zPlate = 0;
        if (mag(d.z()) > SMALL)
        {
            zPlate = mag((zRef - F.z())/d.z());
        }
        // Sampling radius of the parallel-ray bundle. Expands when the waist
        // is defocused away from the sizing plane (z = 0, or the free surface
        // when trackSurface holds the focus there).
        scalar w = w0;
        if (zR > SMALL)
        {
            w = w0*Foam::sqrt(1.0 + sqr(zPlate/zR));
        }
        const word prof(bd.getOrDefault<word>("profile", "gaussian"));
        const scalar rMax = (prof == "tophat") ? w : 2*w;

        // orthonormal basis (u, v) normal to d
        vector u = (mag(d.z()) < 0.9) ? (d ^ vector(0, 0, 1)) : (d ^ vector(1, 0, 0));
        if (planar) u = d ^ vector(0, 1, 0);
        u /= mag(u);
        vector v = d ^ u; v /= mag(v);

        const label n = ceil(rMax/hRay);
        DynamicList<point> org;
        DynamicList<scalar> wt;
        scalar wsum = 0;
        for (label i = -n; i <= n; ++i)
        {
            for (label j = (planar ? 0 : -n); j <= (planar ? 0 : n); ++j)
            {
                const scalar a = i*hRay, b = j*hRay;
                const scalar r2 = planar ? sqr(a) : sqr(a) + sqr(b);
                if (r2 > sqr(rMax)) continue;
                scalar I = (prof == "tophat") ? 1.0 : Foam::exp(-2*r2/sqr(w));
                org.append(F + a*u + b*v);
                wt.append(I);
                wsum += I;
            }
        }
        // power per ray: full beam power P (3D), P*dy/width2D (planar)
        const scalar Pb = planar ? P*dyMesh/width2D : (symY ? 0.5*P : P);
        forAll(org, ri)
        {
            // intersect line org + s d with the bounding box (slab method)
            scalar s0 = -GREAT, s1 = GREAT;
            bool hit = true;
            for (direction k = 0; k < 3; ++k)
            {
                if (mag(d[k]) < 1e-12)
                {
                    if (org[ri][k] < bmin[k] || org[ri][k] > bmax[k]) hit = false;
                }
                else
                {
                    scalar t0 = (bmin[k] - org[ri][k])/d[k];
                    scalar t1 = (bmax[k] - org[ri][k])/d[k];
                    if (t0 > t1) std::swap(t0, t1);
                    s0 = max(s0, t0); s1 = min(s1, t1);
                }
            }
            if (!hit || s1 <= s0) continue;
            const label ns = label((s1 - s0)/dsRay) + 1;
            DynamicList<label> cl, sl;
            label lastCell = -1;
            for (label k = 0; k < ns; ++k)
            {
                point p = org[ri] + (s0 + (k + 0.5)*dsRay)*d;
                if (symY) p.y() = mag(p.y());
                const label c = mesh.findCell(p);
                if (c >= 0 && c != lastCell)
                {
                    cl.append(c);
                    sl.append(k);
                    lastCell = c;
                }
            }
            nSamplesTot += ns;
            rayPower.append(Pb*wt[ri]/max(wsum, VSMALL));
            rayBeam.append(bi);
            cellsAll.append(cl);
            sampAll.append(sl);
        }
        Info<< "Laser beam " << beamNames[bi] << ": P = " << P << " W, focus " << F
            << ", direction " << d << ", w0 = " << w0 << " m";
        if (zR > SMALL)
        {
            const scalar w1mm = w0*Foam::sqrt(1.0 + sqr((zPlate + 0.001/max(mag(d.z()), SMALL))/zR));
            Info<< ", zR = " << zR << " m, |z|_plate = " << zPlate
                << " m -> w_plate = " << w << " m (" << w/w0 << " x w0)"
                << ", w(z=1mm) ~ " << w1mm << " m";
        }
        else
        {
            Info<< ", radius = " << w << " m (collimated)";
        }
        Info<< " (" << prof << "), rays " << org.size() << endl;
    }
    rayCells.setSize(cellsAll.size());
    raySamp.setSize(sampAll.size());
    forAll(cellsAll, i) { rayCells[i] = cellsAll[i]; raySamp[i] = sampAll[i]; }
    Info<< "Laser rays: " << rayPower.size() << " rays in the domain, "
        << nSamplesTot << " samples, spacing " << hRay << " m, step " << dsRay
        << " m, focus shifted in y by " << weaveY << " m" << nl << endl;
    weaveRetraceDy = 0.25*dxMin;
    weaveYTraced = weaveY;
    if (laserTrackDz <= SMALL) laserTrackDz = 0.25*dxMin;
};
retraceLaser();

#include "trackLaserSurface.H"
if (trackLaserFoci())
{
    retraceLaser();
}
