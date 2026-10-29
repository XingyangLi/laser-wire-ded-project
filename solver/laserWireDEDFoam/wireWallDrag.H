// Trailing wire wall drags a pinned contact line. See createContactLine.H.
// Runs after contactLine.H, which zeros Kcontact at the start of every call.
// Off, or no wireWall, leaves the momentum equation unchanged.
{
    if (wireDragEnabled)
    {
        const label patchi = mesh.boundaryMesh().findPatchID("wireWall");
        const bool havePin =
            patchi >= 0
         && isA<pinnedAlphaContactAngleFvPatchScalarField>
            (
                alpha1.boundaryField()[patchi]
            );
        const bool haveSlip =
            patchi >= 0
         && isA<partialSlipFvPatchVectorField>(U.boundaryField()[patchi]);

        if (havePin && haveSlip)
        {
            const pinnedAlphaContactAngleFvPatchScalarField& pinBC =
                refCast<const pinnedAlphaContactAngleFvPatchScalarField>
                (
                    alpha1.boundaryField()[patchi]
                );
            const scalar thetaA = pinBC.thetaA();
            const scalar thetaR = pinBC.thetaR();

            const fvPatch& wp = mesh.boundary()[patchi];
            const labelUList& faceCells = wp.faceCells();
            const vectorField nf(wp.nf());
            const vectorField& Cf = wp.Cf();
            const scalarField& dc = wp.deltaCoeffs();
            const labelListList& cCells = mesh.cellCells();
            const vectorField& C = mesh.C().primitiveField();

            const volVectorField gradAlpha(fvc::grad(alpha1));
            const scalarField& a = alpha1.primitiveField();
            const vectorField& gA = gradAlpha.primitiveField();
            const scalarField& V = mesh.V();
            const scalar radToDeg = 180.0/constant::mathematical::pi;

            scalarField vf(wp.size(), Zero);
            boolList onLine(wp.size(), false);
            scalarField thetaFace(wp.size(), Zero);
            labelList sinkCell(wp.size(), -1);
            scalar nPin = 0, nSlip = 0, nLine = 0, thSum = 0;
            scalar zPinLo = GREAT, zPinHi = -GREAT;
            // Highest trailing face that is still metal. The free-surface
            // contact sits in a short band under that height. Pinning every
            // interfacial face drags the whole wetted wall.
            scalar zWet = -GREAT;
            const scalar zBand = 2.0e-4;

            forAll(faceCells, fi)
            {
                const label owner = faceCells[fi];
                const scalar h = Foam::cbrt(max(V[owner], SMALL));
                const scalar delta = 1.0/max(dc[fi], SMALL);
                vf[fi] = delta/(delta + wireDragSlipFar);

                const bool sideWall = mag(nf[fi].z()) < 0.5;
                const bool trailing = sideWall && (Cf[fi].x() > 0);
                if (!trailing) continue;
                // Top of the liquid metal on the wall. The solid wire above
                // the pool is cold (liquid fraction 0) and is not the contact.
                if (a[owner] > 0.5 && liquidFraction[owner] > 0.5)
                {
                    zWet = max(zWet, Cf[fi].z());
                }

                label gCell = owner;
                scalar best = mag(gA[owner])*h;
                for (const label n : cCells[owner])
                {
                    if (mag(C[n] - Cf[fi]) > 2.5*h) continue;
                    const scalar hn = Foam::cbrt(max(V[n], SMALL));
                    const scalar score = mag(gA[n])*hn;
                    if (score > best)
                    {
                        best = score;
                        gCell = n;
                    }
                }
                if
                (
                    best <= wireDragGradMin
                 || a[gCell] <= 0.10
                 || a[gCell] >= 0.90
                ) continue;

                const scalar magG = mag(gA[gCell]);
                const scalar c = max
                (
                    min((gA[gCell]/magG) & nf[fi], scalar(1)),
                    scalar(-1)
                );
                onLine[fi] = true;
                thetaFace[fi] = ::acos(c)*radToDeg;
                const scalar hOwn = Foam::cbrt(max(V[owner], SMALL));
                const bool ownerOnLine =
                    mag(gA[owner])*hOwn > wireDragGradMin
                 && a[owner] > 0.10
                 && a[owner] < 0.90;
                sinkCell[fi] = ownerOnLine ? owner : gCell;
            }

            reduce(zWet, maxOp<scalar>());

            forAll(faceCells, fi)
            {
                if (!onLine[fi]) continue;
                if (Cf[fi].z() < zWet - zBand || Cf[fi].z() > zWet + 0.05e-3)
                {
                    continue;
                }

                const scalar th = thetaFace[fi];
                thSum += th;
                nLine += 1;

                if (th >= thetaR && th <= thetaA)
                {
                    // No-slip at the feed velocity, and a sink that locks the
                    // interface cell to that velocity. Viscous diffusion from
                    // the wall does not cross one cell in a capillary step,
                    // so the sink is what carries the line.
                    vf[fi] = 1;
                    Kcontact[sinkCell[fi]] = wireDragKpin;
                    Ucontact[sinkCell[fi]] = wireFeedVelocity;
                    nPin += 1;
                    zPinLo = min(zPinLo, Cf[fi].z());
                    zPinHi = max(zPinHi, Cf[fi].z());
                }
                else
                {
                    // Outside the window the angle BC supplies a Young force.
                    // A short slip length lets that force slide the line.
                    const scalar delta = 1.0/max(dc[fi], SMALL);
                    vf[fi] = delta/(delta + wireDragSlipNear);
                    nSlip += 1;
                }
            }

            partialSlipFvPatchVectorField& psp =
                refCast<partialSlipFvPatchVectorField>
                (
                    U.boundaryFieldRef()[patchi]
                );
            psp.valueFraction() = vf;
            psp.evaluate();

            reduce(nPin, sumOp<scalar>());
            reduce(nSlip, sumOp<scalar>());
            reduce(nLine, sumOp<scalar>());
            reduce(thSum, sumOp<scalar>());
            reduce(zPinLo, minOp<scalar>());
            reduce(zPinHi, maxOp<scalar>());

            if
            (
                runTime.timeIndex() <= 2
             || runTime.timeIndex() % max(contactInterval, 1) == 0
            )
            {
                Info<< "WireDrag: pin " << nPin
                    << " slip " << nSlip
                    << " theta " << (nLine > SMALL ? thSum/nLine : 0)
                    << " deg  zWet " << zWet*1e3
                    << " mm  zPin "
                    << (nPin > SMALL ? zPinLo*1e3 : -1)
                    << " " << (nPin > SMALL ? zPinHi*1e3 : -1)
                    << " mm  feed " << wireFeedVelocity.z()
                    << nl;
            }
        }
        else if (runTime.timeIndex() <= 1)
        {
            Info<< "WireDrag: enabled but wireWall is "
                << (patchi < 0 ? "missing" : "not a pinned partial-slip wall")
                << nl;
        }
    }
}

// ************************************************************************* //
