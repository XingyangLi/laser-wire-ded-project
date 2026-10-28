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
        // tau is a ramp, not a one-step overwrite. A full alpha jump on the
        // 19 um neck makes a one-cell interface and the capillary force
        // collapses the time step. The shell is imposed; this only slows
        // how fast that imposition is applied.
        const scalar ramp = min
        (
            max(runTime.value()/max(linePinTau, SMALL), scalar(0)),
            scalar(1)
        );
        const scalar fac = sHold*ramp;

        const vectorField& C = mesh.C().primitiveField();
        const scalarField& Vc = mesh.V();
        scalarField& alpha = alpha1.primitiveFieldRef();
        vectorField& Uc = U.primitiveFieldRef();

        if (linePinZ0 < 0)
        {
            if (linePinZ0User > 0)
            {
                linePinZ0 = linePinZ0User;
                Info<< "LinePin: imposed mouth height " << linePinZ0*1e3
                    << " mm" << nl;
            }
        }
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
                if (r <= wireRadius || r > wireRadius + linePinNCells*h) continue;
                if (alpha[celli] > 0.5) zMax = max(zMax, C[celli].z());
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
        const scalar Khold = fac*linePinK;
        scalar nGas = 0, nMet = 0;
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

        // Wedge: throat of width wBottom down to the moving line, opening
        // to wTop at the original wetted surface. The slope is imposed.
        // Cells outside it, and cells under the slope, stay free so the
        // pool surface can sit on that slope. The old rectangular shell
        // is used when wTop is not set.
        const bool wedgeOn =
            linePinWTop > linePinWBottom && linePinWBottom > 0;
        const scalar wedgeDepth = max(linePinZ0 - zLine, SMALL);

        boolList inShell(mesh.nCells(), false);
        boolList inThroat(mesh.nCells(), false);
        DynamicList<label> shellCells(64);
        forAll(alpha, celli)
        {
            const vector d = C[celli] - wireOrigin;
            const scalar sAx = d & wireUp;
            const vector rad = d - sAx*wireUp;
            if (rad.x() <= 0) continue;
            const scalar h = Foam::cbrt(max(Vc[celli], SMALL));
            const scalar r = mag(rad);
            const scalar gap = r - wireRadius;
            const scalar rMax = wedgeOn ? linePinWTop : linePinNCells*h;
            if (gap <= 0 || gap > rMax) continue;
            const scalar z = C[celli].z();
            if (z > linePinZ0 + 0.5*h || z < zLine - 1.5*h) continue;
            if (z < 0.15e-3) continue;

            scalar zCut = zLine;
            bool underIsFree = false;
            if (wedgeOn && gap > linePinWBottom)
            {
                const scalar f =
                    (gap - linePinWBottom)
                   /max(linePinWTop - linePinWBottom, SMALL);
                zCut = zLine + wedgeDepth*min(max(f, scalar(0)), scalar(1));
                underIsFree = true;
            }
            // Under the slope the metal is not painted back on. That paint
            // was a one-cell film, and it is what drove the speed up.
            if (underIsFree && z <= zCut) continue;

            inShell[celli] = true;
            inThroat[celli] = !underIsFree;
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
            // Throat: gas above the moving line, metal below it so the
            // attachment stays on the wire. Mouth: gas only, above the slope.
            scalar zCut = zLine;
            if (wedgeOn && !inThroat[celli])
            {
                const scalar f =
                    (r - wireRadius - linePinWBottom)
                   /max(linePinWTop - linePinWBottom, SMALL);
                zCut = zLine + wedgeDepth*min(max(f, scalar(0)), scalar(1));
            }
            const scalar target = (z > zCut) ? scalar(0) : scalar(1);
            if (fac > 0)
            {
                scalar dAlpha = fac*(target - alpha[celli]);
                // At most 0.2 of a cell per step, so the interface is not a
                // single-face jump.
                dAlpha = max(min(dAlpha, scalar(0.2)), scalar(-0.2));
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
                // Velocity lock only in the throat. The mouth is free.
                if (inThroat[celli])
                {
                    Uc[celli] += fac*(wireFeedVelocity - Uc[celli]);
                }
            }
            if (Khold > 0 && inThroat[celli])
            {
                Kcontact[celli] = max(Kcontact[celli], Khold);
                Ucontact[celli] = wireFeedVelocity;
            }
            if (target < 0.5) nGas += 1;
            else nMet += 1;
        }

        // The cell just outside the slope is held toward metal. That keeps
        // the bead beside the gap so the free surface cannot fall onto the
        // wire. The old vertical one-cell film did this and then ran the
        // Courant number away; the speed ceiling now stops that, and the
        // neighbour follows the slope instead of a constant-width channel.
        if (fac > 0)
        {
            for (const label celli : shellCells)
            {
                if (alpha[celli] > 0.5) continue;
                const vector d = C[celli] - wireOrigin;
                const vector rad = d - (d & wireUp)*wireUp;
                const scalar r = mag(rad);
                const scalar h = Foam::cbrt(max(Vc[celli], SMALL));
                const scalar z = C[celli].z();
                const label nei = outerCell(celli, r, z, h);
                if (nei < 0 || inShell[nei]) continue;
                const scalar dOut = min(fac*(scalar(1) - alpha[nei]), scalar(0.2));
                alpha[nei] = min(max(alpha[nei] + dOut, scalar(0)), scalar(1));
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
                << "  ramp " << ramp
                << "  gas " << nGas
                << "  metal " << nMet
                << "  feed " << wireFeedVelocity.z()
                << "  wedge " << (wedgeOn ? 1 : 0)
                << "  (throat and slope imposed, pool under the slope is free)"
                << nl;
        }
    }
}

// ************************************************************************* //
