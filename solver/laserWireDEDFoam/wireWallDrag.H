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
            scalar nPin = 0, nSlip = 0, nLine = 0, thSum = 0;
            scalar zPinLo = GREAT, zPinHi = -GREAT;
            scalar zLineLo = GREAT, zLineHi = -GREAT;

            forAll(faceCells, fi)
            {
                const label owner = faceCells[fi];
                const scalar h = Foam::cbrt(max(V[owner], SMALL));
                const scalar delta = 1.0/max(dc[fi], SMALL);
                const bool sideWall = mag(nf[fi].z()) < 0.5;
                const bool trailing = sideWall && (Cf[fi].x() > 0);

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

                const bool interface =
                    best > wireDragGradMin
                 && a[gCell] > 0.02
                 && a[gCell] < 0.98;

                if (!(trailing && interface))
                {
                    vf[fi] = delta/(delta + wireDragSlipFar);
                    continue;
                }

                const scalar magG = mag(gA[gCell]);
                const scalar c = max
                (
                    min((gA[gCell]/magG) & nf[fi], scalar(1)),
                    scalar(-1)
                );
                const scalar th = ::acos(c)*radToDeg;
                thSum += th;
                nLine += 1;
                zLineLo = min(zLineLo, Cf[fi].z());
                zLineHi = max(zLineHi, Cf[fi].z());

                if (th >= thetaR && th <= thetaA)
                {
                    // No-slip at the feed velocity, and a sink that locks the
                    // near-wall interface cell to that velocity. Viscous
                    // diffusion from the wall does not cross one cell in a
                    // capillary step, so the sink is what carries the line.
                    vf[fi] = 1;
                    const scalar hOwn = Foam::cbrt(max(V[owner], SMALL));
                    const bool ownerOnLine =
                        mag(gA[owner])*hOwn > wireDragGradMin
                     && a[owner] > 0.02
                     && a[owner] < 0.98;
                    const label sink = ownerOnLine ? owner : gCell;
                    Kcontact[sink] = wireDragKpin;
                    Ucontact[sink] = wireFeedVelocity;
                    nPin += 1;
                    zPinLo = min(zPinLo, Cf[fi].z());
                    zPinHi = max(zPinHi, Cf[fi].z());
                }
                else
                {
                    // Outside the window the angle BC supplies a Young force.
                    // A short slip length lets that force slide the line.
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
            reduce(zLineLo, minOp<scalar>());
            reduce(zLineHi, maxOp<scalar>());

            if
            (
                runTime.timeIndex() <= 2
             || runTime.timeIndex() % max(contactInterval, 1) == 0
            )
            {
                Info<< "WireDrag: pin " << nPin
                    << " slip " << nSlip
                    << " theta " << (nLine > SMALL ? thSum/nLine : 0)
                    << " deg  zPin "
                    << (nPin > SMALL ? zPinLo*1e3 : -1)
                    << " " << (nPin > SMALL ? zPinHi*1e3 : -1)
                    << " mm  zLine "
                    << (nLine > SMALL ? zLineLo*1e3 : -1)
                    << " " << (nLine > SMALL ? zLineHi*1e3 : -1)
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
