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
// where z_plate is the distance along the beam from the focus to the substrate
// top (z = 0). That makes a defocused waist below the plate illuminate a larger
// spot on the plate (paraxial / collimated-ray approximation of a caustic).
// Each ray carries a fixed power. The cells crossed (in order) are stored per
// processor. A weave rebuilds the rays when the head has moved sideways by
// about a quarter of a fine cell (retraceLaser, called from updateWeave.H).
// The focus read from the dictionary is shifted by weaveY.
//
// Positive inclination aims the spot further out than the focus, so the line
// above the focus runs back through the wire. That segment is not the path
// onto the plate: samples above the focus (s < 0) that still lie inside the
// wire radius are omitted. From the focus downward, and anywhere the ray is
// already outside the wire, the first metal cell takes the ray. A bead grown
// outside the wire stops the rear beam before the plate. The inner part of
// the spot still meets the wire at the aim height.
// ---------------------------------------------------------------------------
DynamicList<scalar> rayPower;          // W (full ray power, before ramp/absorption)
DynamicList<label>  rayBeam;
List<DynamicList<label>> rayCellsDyn;  // local cells along ray (in order)
List<DynamicList<label>> raySampDyn;   // global sample index of each local cell
wordList beamNames;
scalarList beamPower;
List<labelList> rayCells, raySamp;
retraceLaser = [&]()
{
    const dictionary& ld = meltProperties.subDict("laser");
    const bool planar = ld.getOrDefault<bool>("planar2D", false);
    const scalar width2D = ld.getOrDefault<scalar>("width2D", 1e-3);
    const scalar dxMin = 1.0/max(gMax(mesh.deltaCoeffs().primitiveField()), SMALL);
    // Neck cells can be a few micrometres. The beam radius is 0.26 mm, so
    // ray spacing stops following the mesh below 15 um. Finer than that the
    // march is billions of findCell calls and never reaches the time loop.
    const scalar dxRay = max(dxMin, scalar(1.5e-5));
    const scalar hRay = ld.getOrDefault<scalar>("raySpacingFactor", 0.5)*dxRay;
    const scalar dsRay = ld.getOrDefault<scalar>("rayStepFactor", 0.33)*dxRay;

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

    DynamicList<List<label>> cellsAll, sampAll;
    label nSamplesTot = 0;
    forAll(beamEntries, bi)
    {
        const dictionary& bd = beamEntries[bi].dict();
        beamNames[bi] = beamEntries[bi].keyword();
        const scalar P = bd.get<scalar>("power");
        beamPower[bi] = P;
        point F(bd.get<point>("focus"));
        F.y() += weaveY;   // head zigzag (0 when the weave is off)
        vector d(bd.get<vector>("direction"));
        if (planar) { d.y() = 0; F.y() = yMid; }
        d /= mag(d) + VSMALL;
        const scalar w0 = bd.get<scalar>("radius");   // 1/e^2 waist at focus
        const scalar zR = bd.getOrDefault<scalar>("rayleighLength", -1.0);
        // Distance along the beam from focus to the substrate top plane z = 0.
        // F + t d has z = 0 => t = -F.z()/d.z(); z_plate = |t|.
        scalar zPlate = 0;
        if (mag(d.z()) > SMALL)
        {
            zPlate = mag(-F.z()/d.z());
        }
        // Effective sampling radius at the plate (and used for the parallel-ray
        // cylinder): expands when the waist is defocused away from z = 0.
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
                const scalar sHere = s0 + (k + 0.5)*dsRay;
                point p = org[ri] + sHere*d;
                if (symY) p.y() = mag(p.y());
                // Above the focus the outward ray track passes through the
                // wire column. Skip that segment so the spot on the plate,
                // and a bead outside the wire, are not shadowed by the shaft.
                if (sHere < 0
                    && Foam::hypot(p.x() - wireOrigin.x(), p.y() - wireOrigin.y())
                       < wireRadius)
                {
                    continue;
                }
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
};
retraceLaser();
