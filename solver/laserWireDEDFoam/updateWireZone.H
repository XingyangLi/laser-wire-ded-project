// Target velocity of the solid metal (Carman-Kozeny sink):
//   wire zone (cylinder about the wire axis, above zoneMinHeight/zoneMinZ):
//       wire feed velocity (ramped from tFeedStart over tFeedRamp)
//       x stall factor of the optional stubbing model (createStubbing.H)
//       + lateral bow velocity of the optional buckling model (stubbing/buckling):
//         the wire zone then follows the bent axis
//   elsewhere: solidVelocity (substrate moving under the fixed laser)
{
    const scalar tNow = runTime.value();
    scalar feedFac = 1.0;
    if (tNow < wireFeedStart) feedFac = 0.0;
    else if (wireFeedRamp > SMALL) feedFac = min((tNow - wireFeedStart)/wireFeedRamp, 1.0);

    const volVectorField& C = mesh.C();
    vectorField& Us = Usolid.primitiveFieldRef();

    // multi-component option 'wireStubbing': a never-molten wire cannot be
    // driven into solid substrate/deposit. Per column, the support height is
    // the top of the contiguous solid, non-wire metal from the bottom; wire-zone
    // cells less than stubContactDist above it move with the substrate (the
    // stub is dragged along with the part instead of penetrating it).
    scalarField zSupport(colCells.size(), -GREAT);
    if (multiComp && wireStubbing)
    {
        forAll(colCells, ci)
        {
            const labelList& cl = colCells[ci];
            for (label k = cl.size() - 1; k >= 0; --k)
            {
                const label c = cl[k];
                scalar uSum = 0;
                forAll(uComp, i) uSum += uComp[i][c];
                if (alpha1[c] > 0.5 && liquidFraction[c] < 0.5 && uSum < 0.5)
                {
                    zSupport[ci] = C[c].z();
                }
                else
                {
                    break;
                }
            }
            // optional floor: the original plate surface always supports
            if (stubFloorZ > -0.5*GREAT)
            {
                zSupport[ci] = max(zSupport[ci], stubFloorZ);
            }
        }
    }

    // --- rigid-wire stubbing model (meltProperties/stubbing): detect solid,
    //     never-molten wire resting on solid support (substrate / deposit /
    //     solid pool bottom), then stall the feed of the whole solid wire.
    stubFeedFac = feedFac;
    if (stubDictFound)
    {
        stubContact = false;
        stubNCells = 0;
        stubArea = 0;
        stubSupZ = -GREAT;
        stubSTip = GREAT;
        forAll(colCells, ci)
        {
            const labelList& cl = colCells[ci];
            scalar zs = -GREAT;
            label kTop = cl.size();          // index (top->bottom order) of the support top
            for (label k = cl.size() - 1; k >= 0; --k)
            {
                const label c = cl[k];
                if
                (
                    alpha1[c] > 0.5 && liquidFraction[c] < stubSupportFlMax
                 && !lwdUnmeltedWire(c)
                )
                {
                    zs = C[c].z();
                    kTop = k;
                }
                else
                {
                    break;
                }
            }
            if (stubUseFloor && stubFloorZ > -0.5*GREAT && stubFloorZ > zs)
            {
                zs = stubFloorZ;
                kTop = cl.size();
                for (label k = cl.size() - 1; k >= 0; --k)
                {
                    if (C[cl[k]].z() <= zs) kTop = k; else break;
                }
            }
            if (zs < -0.5*GREAT) continue;
            bool colHit = false;
            for (label k = kTop - 1; k >= 0; --k)
            {
                const label c = cl[k];
                const scalar z = C[c].z();
                if (z <= zs) continue;
                if (z > zs + stubContactDistNew) break;
                const vector d = C[c] - wireOrigin;
                const scalar s = (d & wireUp);
                const scalar r = mag(d - s*wireUp);
                if
                (
                    r <= wireZoneRadiusFactor*wireRadius && s >= wireZoneMinHeight
                 && alpha1[c] > 0.5 && liquidFraction[c] < stubWireFlMax
                 && lwdUnmeltedWire(c)
                )
                {
                    // contiguous solid unmelted wire above (not a loose fragment)
                    scalar len = 0;
                    for (label j = k; j >= 0; --j)
                    {
                        const label cj = cl[j];
                        if
                        (
                            alpha1[cj] > 0.5 && liquidFraction[cj] < stubWireFlMax
                         && lwdUnmeltedWire(cj)
                        )
                        {
                            len = C[cj].z() - z;
                            if (len >= stubMinLength) break;
                        }
                        else
                        {
                            break;
                        }
                    }
                    if (len >= stubMinLength)
                    {
                        stubContact[c] = true;
                        stubSTip = min(stubSTip, s);
                        ++stubNCells;
                        colHit = true;
                    }
                }
            }
            if (colHit)
            {
                stubArea += colArea[ci];
                stubSupZ = max(stubSupZ, zs);
            }
        }
        reduce(stubNCells, sumOp<label>());
        reduce(stubArea, sumOp<scalar>());
        reduce(stubSupZ, maxOp<scalar>());
        reduce(stubSTip, minOp<scalar>());

        stubInletMetalArea = 0;
        if (stubInletPatch >= 0)
        {
            stubInletMetalArea = gSum
            (
                max(min(alpha1.boundaryField()[stubInletPatch], scalar(1)), scalar(0))
               *mesh.magSf().boundaryField()[stubInletPatch]
            );
        }

        const bool on = (stubNCells >= max(stubMinCells, label(1)));
        if (!stubStartup)
        {
            const scalar dt = runTime.deltaTValue();
            if (stubEnabled)
            {
                const scalar target = on ? 0.0 : 1.0;
                stubStallFac =
                    (stubResponseTime > SMALL)
                  ? target + (stubStallFac - target)*Foam::exp(-dt/stubResponseTime)
                  : target;
            }
            else
            {
                stubStallFac = 1.0;
            }
            if (on && !stubWasOn)
            {
                stubNEvents += 1;
                stubEventStart = tNow;
                if (stubFirstTime < 0) stubFirstTime = tNow;
                Info<< "Stubbing: solid wire on solid support at t = " << tNow
                    << " s (" << stubNCells << " cells, area " << stubArea*1e6
                    << " mm2, support z " << stubSupZ*1e3 << " mm)"
                    << (stubEnabled ? " -> feed stalls" : " [diagnostics only]") << endl;
            }
            else if (!on && stubWasOn)
            {
                Info<< "Stubbing: contact released at t = " << tNow << " s after "
                    << tNow - max(stubEventStart, 0.0) << " s" << endl;
            }
            if (on) stubContactTime += dt;
            const scalar vf = mag(wireFeedVelocity);
            stubStalledLen += dt*feedFac*(1 - stubStallFac)*vf;
            stubStalledVol += dt*feedFac*(1 - stubStallFac)*vf*stubInletMetalArea;
            stubFedLen += dt*feedFac*stubStallFac*vf;
            stubFedVol += dt*feedFac*stubStallFac*vf*stubInletMetalArea;
            stubWasOn = on;

            // --- buckling of the free wire column under the stall
            //     (pinned end / free length also tracked with buckling off: diagnostics)
            if (on && stubSTip < 0.5*GREAT) bkSTip = stubSTip;
            bkL = (bkSTip > -0.5*GREAT) ? max(bkSIn - bkSTip, 0.0) : 0.0;
            if (bkEnabled)
            {
                bkCrit =
                    (bkCritUser > 0)
                  ? bkCritUser
                  : (
                        (bkL > SMALL)
                      ? sqr(constant::mathematical::pi*bkGyr)*bkPathFactor/(sqr(bkK)*bkL)
                      : 0.0
                    );
                if (on)
                {
                    bkS += dt*feedFac*(1 - stubStallFac)*vf;
                }
                else if (bkSpringBack)
                {
                    bkS *= (bkRelease > SMALL) ? Foam::exp(-dt/bkRelease) : 0.0;
                }
                const scalar Amax =
                    (bkL >= bkMinLength)
                  ? min(bkMaxAmpD*2*wireRadius, bkMaxSlope*bkL)
                  : 0.0;
                const scalar excess = bkAbsorb*max(bkS - bkCrit, 0.0);
                bkATarget = min(Foam::sqrt(excess*bkL/max(bkArc, SMALL)), Amax);
                if (!on && !bkSpringBack) bkATarget = bkA;     // plastic: stays bent
                const bool bkWasOn = bkOn;
                bkOn = on && excess > 0 && Amax > 0;
                const scalar dA = bkATarget - bkA;
                scalar rate = dA/max(bkResponse, dt);
                rate = max(min(rate, bkMaxSpeed), -bkMaxSpeed);
                if (mag(rate*dt) > mag(dA)) rate = dA/max(dt, VSMALL);
                bkAdot = rate;
                bkA = max(bkA + rate*dt, 0.0);
                if (bkA < 1e-9 && bkATarget <= 0) { bkA = 0; bkAdot = 0; }
                bkMaxA = max(bkMaxA, bkA);
                if (bkOn && !bkWasOn)
                {
                    bkNEvents += 1;
                    Info<< "Buckling: stalled wire column buckles at t = " << tNow
                        << " s (free length " << bkL*1e3 << " mm, stalled "
                        << bkS*1e3 << " mm > critical " << bkCrit*1e3
                        << " mm, cap " << Amax*1e3 << " mm, e_b " << bkDir << ")"
                        << endl;
                }
                else if (!bkOn && bkWasOn)
                {
                    Info<< "Buckling: compression released at t = " << tNow
                        << " s, amplitude " << bkA*1e3 << " mm"
                        << (bkSpringBack ? " (springs back)" : " (stays bent)") << endl;
                }
            }
        }
        if (stubEnabled) stubFeedFac = feedFac*stubStallFac;
    }
    else
    {
        bkAdot = 0;
    }
    if (stubStartup) bkAdot = 0;
    if (bkSTip > -0.5*GREAT)
    {
        bkL = max(bkSIn - bkSTip, 0.0);
    }
    const bool bkZone = bkEnabled && bkL > SMALL && (bkA > 0 || mag(bkAdot) > 0);
    const scalar bkRz = wireZoneRadiusFactor*wireRadius;

    forAll(Us, celli)
    {
        const vector d = C[celli] - wireOrigin;
        const scalar s = (d & wireUp);
        const scalar r = mag(d - s*wireUp);
        // buckling: mode-shape value and membership of the bent wire zone
        scalar phi = 0;
        bool inBent = false;
        if (bkZone)
        {
            phi = bkShape((s - bkSTip)/bkL);
            if (phi > 0)
            {
                const vector dB = d - bkA*phi*bkDir;
                inBent = (mag(dB - (dB & wireUp)*wireUp) <= bkRz);
            }
        }
        if
        (
            (r <= bkRz || inBent)
         && s >= wireZoneMinHeight
         && C[celli].z() >= wireZoneMinZ
        )
        {
            // multi-component option: metal in the wire zone that has already
            // been molten (re-solidified deposit / pool) moves with the
            // substrate; only never-molten wire metal is driven at the feed rate
            if
            (
                (multiComp && meltedFollowsSubstrate && meltHistory[celli] > 0.5)
             || (multiComp && wireStubbing
                 && C[celli].z() < zSupport[cellColumn[celli]] + stubContactDist)
             || (stubEnabled && stubDragContact && stubContact[celli])
            )
            {
                Us[celli] = solidVelocity;
            }
            else
            {
                Us[celli] = stubFeedFac*wireFeedVelocity + (bkAdot*phi)*bkDir;
            }
            inWireZone[celli] = true;
        }
        else
        {
            Us[celli] = solidVelocity;
            inWireZone[celli] = false;
        }
    }
    Usolid.correctBoundaryConditions();

    // stubbing model: the feeder (wireInlet patch) stalls with the wire
    if (stubEnabled && stubInletControlled)
    {
        U.boundaryFieldRef()[stubInletPatch] == stubFeedFac*wireFeedVelocity;
    }
    stubStartup = false;
}
