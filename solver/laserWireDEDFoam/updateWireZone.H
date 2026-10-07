// Target velocity of the solid metal (Carman-Kozeny sink):
//   wire zone (cylinder about the wire axis, above zoneMinHeight/zoneMinZ):
//       wire feed velocity (ramped from tFeedStart over tFeedRamp)
//       x stall factor of the optional stubbing model (createStubbing.H)
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
        }
        if (stubEnabled) stubFeedFac = feedFac*stubStallFac;
    }

    forAll(Us, celli)
    {
        const vector d = C[celli] - wireOrigin;
        const scalar s = (d & wireUp);
        const scalar r = mag(d - s*wireUp);
        if
        (
            r <= wireZoneRadiusFactor*wireRadius
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
                Us[celli] = stubFeedFac*wireFeedVelocity;
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
