#include <tuple>
// Trailing-face gas cavity. See createGasCavity.H. Off -> no force, no source.
{
    pGasCavity == dimensionedScalar(pGasCavity.dimensions(), Zero);
    gasVolumeSource == dimensionedScalar(gasVolumeSource.dimensions(), Zero);

    if (gasCavityEnabled && gasCavityStrength > SMALL)
    {
        const scalar pUse = gasCavityStrength*gasCavityP0;
        const scalar qUse =
            gasCavityStrength*gasCavityQ0
           *mag(wireFeedVelocity)/gasCavityFeedRef;
        const vector trail(1, 0, 0);

        auto onWire = [&](const label celli, const vectorField& Cc, const scalarField& Vp)
        {
            const vector d = Cc[celli] - wireOrigin;
            const scalar s = d & wireUp;
            const vector rad = d - s*wireUp;
            const scalar r = mag(rad);
            const scalar h = Foam::cbrt(max(Vp[celli], SMALL));
            const bool onTrail =
                (rad & trail) > 0 && s >= gasCavityZ0 && s <= gasCavityZ1;
            return std::tuple<bool, scalar, scalar, scalar, vector>
                (onTrail, s, r, h, rad);
        };

        const vectorField& Cc = mesh.C().primitiveField();
        const scalarField& Vp = mesh.V();
        scalarField& src = gasVolumeSource.primitiveFieldRef();
        scalarField& pg = pGasCavity.primitiveFieldRef();

        // Contact height: the highest trailing interface cell on the wire.
        // The gas is fed there, not along a prescribed depth.
        scalar zContact = -GREAT;
        {
            const volVectorField gradA0(fvc::grad(alpha1));
            const vectorField& g0 = gradA0.primitiveField();
            const scalarField& a0 = alpha1.primitiveField();
            forAll(a0, celli)
            {
                const auto [onTrail, s, r, h, rad] = onWire(celli, Cc, Vp);
                if (!onTrail) continue;
                // Only a cavity: gas toward the wire. The bare wire above the
                // bead has gas on the outside and must not set the feed height.
                if (r < wireRadius || r > wireRadius + 2.0*h) continue;
                const vector nRad = rad/(r + VSMALL);
                if ((nRad & g0[celli]) <= 0) continue;
                if (mag(g0[celli])*h > 0.25 && a0[celli] > 0.02 && a0[celli] < 0.98)
                {
                    zContact = max(zContact, s);
                }
            }
            reduce(zContact, maxOp<scalar>());
        }

        if (pimple.firstIter() && qUse > SMALL && zContact > -GREAT/2)
        {
            const volVectorField gradA0(fvc::grad(alpha1));
            const vectorField& g0 = gradA0.primitiveField();
            scalarField& a = alpha1.primitiveFieldRef();
            const scalar dt = runTime.deltaTValue();
            forAll(a, celli)
            {
                const auto [onTrail, s, r, h, rad] = onWire(celli, Cc, Vp);
                if (!onTrail) continue;
                if (r < wireRadius || r > wireRadius + 2.0*h) continue;
                if (s < zContact - gasCavityBand || s > zContact + 0.5*h) continue;
                if (!(mag(g0[celli])*h > 0.25 || a[celli] < 0.5)) continue;
                src[celli] = qUse/max(h, SMALL);
                a[celli] = min(max(a[celli] - dt*src[celli], scalar(0)), scalar(1));
            }
            alpha1.correctBoundaryConditions();
            alpha2 = scalar(1) - alpha1;
            rho == alpha1*rho1 + alpha2*rho2;
            mixture.correct();
        }

        const volVectorField gradAlpha(fvc::grad(alpha1));
        const vectorField& gA = gradAlpha.primitiveField();
        const scalarField& a = alpha1.primitiveField();
        scalar nP = 0, nSrc = 0, gapMin = GREAT, wMouth = GREAT, volRate = 0;

        forAll(a, celli)
        {
            const auto [onTrail, s, r, h, rad] = onWire(celli, Cc, Vp);
            if (!onTrail) continue;

            if
            (
                a[celli] > 0.5
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

            const bool iface = mag(gA[celli])*h > 0.25;
            const vector nRad = rad/(r + VSMALL);
            const bool gasInward = (nRad & gA[celli]) > 0;
            if
            (
                pUse > SMALL
             && iface
             && gasInward
             && r > wireRadius
             && r < wireRadius + gasCavityGap
            )
            {
                pg[celli] = pUse;
                nP += 1;
            }

            if (src[celli] > SMALL)
            {
                nSrc += 1;
                volRate += src[celli]*Vp[celli];
            }
        }

        if (pUse > SMALL)
        {
            stForcef += fvc::interpolate(pGasCavity)*fvc::snGrad(alpha1);
        }

        if
        (
            runTime.timeIndex() != gasCavityLogIndex
         && runTime.timeIndex() % max(gasCavityInterval, 1) == 0
        )
        {
            gasCavityLogIndex = runTime.timeIndex();
            reduce(nP, sumOp<scalar>());
            reduce(nSrc, sumOp<scalar>());
            reduce(gapMin, minOp<scalar>());
            reduce(wMouth, minOp<scalar>());
            reduce(volRate, sumOp<scalar>());
            const word mouth =
                (wMouth > 0.20e-3) ? word("bare")
              : (wMouth < 0.020e-3 ? word("closed") : word("open"));
            Info<< "GasCavity: pCells " << nP
                << " srcCells " << nSrc
                << " p " << pUse
                << " q " << qUse
                << " zContact "
                << (zContact < -1 ? scalar(-1) : zContact*1e3) << " mm"
                << " volRate " << volRate
                << " gapMin "
                << (gapMin > 0.5 ? scalar(-1) : gapMin*1e3) << " mm"
                << " wMouth "
                << (wMouth > 0.5 ? scalar(-1) : wMouth*1e3) << " mm " << mouth
                << nl;
        }
    }
}
