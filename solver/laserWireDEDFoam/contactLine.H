// Contact-line hysteresis + solidification pinning. See createContactLine.H.
// Runs after the energy equation so liquidFraction is current. Off -> K = 0.
{
    Kcontact == dimensionedScalar(Kcontact.dimensions(), Zero);
    Fcontact == dimensionedVector(Fcontact.dimensions(), Zero);
    contactState == dimensionedScalar(contactState.dimensions(), Zero);

    if (contactEnabled)
    {
        const volVectorField gradAlpha(fvc::grad(alpha1));
        const vectorField& C = mesh.C().primitiveField();
        const scalarField& V = mesh.V();
        const labelListList& cCells = mesh.cellCells();
        const scalar pi = constant::mathematical::pi;

        scalar nMolten = 0, nPinned = 0, nAdv = 0, nRec = 0, nFrozen = 0;
        scalar thSum = 0, wTh = 0, thMin = GREAT, thMax = -GREAT;
        scalar lenPin = 0, lenMobile = 0;
        scalar xMin = GREAT, xMax = -GREAT, yMin = GREAT, yMax = -GREAT;

        forAll(alpha1, celli)
        {
            const scalar h = Foam::cbrt(max(V[celli], SMALL));
            const vector gA = gradAlpha[celli];
            const scalar magG = mag(gA);
            if (magG*h < contactGradMin) continue;

            const scalar a = alpha1[celli];
            bool gasNbr = (a < 0.20);
            bool liquidNbr = (a > 0.50 && liquidFraction[celli] > 0.50);
            bool solidSub = false;
            bool solidDep = false;
            scalar flMetal = (a > 0.30) ? liquidFraction[celli] : 0.0;
            vector nSub = Zero;

            auto consider = [&](const label c, const vector& fromSolid)
            {
                if (alpha1[c] < 0.20) gasNbr = true;
                if (alpha1[c] > 0.30) flMetal = max(flMetal, liquidFraction[c]);
                if (alpha1[c] > 0.50 && liquidFraction[c] > 0.50) liquidNbr = true;
                const bool solid =
                    alpha1[c] > 0.50
                 && liquidFraction[c] < contactFlSolid
                 && !(inWireZone[c] && lwdUnmeltedWire(c));
                if (!solid) return;
                const scalar mg = mag(fromSolid);
                if (mg > SMALL) nSub += fromSolid/mg;
                const bool deposit =
                    meltHistory[c] > 0.50
                 || C[c].z() > contactZSub + 0.25*h;
                if (deposit) solidDep = true;
                else solidSub = true;
            };

            consider(celli, vector::zero);
            for (const label n : cCells[celli])
            {
                consider(n, C[celli] - C[n]);
            }

            const bool moltenCL = gasNbr && liquidNbr && (solidSub || solidDep);
            const bool frozenCL = gasNbr && !liquidNbr && solidDep;
            if (!moltenCL && !frozenCL) continue;
            if (mag(nSub) < 0.5) continue;
            nSub /= mag(nSub);

            const vector nAlpha = gA/(magG + VSMALL);
            const scalar cosApp = max(min(-(nAlpha & nSub), scalar(1)), scalar(-1));
            const scalar thetaApp = Foam::acos(cosApp);

            // Solidification opens the hysteresis window to [0, pi].
            scalar sPin = 0;
            if (frozenCL || flMetal <= contactFlPin) sPin = 1;
            else if (flMetal < contactFlFree)
            {
                sPin = (contactFlFree - flMetal)
                     /max(contactFlFree - contactFlPin, SMALL);
            }
            const scalar thetaR = (1.0 - sPin)*contactThetaR0;
            const scalar thetaA = (1.0 - sPin)*contactThetaA0 + sPin*pi;
            const bool pinned = (thetaApp >= thetaR && thetaApp <= thetaA);

            const scalar seg = h;
            if (moltenCL && !frozenCL)
            {
                nMolten += 1;
                thSum += thetaApp*V[celli];
                wTh += V[celli];
                thMin = min(thMin, thetaApp);
                thMax = max(thMax, thetaApp);
                xMin = min(xMin, C[celli].x());
                xMax = max(xMax, C[celli].x());
                yMin = min(yMin, C[celli].y());
                yMax = max(yMax, C[celli].y());
            }

            if (pinned)
            {
                Kcontact[celli] = contactKpin;
                if (sPin >= 0.5)
                {
                    contactState[celli] = 2;
                    nFrozen += 1;
                    lenPin += seg;
                }
                else
                {
                    contactState[celli] = 1;
                    nPinned += 1;
                    lenPin += seg;
                }
            }
            else if (thetaApp > thetaA)
            {
                // Too large an angle: the line advances (force toward the gas).
                contactState[celli] = 3;
                nAdv += 1;
                lenMobile += seg;
                vector tOut = -(nAlpha - (nAlpha & nSub)*nSub);
                const scalar mt = mag(tOut);
                if (mt > 0.05)
                {
                    tOut /= mt;
                    const scalar dCos = Foam::cos(thetaA) - Foam::cos(thetaApp);
                    scalar fMag =
                        contactForceFactor*sigmaT[celli]*dCos*magG/h;
                    const scalar fMax = 2.0*max(sigmaT[celli], SMALL)/sqr(h);
                    fMag = max(min(fMag, fMax), -fMax);
                    Fcontact[celli] = (fMag*max(min(a, scalar(1)), scalar(0)))*tOut;
                }
            }
            else
            {
                // Too small an angle: the line recedes.
                contactState[celli] = 4;
                nRec += 1;
                lenMobile += seg;
                vector tOut = -(nAlpha - (nAlpha & nSub)*nSub);
                const scalar mt = mag(tOut);
                if (mt > 0.05)
                {
                    tOut /= mt;
                    const scalar dCos = Foam::cos(thetaR) - Foam::cos(thetaApp);
                    scalar fMag =
                        contactForceFactor*sigmaT[celli]*dCos*magG/h;
                    const scalar fMax = 2.0*max(sigmaT[celli], SMALL)/sqr(h);
                    fMag = max(min(fMag, fMax), -fMax);
                    Fcontact[celli] = (fMag*max(min(a, scalar(1)), scalar(0)))*tOut;
                }
            }
        }

        Kcontact.correctBoundaryConditions();
        Fcontact.correctBoundaryConditions();
        contactState.correctBoundaryConditions();

        const bool report =
            pimple.finalIter()
         && (
                runTime.timeIndex() % max(contactInterval, 1) == 0
             || runTime.writeTime()
            );
        if (report)
        {
            reduce(nMolten, sumOp<scalar>());
            reduce(nPinned, sumOp<scalar>());
            reduce(nAdv, sumOp<scalar>());
            reduce(nRec, sumOp<scalar>());
            reduce(nFrozen, sumOp<scalar>());
            reduce(thSum, sumOp<scalar>());
            reduce(wTh, sumOp<scalar>());
            reduce(thMin, minOp<scalar>());
            reduce(thMax, maxOp<scalar>());
            reduce(lenPin, sumOp<scalar>());
            reduce(lenMobile, sumOp<scalar>());
            reduce(xMin, minOp<scalar>());
            reduce(xMax, maxOp<scalar>());
            reduce(yMin, minOp<scalar>());
            reduce(yMax, maxOp<scalar>());

            const scalar thMean = (wTh > SMALL) ? thSum/wTh : -1;
            Info<< "ContactLine: molten = " << label(nMolten)
                << "  pinned = " << label(nPinned)
                << "  advancing = " << label(nAdv)
                << "  receding = " << label(nRec)
                << "  frozen = " << label(nFrozen)
                << "  thetaMean = " << (thMean < 0 ? -1 : thMean/contactDeg)
                << " deg" << endl;

            if (Pstream::master())
            {
                const fileName dir(runTime.globalPath()/"postProcessing"/"contactLine");
                mkDir(dir);
                const fileName fn(dir/"contactLine.dat");
                const bool isNew = !isFile(fn);
                std::ofstream os(fn.c_str(), std::ios::app);
                if (isNew)
                {
                    os << "# time[s] nMolten nPinnedHysteresis nAdvancing nReceding "
                       << "nFrozenSolidification thetaMean[deg] thetaMin[deg] "
                       << "thetaMax[deg] lengthPinned[m] lengthMobile[m] "
                       << "xMin[m] xMax[m] yMin[m] yMax[m]\n"
                       << "# contactState field: 1 hysteresis pin, 2 solidification "
                       << "pin, 3 advancing, 4 receding\n"
                       << "# length* is the sum of cell sizes on the triple line "
                       << "(mesh measure, not a fitted arc length)\n";
                }
                os.setf(std::ios::scientific);
                os.precision(8);
                os << runTime.value() << ' '
                   << label(nMolten) << ' ' << label(nPinned) << ' '
                   << label(nAdv) << ' ' << label(nRec) << ' ' << label(nFrozen) << ' '
                   << (thMean < 0 ? -1 : thMean/contactDeg) << ' '
                   << (thMin < GREAT/2 ? thMin/contactDeg : -1) << ' '
                   << (thMax > -GREAT/2 ? thMax/contactDeg : -1) << ' '
                   << lenPin << ' ' << lenMobile << ' '
                   << (xMin < GREAT/2 ? xMin : 0) << ' '
                   << (xMax > -GREAT/2 ? xMax : 0) << ' '
                   << (yMin < GREAT/2 ? yMin : 0) << ' '
                   << (yMax > -GREAT/2 ? yMax : 0) << '\n';
            }
        }
    }
}
