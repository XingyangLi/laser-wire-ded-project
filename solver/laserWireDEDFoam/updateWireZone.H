// Target velocity of the solid metal (Carman-Kozeny sink):
//   wire zone (cylinder about the wire axis, above zoneMinHeight/zoneMinZ):
//       wire feed velocity (ramped from tFeedStart over tFeedRamp)
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
        }
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
            )
            {
                Us[celli] = solidVelocity;
            }
            else
            {
                Us[celli] = feedFac*wireFeedVelocity;
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
}
