// Gas entry behind the dragged contact line. See createSlitEntry.H.
// Alpha of opened cells is lowered and that metal volume is returned to
// liquid elsewhere, so the phase fraction does not drop.
{
    if (slitEntryEnabled)
    {
        const scalar dt = runTime.deltaTValue();
        const vectorField& Cc = mesh.C().primitiveField();
        const scalarField& Vc = mesh.V();
        scalarField& alpha = alpha1.primitiveFieldRef();
        const label nCells = mesh.nCells();

        // Generated crest: highest metal a little off the wall, so the thin
        // film on the wire is not mistaken for the bead surface.
        scalar zSurf = -GREAT;
        for (label celli = 0; celli < nCells; ++celli)
        {
            const vector d = Cc[celli] - wireOrigin;
            const scalar sAx = d & wireUp;
            const vector rad = d - sAx*wireUp;
            if (rad.x() <= 0) continue;
            const scalar gap = mag(rad) - wireRadius;
            // Off the wall film, and only the refined neck. A coarse cell
            // above the bead was setting the crest at 1.80 mm.
            if (Foam::cbrt(Vc[celli]) > 3.5e-5) continue;
            // 0.02 mm skips the wall film. 0.60 mm still sees the bead top
            // after the shoulder rounds inside the old 0.08 mm cutoff.
            if (gap < 2.0e-5 || gap > 6.0e-4) continue;
            if (alpha[celli] < 0.5) continue;
            if (sAx < 0.6e-3) continue;
            zSurf = max(zSurf, sAx);
        }
        reduce(zSurf, maxOp<scalar>());

        if (zSurf > 0.5e-3)
        {
            if (slitZpin < 0)
            {
                slitZpin = zSurf;
                slitZfront = zSurf;
                Info<< "SlitEntry: pinned line starts at the generated crest "
                    << zSurf*1e3 << " mm. Nothing opened." << nl;
            }
            else
            {
                // Imposed: the pin is dragged at the feed. The crest is not.
                slitZpin += (wireFeedVelocity & wireUp)*dt;
                slitZpin = max(slitZpin, scalar(0.70e-3));
            }

            const scalar stretch = zSurf - slitZpin;
            if (stretch > slitThresh)
            {
                slitZfront = max
                (
                    slitZpin,
                    slitZfront - slitRate*dt
                );
            }

            boolList opening(nCells, false);
            scalarField aNew(alpha);
            // Physical lengths, not a cell count. The front is smeared over
            // 0.02 mm, and each step removes at most entryRate*dt of metal
            // (capped at 0.002 mm) and at most a quarter of the cell.
            const scalar hFront = 2.0e-5;
            const scalar convDepth =
                min(max(slitRate*dt, scalar(0)), scalar(2.0e-6));

            for (label celli = 0; celli < nCells; ++celli)
            {
                const vector d = Cc[celli] - wireOrigin;
                const scalar sAx = d & wireUp;
                const vector rad = d - sAx*wireUp;
                if (rad.x() <= 0) continue;
                if (sAx <= slitZfront || sAx >= zSurf) continue;
                if (Foam::cbrt(Vc[celli]) > 3.5e-5) continue;
                const scalar r = mag(rad);
                const scalar gap = r - wireRadius;
                const scalar depth = zSurf - sAx;
                const scalar w =
                    slitGapRoot
                  + (slitGapMouth - slitGapRoot)
                   *max(scalar(0), scalar(1) - depth/max(slitSpan, SMALL));
                if (gap <= 0 || gap > w) continue;
                opening[celli] = true;
                scalar target = 0;
                if (sAx < slitZfront + hFront)
                {
                    target = min(max((sAx - slitZfront)/hFront, scalar(0)), scalar(1));
                }
                const scalar hNorm = max(Foam::cbrt(Vc[celli]), SMALL);
                const scalar dAlpha = min(convDepth/hNorm, scalar(0.25));
                aNew[celli] = max(target, alpha[celli] - dAlpha);
            }

            scalar metalBefore = 0;
            for (label celli = 0; celli < nCells; ++celli)
            {
                metalBefore += alpha[celli]*Vc[celli];
            }
            reduce(metalBefore, sumOp<scalar>());

            scalar removed = 0;
            scalarField donate(nCells, 0);
            const labelListList& cellCells = mesh.cellCells();

            for (label celli = 0; celli < nCells; ++celli)
            {
                if (!opening[celli]) continue;
                const scalar dV = (alpha[celli] - aNew[celli])*Vc[celli];
                if (dV <= SMALL) continue;
                removed += dV;
                scalar capSum = 0;
                const labelList& nb = cellCells[celli];
                forAll(nb, ni)
                {
                    const label n = nb[ni];
                    if (opening[n] || aNew[n] < 0.2 || aNew[n] > 0.995) continue;
                    capSum += (1 - aNew[n])*Vc[n];
                }
                if (capSum > SMALL)
                {
                    scalar left = dV;
                    forAll(nb, ni)
                    {
                        const label n = nb[ni];
                        if (opening[n] || aNew[n] < 0.2 || aNew[n] > 0.995) continue;
                        const scalar cap = (1 - aNew[n])*Vc[n];
                        const scalar give = min(left, dV*cap/capSum);
                        aNew[n] += give/Vc[n];
                        left -= give;
                    }
                    if (left > SMALL) donate[celli] = left;
                }
                else
                {
                    donate[celli] = dV;
                }
            }

            reduce(removed, sumOp<scalar>());
            scalar leftTot = gSum(donate);
            scalar returned = removed - leftTot;
            scalar capTot = 0;
            for (label celli = 0; celli < nCells; ++celli)
            {
                if (opening[celli]) continue;
                if (aNew[celli] <= 0.02 || aNew[celli] >= 0.995) continue;
                const vector d = Cc[celli] - wireOrigin;
                const scalar sAx = d & wireUp;
                if (sAx < 0.5e-3 || sAx > zSurf + 0.3e-3) continue;
                const scalar rad = mag(d - sAx*wireUp);
                if (rad > wireRadius + 1.5e-3) continue;
                capTot += (1 - aNew[celli])*Vc[celli];
            }
            reduce(capTot, sumOp<scalar>());

            if (leftTot > SMALL && capTot > SMALL)
            {
                const scalar use = min(leftTot, capTot);
                for (label celli = 0; celli < nCells; ++celli)
                {
                    if (opening[celli]) continue;
                    if (aNew[celli] <= 0.02 || aNew[celli] >= 0.995) continue;
                    const vector d = Cc[celli] - wireOrigin;
                    const scalar sAx = d & wireUp;
                    if (sAx < 0.5e-3 || sAx > zSurf + 0.3e-3) continue;
                    const scalar rad = mag(d - sAx*wireUp);
                    if (rad > wireRadius + 1.5e-3) continue;
                    const scalar cap = (1 - aNew[celli])*Vc[celli];
                    aNew[celli] += use*(cap/capTot)/Vc[celli];
                }
                returned += use;
                leftTot -= use;
            }

            scalar nOpen = 0;
            scalar nSpur = 0;
            for (label celli = 0; celli < nCells; ++celli)
            {
                alpha[celli] = min(max(aNew[celli], scalar(0)), scalar(1));
                if (opening[celli] && alpha[celli] < 0.05)
                {
                    nOpen += 1;
                }
                if (!opening[celli] && alpha[celli] < 0.5)
                {
                    const vector d = Cc[celli] - wireOrigin;
                    const scalar sAx = d & wireUp;
                    const vector rad = d - sAx*wireUp;
                    const scalar gap = mag(rad) - wireRadius;
                    if (rad.x() <= 0 && gap > 0 && gap < 1.0e-4 && sAx > 1.0e-3)
                    {
                        nSpur += 1;
                    }
                }
            }
            reduce(nOpen, sumOp<scalar>());
            reduce(nSpur, sumOp<scalar>());
            scalar metalAfter = 0;
            for (label celli = 0; celli < nCells; ++celli)
            {
                metalAfter += alpha[celli]*Vc[celli];
            }
            reduce(metalAfter, sumOp<scalar>());
            const scalar imbalance = metalAfter - metalBefore;
            alpha1.correctBoundaryConditions();
            U.correctBoundaryConditions();
            mixture.correct();

            if
            (
                runTime.timeIndex() <= 3
             || runTime.timeIndex() % max(contactInterval, 1) == 0
            )
            {
                Info<< "SlitEntry: zPin " << slitZpin*1e3
                    << " mm (imposed, feed " << (wireFeedVelocity & wireUp)
                    << ")  zSurf " << zSurf*1e3
                    << " mm (generated)  stretch " << stretch*1e3
                    << " mm  thresh " << slitThresh*1e3
                    << " mm  front " << slitZfront*1e3
                    << " mm  open " << nOpen
                    << "  metalOut " << removed
                    << "  metalBack " << returned
                    << "  imbalance " << imbalance
                    << "  spur " << nSpur
                    << "  (opening from the drag, not painted)"
                    << nl;
            }
        }
    }
}
