// Contact-line hysteresis + solidification pinning. See createContactLine.H.
// Runs after the energy equation so liquidFraction is current. Off -> K = 0.
{
    Kcontact == dimensionedScalar(Kcontact.dimensions(), Zero);
    Fcontact == dimensionedVector(Fcontact.dimensions(), Zero);
    contactState == dimensionedScalar(contactState.dimensions(), Zero);
    contactSupport == dimensionedScalar(contactSupport.dimensions(), Zero);
    Ucontact == Usolid;
    contactWireZMax = -GREAT;
    contactWireZMin = GREAT;

    if (contactEnabled)
    {
        const volVectorField gradAlpha(fvc::grad(alpha1));
        const vectorField& C = mesh.C().primitiveField();
        const scalarField& V = mesh.V();
        const labelListList& cCells = mesh.cellCells();
        const scalar pi = constant::mathematical::pi;
        const vector UwireSurf =
            stubFeedFac*wireFeedVelocity + vector(0, weaveYDot, 0);

        scalar nMolten = 0, nPinned = 0, nAdv = 0, nRec = 0, nFrozen = 0;
        scalar thSum = 0, wTh = 0, thMin = GREAT, thMax = -GREAT;
        scalar lenPin = 0, lenMobile = 0;
        scalar xMin = GREAT, xMax = -GREAT, yMin = GREAT, yMax = -GREAT;
        scalar nWire = 0, nWirePin = 0, nWireAdv = 0, nWireRec = 0;
        scalar thWireSum = 0, wWire = 0;
        scalar zWireMax = -GREAT, zWireMin = GREAT;

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
            bool wireNbr = false;
            scalar flMetal = (a > 0.30) ? liquidFraction[celli] : 0.0;
            vector nPlate = Zero;

            auto consider = [&](const label c, const vector& fromSolid)
            {
                if (alpha1[c] < 0.20) gasNbr = true;
                if (alpha1[c] > 0.30) flMetal = max(flMetal, liquidFraction[c]);
                if (alpha1[c] > 0.50 && liquidFraction[c] > 0.50) liquidNbr = true;

                const bool unmeltedWire =
                    inWireZone[c] && lwdUnmeltedWire(c)
                 && alpha1[c] > 0.50
                 && liquidFraction[c] < contactFlSolid;
                if (unmeltedWire)
                {
                    if (contactPinWire) wireNbr = true;
                    return;   // the feed itself is not a substrate support
                }

                const bool solid =
                    alpha1[c] > 0.50
                 && liquidFraction[c] < contactFlSolid;
                if (!solid) return;
                const scalar mg = mag(fromSolid);
                if (mg > SMALL) nPlate += fromSolid/mg;
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

            // Wire line: molten metal, gas, and unmelted wire, within a cell
            // or so of the wire surface. Plate/deposit lines use the old test.
            bool useWire = false;
            vector nSub = Zero;
            if (contactPinWire && gasNbr && liquidNbr && wireNbr)
            {
                const vector dAx = C[celli] - wireOrigin;
                const scalar sAx = dAx & wireUp;
                const vector rad = dAx - sAx*wireUp;
                const scalar r = mag(rad);
                if (r > SMALL && r < wireRadius + 1.75*h)
                {
                    useWire = true;
                    nSub = rad/r;
                }
            }

            const bool moltenPlate = gasNbr && liquidNbr && (solidSub || solidDep);
            const bool frozenPlate = gasNbr && !liquidNbr && solidDep;
            if (!useWire)
            {
                if (!moltenPlate && !frozenPlate) continue;
                if (mag(nPlate) < 0.5) continue;
                nSub = nPlate/mag(nPlate);
            }

            const vector nAlpha = gA/(magG + VSMALL);
            const scalar cosApp = max(min(-(nAlpha & nSub), scalar(1)), scalar(-1));
            const scalar thetaApp = Foam::acos(cosApp);

            // Solidification opens the hysteresis window to [0, pi].
            scalar sPin = 0;
            if ((!useWire && frozenPlate) || flMetal <= contactFlPin) sPin = 1;
            else if (flMetal < contactFlFree)
            {
                sPin = (contactFlFree - flMetal)
                     /max(contactFlFree - contactFlPin, SMALL);
            }
            // One wire window, unless wireSector blends in a wider trailing one.
            // psi = 0 on the trailing face (+x), pi on the leading face.
            scalar thetaRwire = contactThetaRwire;
            scalar thetaAwire = contactThetaAwire;
            if (useWire && contactWireSector)
            {
                vector trail(1, 0, 0);
                trail -= (trail & wireUp)*wireUp;
                const scalar mtTrail = mag(trail);
                if (mtTrail > SMALL)
                {
                    trail /= mtTrail;
                }
                const scalar cosPsi =
                    max(min(nSub & trail, scalar(1)), scalar(-1));
                const scalar psi = Foam::acos(cosPsi);
                scalar wTrail = 0;
                if (contactWireSectorBlend <= SMALL)
                {
                    wTrail = psi <= contactWireSectorHalf ? scalar(1) : scalar(0);
                }
                else
                {
                    const scalar inner =
                        contactWireSectorHalf - 0.5*contactWireSectorBlend;
                    const scalar outer =
                        contactWireSectorHalf + 0.5*contactWireSectorBlend;
                    if (psi <= inner) wTrail = 1;
                    else if (psi >= outer) wTrail = 0;
                    else
                    {
                        const scalar tBlend = (psi - inner)/contactWireSectorBlend;
                        wTrail = 0.5*(1 + Foam::cos(pi*tBlend));
                    }
                }
                thetaRwire =
                    (1 - wTrail)*contactThetaRwire + wTrail*contactThetaRtrail;
                thetaAwire =
                    (1 - wTrail)*contactThetaAwire + wTrail*contactThetaAtrail;
                if (thetaAwire < thetaRwire) thetaAwire = thetaRwire;
            }
            const scalar thetaR0 = useWire ? thetaRwire : contactThetaR0;
            const scalar thetaA0 = useWire ? thetaAwire : contactThetaA0;
            const scalar thetaR = (1.0 - sPin)*thetaR0;
            const scalar thetaA = (1.0 - sPin)*thetaA0 + sPin*pi;
            const bool pinned = (thetaApp >= thetaR && thetaApp <= thetaA);

            const scalar seg = h;
            if (useWire)
            {
                nWire += 1;
                thWireSum += thetaApp*V[celli];
                wWire += V[celli];
                zWireMax = max(zWireMax, C[celli].z());
                zWireMin = min(zWireMin, C[celli].z());
                contactSupport[celli] = 2;
                // Molten kink: hold the line in the head frame (or on the
                // feed, if wireVelocity wire). A freezing meniscus is handed
                // to the plate velocity so the bead can leave with the part.
                // Fully solid cells are still owned by the Carman-Kozeny sink.
                if (sPin >= 0.5)
                {
                    Ucontact[celli] = solidVelocity;
                }
                else if (contactWireHeadFrame)
                {
                    Ucontact[celli] = vector::zero;
                }
                else
                {
                    Ucontact[celli] = UwireSurf;
                }
            }
            else if (moltenPlate && !frozenPlate)
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
                contactSupport[celli] = 1;
                Ucontact[celli] = Usolid[celli];
            }
            else
            {
                contactSupport[celli] = 1;
                Ucontact[celli] = Usolid[celli];
            }

            if (pinned)
            {
                Kcontact[celli] = contactKpin;
                if (sPin >= 0.5)
                {
                    contactState[celli] = useWire ? 6 : 2;
                    if (useWire) nWirePin += 1;
                    else nFrozen += 1;
                    lenPin += seg;
                }
                else
                {
                    contactState[celli] = useWire ? 5 : 1;
                    if (useWire) nWirePin += 1;
                    else nPinned += 1;
                    lenPin += seg;
                }
            }
            else if (thetaApp > thetaA)
            {
                contactState[celli] = useWire ? 7 : 3;
                if (useWire) nWireAdv += 1;
                else nAdv += 1;
                lenMobile += seg;
                vector tOut = -(nAlpha - (nAlpha & nSub)*nSub);
                const scalar mt = mag(tOut);
                if (mt > 0.05)
                {
                    tOut /= mt;
                    const scalar dCos = Foam::cos(thetaA) - Foam::cos(thetaApp);
                    scalar fMag =
                        contactForceFactor*sigmaT[celli]*dCos*magG/h;
                    if (contactForceBlend > SMALL)
                    {
                        fMag *= max
                        (
                            min((thetaApp - thetaA)/contactForceBlend, scalar(1)),
                            scalar(0)
                        );
                    }
                    const scalar fMax = 2.0*max(sigmaT[celli], SMALL)/sqr(h);
                    fMag = max(min(fMag, fMax), -fMax);
                    Fcontact[celli] = (fMag*max(min(a, scalar(1)), scalar(0)))*tOut;
                }
            }
            else
            {
                contactState[celli] = useWire ? 8 : 4;
                if (useWire) nWireRec += 1;
                else nRec += 1;
                lenMobile += seg;
                vector tOut = -(nAlpha - (nAlpha & nSub)*nSub);
                const scalar mt = mag(tOut);
                if (mt > 0.05)
                {
                    tOut /= mt;
                    const scalar dCos = Foam::cos(thetaR) - Foam::cos(thetaApp);
                    scalar fMag =
                        contactForceFactor*sigmaT[celli]*dCos*magG/h;
                    if (contactForceBlend > SMALL)
                    {
                        fMag *= max
                        (
                            min((thetaR - thetaApp)/contactForceBlend, scalar(1)),
                            scalar(0)
                        );
                    }
                    const scalar fMax = 2.0*max(sigmaT[celli], SMALL)/sqr(h);
                    fMag = max(min(fMag, fMax), -fMax);
                    Fcontact[celli] = (fMag*max(min(a, scalar(1)), scalar(0)))*tOut;
                }
            }
        }

        Kcontact.correctBoundaryConditions();
        Fcontact.correctBoundaryConditions();
        contactState.correctBoundaryConditions();
        contactSupport.correctBoundaryConditions();
        Ucontact.correctBoundaryConditions();

        reduce(zWireMax, maxOp<scalar>());
        reduce(zWireMin, minOp<scalar>());
        contactWireZMax = zWireMax;
        contactWireZMin = zWireMin;

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
            reduce(nWire, sumOp<scalar>());
            reduce(nWirePin, sumOp<scalar>());
            reduce(nWireAdv, sumOp<scalar>());
            reduce(nWireRec, sumOp<scalar>());
            reduce(thWireSum, sumOp<scalar>());
            reduce(wWire, sumOp<scalar>());

            const scalar thMean = (wTh > SMALL) ? thSum/wTh : -1;
            const scalar thWireMean = (wWire > SMALL) ? thWireSum/wWire : -1;
            Info<< "ContactLine: molten = " << label(nMolten)
                << "  pinned = " << label(nPinned)
                << "  advancing = " << label(nAdv)
                << "  receding = " << label(nRec)
                << "  frozen = " << label(nFrozen)
                << "  thetaMean = " << (thMean < 0 ? -1 : thMean/contactDeg)
                << " deg";
            if (contactPinWire)
            {
                Info<< "  wire = " << label(nWire)
                    << "  wirePinned = " << label(nWirePin)
                    << "  zWire = " << (zWireMax > -0.5*GREAT ? zWireMax : -1)
                    << " m";
            }
            Info<< endl;

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
                       << "xMin[m] xMax[m] yMin[m] yMax[m] "
                       << "nWire nWirePinned nWireAdvancing nWireReceding "
                       << "zWireMax[m] zWireMin[m] thetaMeanWire[deg]\n"
                       << "# contactState: 1 substrate hysteresis, 2 substrate "
                       << "solidification, 3 substrate advancing, 4 substrate receding, "
                       << "5 wire hysteresis, 6 wire solidification, "
                       << "7 wire advancing, 8 wire receding\n"
                       << "# contactSupport: 1 substrate or deposit, 2 unmelted wire\n"
                       << "# nMolten..yMax are the substrate/deposit line. "
                       << "nWire..thetaMeanWire are the unmelted-wire line "
                       << "(0 / -1 when pinWire is off or the line is absent).\n"
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
                   << (yMax > -GREAT/2 ? yMax : 0) << ' '
                   << label(nWire) << ' ' << label(nWirePin) << ' '
                   << label(nWireAdv) << ' ' << label(nWireRec) << ' '
                   << (zWireMax > -0.5*GREAT ? zWireMax : -1) << ' '
                   << (zWireMin < 0.5*GREAT ? zWireMin : -1) << ' '
                   << (thWireMean < 0 ? -1 : thWireMean/contactDeg) << '\n';
            }
        }
    }
}
