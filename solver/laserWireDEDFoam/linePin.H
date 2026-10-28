// Imposed trailing contact. See createLinePin.H. Runs after contactLine.H
// has zeroed Kcontact. Off leaves alpha and the momentum equation unchanged.
//
// Liquid taken out of the shell is passed to the next cell outward, and
// liquid put into the shell is taken from that cell. The pin moves the
// interface. It does not delete the coating.
{
    if (linePinEnabled)
    {
        const scalar sHold = oxygenDependent
            ? min(max(chamberOxygenPpm/linePinPpmRef, scalar(0)), scalar(1))
            : scalar(1);
        // 300 ppm removes the whole error after this alpha solve. Lower ppm
        // removes that fraction, so a strong capillary flux can push the
        // shell back toward metal.
        const scalar fac = sHold;

        const vectorField& C = mesh.C().primitiveField();
        const scalarField& Vc = mesh.V();
        scalarField& alpha = alpha1.primitiveFieldRef();
        vectorField& Uc = U.primitiveFieldRef();
        // Radial width of the imposed shell. A fixed thickness keeps a coarse
        // cell, whose own size would claim a thick shell, out of the gap.
        auto shellThick = [&](const scalar hCell) -> scalar
        {
            return (linePinThickness > 0) ? linePinThickness : linePinNCells*hCell;
        };

        if (linePinZ0 < 0)
        {
            scalar zMax = -GREAT;
            forAll(alpha, celli)
            {
                const vector d = C[celli] - wireOrigin;
                const scalar sAx = d & wireUp;
                const vector rad = d - sAx*wireUp;
                const scalar h = Foam::cbrt(max(Vc[celli], SMALL));
                if (rad.x() <= 0) continue;
                const scalar r = mag(rad);
                if (r <= wireRadius || r > wireRadius + shellThick(h)) continue;
                // The solid wire above the pool is alpha 1 and cold. The crest
                // is the highest liquid metal in the shell, not that column.
                if (alpha[celli] > 0.5 && liquidFraction[celli] > 0.5)
                {
                    zMax = max(zMax, C[celli].z());
                }
            }
            reduce(zMax, maxOp<scalar>());
            if (zMax < 0.2e-3) zMax = 1.20e-3;
            linePinZ0 = zMax;
            Info<< "LinePin: wetted top " << linePinZ0*1e3 << " mm" << nl;
        }

        const scalar zLine = max
        (
            linePinZ0 + wireFeedVelocity.z()*runTime.value(),
            scalar(0.2e-3)
        );
        const scalar Khold = sHold*linePinK;
        scalar nGas = 0, nMet = 0;
        const scalar spanZ = max(linePinZ0 - zLine, scalar(1e-4));
        // Graded bias: narrow and fully held at the line, wider and softer
        // toward the crest. Cells outside the bias are not painted.
        auto thickAt = [&](const scalar z, const scalar hCell) -> scalar
        {
            const scalar base = shellThick(hCell);
            if (linePinThicknessTop <= base || z <= zLine) return base;
            const scalar s = min(max((z - zLine)/spanZ, scalar(0)), scalar(1));
            return base + s*(linePinThicknessTop - base);
        };
        auto fadeAt = [&](const scalar z) -> scalar
        {
            if (linePinThicknessTop <= 0 || z <= zLine + linePinBand) return scalar(1);
            const scalar s = min(max((z - zLine)/spanZ, scalar(0)), scalar(1));
            return max(scalar(1) - linePinFade*s, scalar(0.2));
        };
        const labelListList& cellCells = mesh.cellCells();

        // Radial neighbour, further from the wire, on the trailing side.
        auto outerCell = [&](const label celli, const scalar r0, const scalar z0c, const scalar hCell) -> label
        {
            label best = -1;
            scalar bestR = GREAT;
            for (const label nei : cellCells[celli])
            {
                const vector dn = C[nei] - wireOrigin;
                const scalar sN = dn & wireUp;
                const vector rn = dn - sN*wireUp;
                if (rn.x() <= 0) continue;
                const scalar r = mag(rn);
                if (r <= r0 + 1e-8) continue;
                if (mag(C[nei].z() - z0c) > 2.5*hCell) continue;
                if (r < bestR)
                {
                    bestR = r;
                    best = nei;
                }
            }
            return best;
        };

        boolList inShell(mesh.nCells(), false);
        DynamicList<label> shellCells(64);
        forAll(alpha, celli)
        {
            const vector d = C[celli] - wireOrigin;
            const scalar sAx = d & wireUp;
            const vector rad = d - sAx*wireUp;
            if (rad.x() <= 0) continue;
            const scalar h = Foam::cbrt(max(Vc[celli], SMALL));
            const scalar r = mag(rad);
            const scalar z = C[celli].z();
            if (r <= wireRadius || r > wireRadius + thickAt(z, h)) continue;
            if (z > linePinZ0 + 0.5*h || z < zLine - 1.5*h) continue;
            if (z < 0.15e-3) continue;
            inShell[celli] = true;
            shellCells.append(celli);
        }

        for (const label celli : shellCells)
        {
            const vector d = C[celli] - wireOrigin;
            const scalar sAx = d & wireUp;
            const vector rad = d - sAx*wireUp;
            const scalar h = Foam::cbrt(max(Vc[celli], SMALL));
            const scalar r = mag(rad);
            const scalar z = C[celli].z();
            // Above the line the target is gas. Below it the target is metal,
            // so the attachment stays on the wire. Outside this z window the
            // pool is untouched.
            const scalar target = (z > zLine) ? scalar(0) : scalar(1);
            const scalar facLocal = fac*fadeAt(z);
            if (facLocal > 0)
            {
                const scalar dAlpha = facLocal*(target - alpha[celli]);
                alpha[celli] = min(max(alpha[celli] + dAlpha, scalar(0)), scalar(1));
                // give > 0: liquid left the shell and must land outside it.
                scalar give = -dAlpha*Vc[celli];
                label cur = celli;
                scalar rCur = r;
                for (label step = 0; step < 4 && mag(give) > 1e-18; ++step)
                {
                    const label nei = outerCell(cur, rCur, z, h);
                    if (nei < 0) break;
                    const vector dn = C[nei] - wireOrigin;
                    const vector rn = dn - (dn & wireUp)*wireUp;
                    cur = nei;
                    rCur = mag(rn);
                    if (inShell[nei]) continue;
                    if (give > 0)
                    {
                        const scalar room = max((1 - alpha[nei])*Vc[nei], scalar(0));
                        if (room <= 1e-18) continue;
                        const scalar take = min(give, room);
                        alpha[nei] = min(alpha[nei] + take/Vc[nei], scalar(1));
                        give -= take;
                    }
                    else
                    {
                        const scalar avail = max(alpha[nei]*Vc[nei], scalar(0));
                        const scalar take = min(-give, avail);
                        alpha[nei] = max(alpha[nei] - take/Vc[nei], scalar(0));
                        give += take;
                        break;
                    }
                }
                Uc[celli] += facLocal*(wireFeedVelocity - Uc[celli]);
            }
            // The stiff hold is the line itself. Above the band the meniscus
            // is only biased, so it can open wider than the imposed taper.
            if (Khold > 0 && z <= zLine + linePinBand)
            {
                Kcontact[celli] = max(Kcontact[celli], Khold);
                Ucontact[celli] = wireFeedVelocity;
            }
            if (target < 0.5) nGas += 1;
            else nMet += 1;
        }

        // The cell just outside the gas shell keeps the liquid that was
        // displaced off the wire. Selected by radius, not by cellCells,
        // because the neck is split across processors. Cells beyond this
        // one cell are free. ppm uses the same hold.
        // A graded shell does not clamp the outer cell to metal. That clamp
        // is what kept cal109 a rectangle. The free surface sits where the
        // meniscus relaxes.
        if (fac > 0 && linePinThicknessTop <= 0)
        {
            forAll(alpha, celli)
            {
                if (inShell[celli]) continue;
                const vector d = C[celli] - wireOrigin;
                const scalar sAx = d & wireUp;
                const vector rad = d - sAx*wireUp;
                if (rad.x() <= 0) continue;
                const scalar h = Foam::cbrt(max(Vc[celli], SMALL));
                const scalar r = mag(rad);
                const scalar rShell = wireRadius + shellThick(h);
                if (r <= rShell || r > rShell + h) continue;
                const scalar z = C[celli].z();
                if (z <= zLine || z > linePinZ0 + 0.5*h) continue;
                alpha[celli] += fac*(scalar(1) - alpha[celli]);
                alpha[celli] = min(max(alpha[celli], scalar(0)), scalar(1));
            }
        }

        alpha2 = 1.0 - alpha1;
        rho == alpha1*rho1 + alpha2*rho2;
        mixture.correct();

        reduce(nGas, sumOp<scalar>());
        reduce(nMet, sumOp<scalar>());
        if
        (
            runTime.timeIndex() <= 2
         || runTime.timeIndex() % max(contactInterval, 1) == 0
        )
        {
            Info<< "LinePin: zLine " << zLine*1e3
                << " mm  z0 " << linePinZ0*1e3
                << " mm  hold " << sHold
                << "  gas " << nGas
                << "  metal " << nMet
                << "  feed " << wireFeedVelocity.z()
                << nl;
        }
    }
}

// ************************************************************************* //
