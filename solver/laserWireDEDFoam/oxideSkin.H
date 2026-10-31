// Oxide-skin membrane. See createOxideSkin.H. Off -> mu = 0, K = 0.
{
    muOxide == dimensionedScalar(muOxide.dimensions(), Zero);
    Koxide == dimensionedScalar(Koxide.dimensions(), Zero);
    Ukeep == U;
    Fskin == dimensionedVector(Fskin.dimensions(), Zero);

    if (oxideSkinEnabled && oxideSkinDynamic && oxideSkinStrength > SMALL)
    {
        #include "oxideCoverage.H"
        // Carry the stretch with the surface, then let the exposed skin
        // accumulate strain from the surface divergence of velocity.
        {
            const scalar dtEs = runTime.deltaTValue();
            skinStrain.correctBoundaryConditions();
            const volScalarField divEs(fvc::div(phi, skinStrain));
            scalarField& es = skinStrain.primitiveFieldRef();
            const scalarField& dEs = divEs.primitiveField();
            forAll(es, celli)
            {
                es[celli] = max(min(es[celli] - dtEs*dEs[celli], scalar(4)), scalar(-1));
            }
        }
        // Imposed numerical stiffness. Alloy sigma is already in stForcef.
        // Coverage starts at 0, so the first step adds nothing.
        if (oxideSkinSigma > 0)
        {
            const volScalarField sigSkin
            (
                dimensionedScalar(sigmaT.dimensions(), oxideSkinSigma)
               *oxideCoverage
            );
            surfaceScalarField skinKf
            (
                fvc::interpolate(sigSkin*(-fvc::div(mixture.nHatf())))
            );
            if (stLiquidOnly)
            {
                skinKf *= stWeightf;
            }
            surfaceScalarField skinForce(skinKf*fvc::snGrad(alpha1));
            if (stDensityScaled)
            {
                skinForce *= fvc::interpolate((2.0*rho)/(rho1 + rho2));
            }
            stForcef += skinForce;
            const scalar fMax = rho1.value()*2.0/1.0e-6;
            const dimensionedScalar fMaxD("fCap", stForcef.dimensions(), fMax);
            const dimensionedScalar fMinD("fCap", stForcef.dimensions(), -fMax);
            stForcef = min(max(stForcef, fMinD), fMaxD);
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
        const volTensorField gradU(fvc::grad(U));
        const tensorField& gradUc = gradU.primitiveField();
        const scalarField& rhoC = rho.primitiveField();
        scalarField& es = skinStrain.primitiveFieldRef();
        scalarField& oxW = oxideCoverage.primitiveFieldRef();
        vectorField& Fs = Fskin.primitiveFieldRef();
        const scalar dtEs = runTime.deltaTValue();

        scalar nSkin = 0, nMu = 0, gapMin = GREAT, unMax = 0, wMouth = GREAT;
        scalar oxMax = 0, oxSum = 0, nOx = 0, nRup = 0, eMax = 0, aMax = 0;

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

            // Surface strain. Capped rate so a noisy divergence cannot
            // rupture the skin in one step.
            const scalar divS = max
            (
                min
                (
                    tr(gradUc[celli]) - (nHat & (gradUc[celli] & nHat)),
                    scalar(40)
                ),
                scalar(-40)
            );
            es[celli] = max(min(es[celli] + dtEs*divS, scalar(4)), scalar(-1));
            eMax = max(eMax, es[celli]);
            if (es[celli] > oxideSkinEpsRup)
            {
                // Rupture: this patch of skin is gone. The surface here is
                // generated again, with no membrane force.
                oxW[celli] = 0;
                es[celli] = 0;
                nRup += 1;
                continue;
            }

            // Elastic membrane on the trailing face. The force points away
            // from the wire and fades once the gap reaches the bending
            // length, so a stretched skin is not pushed back onto the wire
            // and does not inflate a wide cavity. Acceleration is capped.
            // The old shell stopped at 1.55 mm. The bead top sits above
            // that, so the membrane uses the whole trailing face.
            const bool trailFace =
                (rad & trail) > 0 && s > 0.4e-3 && s < 2.0e-3;
            if (!trailFace || r <= wireRadius) continue;
            const scalar gap = r - wireRadius;
            if (gap >= oxideSkinBend) continue;
            const scalar close = (oxideSkinBend - gap)/oxideSkinBend;
            const scalar tensionW =
                min(max(es[celli], scalar(0)), oxideSkinEpsRup)
               /oxideSkinEpsRup;
            const scalar eFrac = min(oxideSkinE/2.5, scalar(2));
            const scalar aEl =
                oxideSkinACap
               *(ox[celli]/max(oxideSkinStrength, scalar(0.05)))
               *close
               *(0.35 + 0.65*tensionW)
               *eFrac;
            const vector nOut = rad/max(r, SMALL);
            Fs[celli] = rhoC[celli]*aEl*nOut;
            aMax = max(aMax, aEl);
        }

        // The neck diagnostic showed the membrane acceleration was zero on
        // 581 of 582 centre-plane cells against the wire: they are alpha~1
        // and carry no coverage, and one neighbour hop does not reach the
        // free surface. Once the trailing surface has a skin, that skin
        // pushes the metal in the first bending-length off the wall.
        scalar oxSurf = 0;
        forAll(a, celli)
        {
            if (oxW[celli] < 0.05) continue;
            const vector d = Cc[celli] - wireOrigin;
            const scalar sAx = d & wireUp;
            const vector rad = d - sAx*wireUp;
            if ((rad & trail) <= 0) continue;
            oxSurf = max(oxSurf, oxW[celli]);
        }
        reduce(oxSurf, maxOp<scalar>());
        // slitEntry opens the neck by letting gas in at the dragged line.
        // The body force on wet wall cells is off in that mode.
        if (oxSurf > 0.3 && !slitEntryEnabled)
        {
            forAll(a, celli)
            {
                if (a[celli] < 0.35) continue;
                const vector d = Cc[celli] - wireOrigin;
                const scalar sAx = d & wireUp;
                const vector rad = d - sAx*wireUp;
                if ((rad & trail) <= 0) continue;
                if (sAx < 1.15e-3 || sAx > 1.80e-3) continue;
                const scalar r = mag(rad);
                if (r <= wireRadius) continue;
                const scalar gap = r - wireRadius;
                if (gap <= 0 || gap >= oxideSkinBend) continue;
                const scalar close = (oxideSkinBend - gap)/oxideSkinBend;
                const scalar tensionW =
                    min(max(es[celli], scalar(0)), oxideSkinEpsRup)
                   /oxideSkinEpsRup;
                const scalar eFrac = min(oxideSkinE/2.5, scalar(2));
                const scalar aEl =
                    oxideSkinACap
                   *(oxSurf/max(oxideSkinStrength, scalar(0.05)))
                   *close
                   *(0.35 + 0.65*tensionW)
                   *eFrac;
                const vector nOut = rad/max(r, SMALL);
                Fs[celli] = rhoC[celli]*aEl*nOut;
                aMax = max(aMax, aEl);
                nSkin += 1;
            }
        }

        // Neck diagnostic: cells on the centre plane, within 0.08 mm of the
        // trailing wire face, z = 1.20-1.80 mm. Reports the acceleration the
        // membrane actually applied there.
        {
            scalar nNeck = 0, aSum = 0, aLo = 1, aHi = 0, oxN = 0;
            scalar accMax = 0, kN = 0, urSum = 0, nPush = 0;
            const scalarField& kC = Kcontact.primitiveField();
            forAll(a, celli)
            {
                const vector d = Cc[celli] - wireOrigin;
                const scalar sAx = d & wireUp;
                const vector rad = d - sAx*wireUp;
                if ((rad & trail) <= 0) continue;
                if (mag(Cc[celli].y()) > 1.2e-4) continue;
                if (sAx < 1.20e-3 || sAx > 1.80e-3) continue;
                const scalar r = mag(rad);
                const scalar gap = r - wireRadius;
                if (gap <= 0 || gap > 8.0e-5) continue;
                nNeck += 1;
                aSum += a[celli];
                aLo = min(aLo, a[celli]);
                aHi = max(aHi, a[celli]);
                oxN += oxW[celli];
                const scalar acc = mag(Fs[celli])/max(rhoC[celli], SMALL);
                accMax = max(accMax, acc);
                if (acc > 1) nPush += 1;
                kN = max(kN, kC[celli]);
                urSum += Uc[celli] & (rad/max(r, SMALL));
            }
            reduce(nNeck, sumOp<scalar>());
            reduce(aSum, sumOp<scalar>());
            reduce(aLo, minOp<scalar>());
            reduce(aHi, maxOp<scalar>());
            reduce(oxN, sumOp<scalar>());
            reduce(accMax, maxOp<scalar>());
            reduce(kN, maxOp<scalar>());
            reduce(urSum, sumOp<scalar>());
            reduce(nPush, sumOp<scalar>());
            if
            (
                runTime.timeIndex() <= 3
             || runTime.timeIndex() % max(oxideSkinInterval, 1) == 0
            )
            {
                Info<< "NeckDiag: n " << nNeck
                    << " alpha " << (nNeck > 0 ? aSum/nNeck : 0)
                    << " [" << aLo << "," << aHi << "]"
                    << " ox " << (nNeck > 0 ? oxN/nNeck : 0)
                    << " aElMax " << accMax
                    << " nPush " << nPush
                    << " Kmax " << kN
                    << " uRad " << (nNeck > 0 ? urSum/nNeck : 0)
                    << nl;
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
            reduce(oxMax, maxOp<scalar>());
            reduce(oxSum, sumOp<scalar>());
            reduce(nOx, sumOp<scalar>());
            reduce(nRup, sumOp<scalar>());
            reduce(eMax, maxOp<scalar>());
            reduce(aMax, maxOp<scalar>());
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
                << " eMax " << eMax
                << " nRup " << nRup
                << " aEl " << aMax
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
