// ---------------------------------------------------------------------------
// Place each beam focus on the free surface at its aim, then ask the caller
// to rebuild the rays when that height has moved.
//
// The aim (x, y) is the dictionary focus, plus the weave shift. z is the
// height where a downward march through that column first reaches
// alpha >= alphaHit: the substrate top on a bare plate, the bead top once
// metal has piled up. A column with no metal keeps the current focus z.
// The nearest column has to lie within 1 mm; an aim off the mesh keeps the
// dictionary height. Rays are rebuilt after a move of about a quarter of
// that column (and at least laserTrackDz), so a settled surface does not
// retrace every step.
// ---------------------------------------------------------------------------
auto trackLaserFoci = [&]() -> bool
{
    if (!trackLaserSurface || beamFocus.empty()) return false;

    const dictionary& ld = meltProperties.subDict("laser");
    const bool symY = ld.getOrDefault<bool>("symmetryY", false);
    const scalar aHit = ld.getOrDefault<scalar>("alphaHit", 0.5);
    if (laserTrackDz <= SMALL)
    {
        const scalar dxMin =
            1.0/max(gMax(mesh.deltaCoeffs().primitiveField()), SMALL);
        laserTrackDz = 0.25*dxMin;
    }

    const vectorField& CC = mesh.C().primitiveField();
    const scalarField& V = mesh.V();
    const scalarField& a = alpha1.primitiveField();

    // Geometric free-surface height of every local column. -GREAT: no metal.
    scalarField colZ(colCells.size(), -GREAT);
    forAll(colCells, ci)
    {
        const labelList& cl = colCells[ci];
        for (const label c : cl)   // top -> bottom
        {
            if (a[c] < aHit) continue;
            const scalar dz = V[c]/max(colArea[ci], VSMALL);
            const scalar zTop = CC[c].z() + 0.5*dz;
            const scalar aCl = max(min(a[c], scalar(1)), scalar(0));
            colZ[ci] = zTop - (scalar(1) - aCl)*dz;
            break;
        }
    }

    bool moved = false;
    forAll(beamFocus, bi)
    {
        const scalar ax = beamFocus[bi].x();
        scalar ay = beamFocus[bi].y() + weaveY;
        if (symY) ay = mag(ay);

        scalar bestD = GREAT;
        label bestI = -1;
        forAll(colZ, ci)
        {
            const scalar d2 = sqr(colX[ci] - ax) + sqr(colY[ci] - ay);
            if (d2 < bestD)
            {
                bestD = d2;
                bestI = ci;
            }
        }
        const scalar zNear = (bestI >= 0 ? colZ[bestI] : -GREAT);
        const scalar aNear = (bestI >= 0 ? colArea[bestI] : GREAT);

        const scalar gD = returnReduce(bestD, minOp<scalar>());
        // Only the rank that owns the nearest column contributes its height.
        const bool own = bestD <= gD + SMALL;
        const scalar zSend = (own && zNear > -0.5*GREAT) ? zNear : GREAT;
        const scalar aSend = own ? aNear : GREAT;
        const scalar gZ = returnReduce(zSend, minOp<scalar>());
        const scalar gA = returnReduce(aSend, minOp<scalar>());

        if (gD > sqr(scalar(1e-3)) || gZ > 0.5*GREAT)
        {
            continue;
        }
        scalar moveTol = laserTrackDz;
        if (gA > SMALL && gA < 0.5*GREAT)
        {
            moveTol = max(laserTrackDz, 0.25*Foam::sqrt(gA));
        }
        if (mag(gZ - beamFocus[bi].z()) > moveTol)
        {
            if (Pstream::master())
            {
                const word bname =
                    (bi < beamNames.size() ? beamNames[bi] : word("beam"));
                Info<< "Laser trackSurface: " << bname
                    << " focus z " << beamFocus[bi].z()
                    << " -> " << gZ << " m" << endl;
            }
            beamFocus[bi].z() = gZ;
            moved = true;
        }
    }
    return moved;
};
