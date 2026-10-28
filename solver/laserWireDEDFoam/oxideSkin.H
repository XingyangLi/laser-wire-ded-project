// Oxide-skin membrane. See createOxideSkin.H. Off -> mu = 0, K = 0.
{
    muOxide == dimensionedScalar(muOxide.dimensions(), Zero);
    Koxide == dimensionedScalar(Koxide.dimensions(), Zero);
    Ukeep == U;

    if (oxideSkinEnabled && oxideSkinDynamic && oxideSkinStrength > SMALL)
    {
        // oxideSurface.H already advanced coverage this step.
        if (!oxideSurface)
        {
            #include "oxideCoverage.H"
        }
        const volVectorField gradAlpha(fvc::grad(alpha1));
        scalarField& muI = muOxide.primitiveFieldRef();
        scalarField& KI = Koxide.primitiveFieldRef();
        vectorField& Uk = Ukeep.primitiveFieldRef();
        const vectorField& Uc = U.primitiveField();
        const vectorField& Cc = mesh.C().primitiveField();
        const scalarField& Vp = mesh.V();
        const scalarField& a = alpha1.primitiveField();
        const scalarField& ox = oxideCoverage.primitiveField();
        const vectorField& gA = gradAlpha.primitiveField();
        const vector trail(1, 0, 0);

        scalar nSkin = 0, nMu = 0, gapMin = GREAT, unMax = 0, wMouth = GREAT;
        scalar oxMax = 0, oxSum = 0, nOx = 0;

        forAll(a, celli)
        {
            const vector d = Cc[celli] - wireOrigin;
            const scalar s = d & wireUp;
            const vector rad = d - s*wireUp;
            const scalar r = mag(rad);
            const scalar h = Foam::cbrt(max(Vp[celli], SMALL));
            const bool onTrail = (rad & trail) > 0 && s >= oxideSkinZ0 && s <= oxideSkinZ1;
            const scalar magG = mag(gA[celli]);
            const bool exposed =
                magG*h > 0.25 && a[celli] > 0.02 && a[celli] < 0.98;

            if
            (
                onTrail
             && a[celli] > 0.5
             && r > wireRadius
             && r < wireRadius + 0.40e-3
            )
            {
                gapMin = min(gapMin, r - wireRadius);
                if (s > 1.10e-3 && s < 1.30e-3 && mag(Cc[celli].y()) < 4.0e-5)
                {
                    wMouth = min(wMouth, r - wireRadius);
                }
            }

            if (!exposed || ox[celli] < 1e-3) continue;
            oxMax = max(oxMax, ox[celli]);
            oxSum += ox[celli];
            nOx += 1;
            const vector nHat = gA[celli]/(magG + VSMALL);
            Uk[celli] = Uc[celli] - (Uc[celli] & nHat)*nHat;
            KI[celli] = ox[celli]*oxideSkinK0;
            muI[celli] = ox[celli]*oxideSkinMu0;
            nSkin += 1;
            nMu += 1;
            unMax = max(unMax, mag(Uc[celli] & nHat));
        }

        if
        (
            runTime.timeIndex() != oxideSkinLogIndex
         && runTime.timeIndex() % max(oxideSkinInterval, 1) == 0
        )
        {
            oxideSkinLogIndex = runTime.timeIndex();
            reduce(nSkin, sumOp<scalar>());
            reduce(nMu, sumOp<scalar>());
            reduce(gapMin, minOp<scalar>());
            reduce(unMax, maxOp<scalar>());
            reduce(wMouth, minOp<scalar>());
            reduce(oxMax, maxOp<scalar>());
            reduce(oxSum, sumOp<scalar>());
            reduce(nOx, sumOp<scalar>());
            const word mouth =
                (wMouth > 0.20e-3) ? word("bare")
              : (wMouth < 0.020e-3 ? word("closed") : word("open"));
            Info<< "OxideSkin: dynamic cells " << nSkin
                << " oxMax " << oxMax
                << " oxMean " << (nOx > 0 ? oxSum/nOx : scalar(0))
                << " sat " << oxideSkinStrength
                << " gapMin "
                << (gapMin > 0.5 ? scalar(-1) : gapMin*1e3) << " mm"
                << " wMouth "
                << (wMouth > 0.5 ? scalar(-1) : wMouth*1e3) << " mm " << mouth
                << " Un " << unMax
                << nl;
        }
    }
    else if (oxideSkinEnabled && oxideSkinStrength > SMALL)
    {
        const volVectorField gradAlpha(fvc::grad(alpha1));
        scalarField& muI = muOxide.primitiveFieldRef();
        scalarField& KI = Koxide.primitiveFieldRef();
        vectorField& Uk = Ukeep.primitiveFieldRef();
        const vectorField& Uc = U.primitiveField();
        const vectorField& Cc = mesh.C().primitiveField();
        const scalarField& Vp = mesh.V();
        const scalarField& a = alpha1.primitiveField();
        const vectorField& gA = gradAlpha.primitiveField();
        const vector trail(1, 0, 0);
        const scalar muUse = oxideSkinStrength*oxideSkinMu0;
        const scalar Kuse = oxideSkinStrength*oxideSkinK0;

        // gapMin / wMouth watch the nearest metal outside the wire, whether
        // or not that cell is inside the damped shell.
        scalar nSkin = 0, nMu = 0, gapMin = GREAT, unMax = 0, wMouth = GREAT;

        forAll(a, celli)
        {
            const vector d = Cc[celli] - wireOrigin;
            const scalar s = d & wireUp;
            const vector rad = d - s*wireUp;
            const scalar r = mag(rad);
            const scalar h = Foam::cbrt(max(Vp[celli], SMALL));
            const bool onTrail = (rad & trail) > 0 && s >= oxideSkinZ0 && s <= oxideSkinZ1;

            if
            (
                onTrail
             && a[celli] > 0.5
             && r > wireRadius
             && r < wireRadius + 0.40e-3
            )
            {
                gapMin = min(gapMin, r - wireRadius);
                if (s > 1.10e-3 && s < 1.30e-3 && mag(Cc[celli].y()) < 4.0e-5)
                {
                    wMouth = min(wMouth, r - wireRadius);
                }
            }

            if (!onTrail) continue;
            if (r < wireRadius - 0.5*h || r > wireRadius + oxideSkinGap) continue;

            // Every cell in the shell: both metal faces and the gas between
            // them. A scalar Sp cannot damp only the radial component without
            // also holding the tangential velocity at Ukeep, so with this K
            // the shell stays on the tangential part of the velocity it
            // entered with. The painted film enters at rest once the radial
            // scan speed is removed.
            const scalar magG = mag(gA[celli]);
            const bool iface = (magG*h > 0.25);

            const vector n = rad/(r + VSMALL);
            Uk[celli] = Uc[celli] - (Uc[celli] & n)*n;
            KI[celli] = Kuse;
            nSkin += 1;
            unMax = max(unMax, mag(Uc[celli] & n));
            if (iface)
            {
                muI[celli] = muUse;
                nMu += 1;
            }
        }

        if
        (
            runTime.timeIndex() != oxideSkinLogIndex
         && runTime.timeIndex() % max(oxideSkinInterval, 1) == 0
        )
        {
            oxideSkinLogIndex = runTime.timeIndex();
            reduce(nSkin, sumOp<scalar>());
            reduce(nMu, sumOp<scalar>());
            reduce(gapMin, minOp<scalar>());
            reduce(unMax, maxOp<scalar>());
            reduce(wMouth, minOp<scalar>());
            const word mouth =
                (wMouth > 0.20e-3) ? word("bare")
              : (wMouth < 0.020e-3 ? word("closed") : word("open"));
            Info<< "OxideSkin: cells " << nSkin
                << " muCells " << nMu
                << " strength " << oxideSkinStrength
                << " gapMin "
                << (gapMin > 0.5 ? scalar(-1) : gapMin*1e3) << " mm"
                << " wMouth "
                << (wMouth > 0.5 ? scalar(-1) : wMouth*1e3) << " mm " << mouth
                << " Un " << unMax
                << nl;
        }
    }
}
