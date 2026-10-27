// Oxide-skin membrane. See createOxideSkin.H. Off -> mu = 0, K = 0.
{
    muOxide == dimensionedScalar(muOxide.dimensions(), Zero);
    Koxide == dimensionedScalar(Koxide.dimensions(), Zero);
    Ukeep == U;

    if (oxideSkinEnabled && oxideSkinStrength > SMALL)
    {
        // Coverage starts bare. One explicit step per time step: carry the
        // film down with the wire, then add oxide on the exposed trailing
        // face. The rate already contains the ppm factor, so the damper
        // below is not multiplied by it again.
        if (oxideGrowth && pimple.firstIter())
        {
            const scalar Vfeed = mag(wireFeedVelocity);
            const vector Ufeed = -wireUp*Vfeed;
            oxideFilm -= runTime.deltaT()*fvc::div
            (
                mesh.Sf() & Ufeed,
                oxideFilm,
                "div(phiOxide,oxideFilm)"
            );

            const volVectorField gradOx(fvc::grad(alpha1));
            scalarField& ox = oxideFilm.primitiveFieldRef();
            const vectorField& CcOx = mesh.C().primitiveField();
            const scalarField& VpOx = mesh.V();
            const scalarField& aOx = alpha1.primitiveField();
            const vectorField& gOx = gradOx.primitiveField();
            const vector trailOx(1, 0, 0);
            const scalar dt = runTime.deltaTValue();
            const scalar sRate =
                oxideSkinStrength*(Vfeed/oxideFeedRef)/oxideTau;

            forAll(ox, celli)
            {
                const vector d = CcOx[celli] - wireOrigin;
                const scalar s = d & wireUp;
                const vector rad = d - s*wireUp;
                const scalar r = mag(rad);
                const scalar h = Foam::cbrt(max(VpOx[celli], SMALL));
                const bool exposed =
                    (rad & trailOx) > 0
                 && s >= oxideSkinZ0 && s <= oxideSkinZ1
                 && r > wireRadius - 0.5*h
                 && r < wireRadius + oxideSkinGap
                 && (mag(gOx[celli])*h > 0.25 || aOx[celli] < 0.5);
                if (exposed)
                {
                    ox[celli] += dt*sRate;
                }
                ox[celli] = min(max(ox[celli], scalar(0)), scalar(2));
            }
            oxideFilm.correctBoundaryConditions();
        }

        const volVectorField gradAlpha(fvc::grad(alpha1));
        scalarField& muI = muOxide.primitiveFieldRef();
        scalarField& KI = Koxide.primitiveFieldRef();
        vectorField& Uk = Ukeep.primitiveFieldRef();
        const vectorField& Uc = U.primitiveField();
        const vectorField& Cc = mesh.C().primitiveField();
        const scalarField& Vp = mesh.V();
        const scalarField& a = alpha1.primitiveField();
        const vectorField& gA = gradAlpha.primitiveField();
        const scalarField& oxNow = oxideFilm.primitiveField();
        const vector trail(1, 0, 0);

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

            // Uniform skin: one strength on the whole shell. Growing skin:
            // that strength is already in the coverage, so a cell scales
            // with min(coverage, 1) and a barely covered cell is left free.
            scalar fac = oxideSkinStrength;
            if (oxideGrowth)
            {
                fac = min(max(oxNow[celli], scalar(0)), scalar(1));
                if (fac < scalar(0.02)) continue;
            }
            const scalar muUse = fac*oxideSkinMu0;
            const scalar Kuse = fac*oxideSkinK0;

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
                << " strength " << oxideSkinStrength;
            if (oxideGrowth)
            {
                const scalar oxMax = returnReduce
                (
                    max(oxideFilm.primitiveField()),
                    maxOp<scalar>()
                );
                Info<< " oxMax " << oxMax;
            }
            Info<< " gapMin "
                << (gapMin > 0.5 ? scalar(-1) : gapMin*1e3) << " mm"
                << " wMouth "
                << (wMouth > 0.5 ? scalar(-1) : wMouth*1e3) << " mm " << mouth
                << " Un " << unMax
                << nl;
        }
    }
}
