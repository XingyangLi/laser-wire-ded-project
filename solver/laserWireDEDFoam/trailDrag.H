// Stamp the trailing-face shell. See createTrailDrag.H.
// trailDragDoLog is set by the caller.
if (trailDragEnabled)
{
    const scalar tNow = runTime.value();
    scalar feedFac = 1;
    if (tNow < wireFeedStart) feedFac = 0;
    else if (wireFeedRamp > SMALL)
    {
        feedFac = min((tNow - wireFeedStart)/wireFeedRamp, scalar(1));
    }
    const vector Ufeed = feedFac*wireFeedVelocity;

    const vectorField& Ctd = mesh.C().primitiveField();
    const scalarField& Vtd = mesh.V();
    vector trail(1, 0, 0);
    trail -= (trail & wireUp)*wireUp;
    const scalar mtTrail = mag(trail);
    if (mtTrail > SMALL) trail /= mtTrail;
    const scalar cosCut = Foam::cos(trailDragSector);

    if (!trailDragReady)
    {
        scalar zMax = -GREAT;
        forAll(Ctd, celli)
        {
            const scalar h = Foam::cbrt(max(Vtd[celli], SMALL));
            const vector d = Ctd[celli] - wireOrigin;
            const scalar sAx = d & wireUp;
            const vector rad = d - sAx*wireUp;
            const scalar r = mag(rad);
            if (r < wireRadius - 0.5*h) continue;
            if (r > wireRadius + trailDragRadial*h) continue;
            if (r > SMALL && (rad & trail) < cosCut*r) continue;
            // Liquid metal only. The solid wire continues above the pool,
            // and taking its tip puts the shell in the gas.
            if (alpha1[celli] < 0.5) continue;
            if (liquidFraction[celli] < 0.5) continue;
            if (Ctd[celli].z() < 0.05e-3) continue;
            zMax = max(zMax, Ctd[celli].z());
        }
        reduce(zMax, maxOp<scalar>());
        if (zMax < -GREAT/2)
        {
            FatalErrorInFunction
                << "TrailDrag: no wetted trailing-face cell" << nl
                << exit(FatalError);
        }
        trailDragZ0 = zMax;
        trailDragT0 = tNow;
        trailDragReady = true;
        Info<< "TrailDrag: wetted top z0 = " << trailDragZ0
            << " m at t = " << tNow << " s" << nl;
    }

    const scalar fed = max(tNow - max(trailDragT0, wireFeedStart), scalar(0));
    const scalar zTop =
        trailDragZ0 + (wireFeedVelocity & vector(0, 0, 1))*fed;

    label nHold = 0;
    label nDry = 0;
    scalarField& aHold = alpha1.primitiveFieldRef();
    vectorField& uHold = U.primitiveFieldRef();
    // Do not write phi. Zeroing faces made the next alpha equation
    // unbounded (alpha above 2). The dry cells are reset after each
    // alpha solve instead.
    forAll(Ctd, celli)
    {
        const scalar h = Foam::cbrt(max(Vtd[celli], SMALL));
        const vector d = Ctd[celli] - wireOrigin;
        const scalar sAx = d & wireUp;
        const vector rad = d - sAx*wireUp;
        const scalar r = mag(rad);
        if (r < wireRadius - 0.35*h) continue;
        if (r > wireRadius + trailDragRadial*h) continue;
        if (r > SMALL && (rad & trail) < cosCut*r) continue;
        const scalar z = Ctd[celli].z();
        if (z < 0.05e-3) continue;
        // Pinned wet line: a few cells under the moving top.
        if (z <= zTop && z >= zTop - trailDragAxial*h)
        {
            aHold[celli] = 1;
            uHold[celli] = Ufeed;
            ++nHold;
            continue;
        }
        // Face the line has swept. Held dry so the line cannot climb
        // back. The pool outside this shell is not written.
        if (z > zTop && z <= trailDragZ0 + 0.25*h)
        {
            aHold[celli] = 0;
            ++nDry;
        }
    }
    alpha1.correctBoundaryConditions();
    U.correctBoundaryConditions();
    reduce(nHold, sumOp<label>());
    reduce(nDry, sumOp<label>());

    if (trailDragDoLog && pimple.finalIter())
    {
        Info<< "TrailDrag: zTop " << zTop << " m  wet " << nHold
            << "  dry " << nDry
            << "  Ufeed " << Ufeed << nl;
    }
}
