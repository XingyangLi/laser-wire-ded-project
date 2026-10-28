// ---------------------------------------------------------------------------
// Ray-traced laser heat source (multi-beam, inclined beams)
// For every ray the first sample (march order) whose cell has alpha >= alphaHit
// is found across all processors (min-reduction of the global sample index);
// the processor owning that cell deposits A(cWire) * P_ray there.
// Metal behind that point (along the ray) is shadowed: the wire shadows the
// pool and vice versa, and each beam can hit the wire side.
// The same routine also computes the column surface height zSurface.
// trackLaserFoci() (trackLaserSurface.H) may move each focus onto the free
// surface at its aim and rebuild the rays before this deposition.
// ---------------------------------------------------------------------------
{
    if (trackLaserFoci())
    {
        retraceLaser();
    }

    const dictionary& lDict = meltProperties.subDict("laser");
    const bool   lOn     = lDict.getOrDefault<bool>("enabled", true);
    const scalar lStart  = lDict.getOrDefault<scalar>("tStart", 0.0);
    const scalar lRamp   = lDict.getOrDefault<scalar>("tRamp", 0.0);
    const scalar lStop   = lDict.getOrDefault<scalar>("tStop", GREAT);
    const bool   lShadow = lDict.getOrDefault<bool>("shadowing", true);
    const scalar aHit    = lDict.getOrDefault<scalar>("alphaHit", 0.5);
    const scalar pScale  = lDict.getOrDefault<scalar>("powerScale", 1.0);

    scalar ramp = 1.0;
    const scalar t = runTime.value();
    if (!lOn || t < lStart || t > lStop) ramp = 0.0;
    else if (lRamp > SMALL) ramp = min((t - lStart)/lRamp, 1.0);

    // Optional brief scale on one beam (index into the beams list, 0-based).
    // Absent from the dictionary, every beam keeps ramp*powerScale.
    scalar dipScale = 1.0;
    label dipBeam = -1;
    if (lDict.found("powerDip"))
    {
        const dictionary& dip = lDict.subDict("powerDip");
        dipBeam = dip.getOrDefault<label>("beam", 2);
        const scalar t0 = dip.get<scalar>("tStart");
        const scalar t1 = dip.get<scalar>("tEnd");
        const scalar fac = dip.getOrDefault<scalar>("factor", 0.3);
        if (t >= t0 && t < t1) dipScale = fac;
        static bool dipNoted = false;
        if (!dipNoted && t >= t0 && t < t1)
        {
            Info<< "Laser powerDip: beam " << dipBeam
                << " x" << fac << " on [" << t0 << ", " << t1 << ") s" << endl;
            dipNoted = true;
        }
    }

    const scalarField& V = mesh.V();
    scalarField& Q = Qheat.primitiveFieldRef();
    Q = 0.0;

    labelList hit(rayPower.size(), labelMax);
    forAll(rayCells, ri)
    {
        const labelList& cl = rayCells[ri];
        forAll(cl, k)
        {
            const label c = cl[k];
            if (!lShadow && inWireZone[c] && liquidFraction[c] < 0.5) continue;
            if (alpha1[c] >= aHit) { hit[ri] = raySamp[ri][k]; break; }
        }
    }
    Pstream::listCombineReduce(hit, minEqOp<label>());

    scalar incident = 0, missed = 0;
    forAll(rayCells, ri)
    {
        scalar bscale = 1.0;
        if (dipBeam >= 0 && ri < rayBeam.size() && rayBeam[ri] == dipBeam)
        {
            bscale = dipScale;
        }
        const scalar Pr = ramp*pScale*bscale*rayPower[ri];
        if (Pstream::master()) incident += Pr;
        if (hit[ri] == labelMax)
        {
            if (Pstream::master()) missed += Pr;
            continue;
        }
        const labelList& sl = raySamp[ri];
        forAll(sl, k)
        {
            if (sl[k] == hit[ri])
            {
                const label c = rayCells[ri][k];
                Q[c] += matA[c]*Pr/V[c];
                break;
            }
        }
    }
    Qheat.correctBoundaryConditions();
    laserIncidentPower = returnReduce(incident, sumOp<scalar>());
    laserAbsorbedPower = gSum(Q*V);

    // column surface heights
    scalarField& zs = zSurface.primitiveFieldRef();
    forAll(colCells, ci)
    {
        scalar hsum = 0;
        const labelList& cl = colCells[ci];
        for (const label c : cl) hsum += max(min(alpha1[c], 1.0), 0.0)*V[c]/colArea[ci];
        for (const label c : cl) zs[c] = colZbot[ci] + hsum;
    }
    zSurface.correctBoundaryConditions();
}
