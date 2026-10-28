// Grow trailing-wire oxide coverage once per time step, then set the
// trailing-wall slip fraction to that coverage. See createOxideAngle.H.
// Off leaves coverage at 0 and does not touch the wall.
{
    if (oxideAngleEnabled && pimple.firstIter())
    {
        const scalar sCap = oxygenDependent
            ? min(max(chamberOxygenPpm/oxideAnglePpmRef, scalar(0)), scalar(1))
            : scalar(1);
        const scalar relax = min(runTime.deltaTValue()/oxideAngleTau, scalar(1));

        const vectorField& C = mesh.C().primitiveField();
        const scalarField& Vc = mesh.V();
        const scalarField& alpha = alpha1.primitiveField();
        scalarField& cov = oxideCoverage.primitiveFieldRef();

        scalar cMax = 0, nWall = 0, nExposed = 0, nFull = 0;
        forAll(cov, celli)
        {
            const vector d = C[celli] - wireOrigin;
            const scalar sAx = d & wireUp;
            const vector rad = d - sAx*wireUp;
            const scalar h = Foam::cbrt(max(Vc[celli], SMALL));
            const scalar r = mag(rad);
            const bool inShell =
                rad.x() > 0
             && r > wireRadius
             && r <= wireRadius + oxideAngleNCells*h
             && C[celli].z() > oxideAngleZMin;
            // The first cell is the wire surface, oxide under the melt
            // included. Farther cells oxidize only while they are gas or
            // on the interface. Buried metal relaxes.
            const bool onWire = inShell && r <= wireRadius + h;
            const scalar target =
                (inShell && (onWire || alpha[celli] < 0.9)) ? sCap : scalar(0);

            cov[celli] += relax*(target - cov[celli]);
            cov[celli] = min(max(cov[celli], scalar(0)), scalar(1));

            cMax = max(cMax, cov[celli]);
            if (target > 0.5*sCap) nExposed += 1;
            // 0.5*sCap so a 50 ppm run, whose coverage cannot exceed 1/6,
            // still counts wall cells that have reached the cap.
            if (onWire && cov[celli] > 0.5*max(sCap, SMALL)) nWall += 1;
            if (sCap > SMALL && cov[celli] > 0.9*sCap) nFull += 1;
        }
        oxideCoverage.correctBoundaryConditions();

        const label patchi = mesh.boundaryMesh().findPatchID("wireWall");
        if
        (
            patchi >= 0
         && isA<partialSlipFvPatchVectorField>(U.boundaryField()[patchi])
        )
        {
            const fvPatch& wp = mesh.boundary()[patchi];
            const labelUList& faceCells = wp.faceCells();
            const vectorField nf(wp.nf());
            const vectorField& Cf = wp.Cf();
            scalarField vf(wp.size(), Zero);
            forAll(faceCells, fi)
            {
                const bool sideWall = mag(nf[fi].z()) < 0.5;
                if (!(sideWall && Cf[fi].x() > 0)) continue;
                vf[fi] = cov[faceCells[fi]];
            }
            partialSlipFvPatchVectorField& psp =
                refCast<partialSlipFvPatchVectorField>
                (
                    U.boundaryFieldRef()[patchi]
                );
            psp.valueFraction() = vf;
            psp.evaluate();
        }

        reduce(cMax, maxOp<scalar>());
        reduce(nWall, sumOp<scalar>());
        reduce(nExposed, sumOp<scalar>());
        reduce(nFull, sumOp<scalar>());
        if
        (
            runTime.timeIndex() <= 2
         || runTime.timeIndex() % max(contactInterval, 1) == 0
        )
        {
            Info<< "OxideAngle: sCap " << sCap
                << " cMax " << cMax
                << " nExposed " << nExposed
                << " nWall " << nWall
                << " nFull " << nFull << nl;
        }
    }
}

// ************************************************************************* //
