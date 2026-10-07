// Wire-transfer / stubbing statistics -> postProcessing/wireTransfer/wireTransfer.dat
// (only when meltProperties has a stubbing{} dict; see createStubbing.H)
//
// Column scan in the columns within diagRadius (horizontal) of the wire axis
// (vertical / coaxial wire assumed for the horizontal distance):
//   bottom block = metal contiguous from the domain bottom (substrate + pool +
//                  deposit + anything touching them)
//   hanging      = metal above a gas gap (wire, molten ball, droplet in flight)
//   tipZ         = lowest solid, never-molten wire cell in the wire zone
//   bridged      = a column in the wire footprint whose bottom block reaches the
//                  solid wire (contains never-molten wire metal or reaches tipZ):
//                  wire (solid or its molten tip) connected to the substrate
//   gapMin       = smallest gas gap between hanging metal and the bottom block
//                  below it in the wire footprint (0 when bridged)
//   ball*        = hanging LIQUID metal (fl > 0.5): volume, equivalent sphere
//                  diameter, bounding box widths/height, bottom/top z
if (stubDictFound && stubStats)
{
    const dictionary& stDictW = meltProperties.subOrEmptyDict("statistics");
    const label everyW = stDictW.getOrDefault<label>("interval", 10);
    if (runTime.timeIndex() % max(everyW, 1) == 0 || runTime.writeTime())
    {
        const vectorField& C = mesh.C().primitiveField();
        const scalarField& V = mesh.V();

        // lowest solid never-molten wire cell (geometric wire zone, any z)
        scalar tipZ = GREAT;
        forAll(C, c)
        {
            if (alpha1[c] < 0.5 || liquidFraction[c] >= stubWireFlMax) continue;
            const vector d = C[c] - wireOrigin;
            const scalar s = (d & wireUp);
            const scalar r = mag(d - s*wireUp);
            if (r <= wireZoneRadiusFactor*wireRadius && lwdUnmeltedWire(c))
            {
                tipZ = min(tipZ, C[c].z());
            }
        }
        reduce(tipZ, minOp<scalar>());

        const scalar rFoot = wireZoneRadiusFactor*wireRadius;
        label nFootCols = 0, nBridged = 0;
        scalar bridgedArea = 0, gapMin = GREAT, hangMinZ = GREAT, surfUnderZ = -GREAT;
        scalar Vball = 0, bx0 = GREAT, bx1 = -GREAT, by0 = GREAT, by1 = -GREAT;
        scalar bz0 = GREAT, bz1 = -GREAT, dzBall = 0;
        forAll(colCells, ci)
        {
            const scalar rh = Foam::sqrt
            (
                sqr(colX[ci] - wireOrigin.x()) + sqr(colY[ci] - wireOrigin.y())
            );
            if (rh > stubDiagRadius) continue;
            const labelList& cl = colCells[ci];
            const label n = cl.size();
            if (!n) continue;
            const scalar dzc = V[cl[0]]/max(colArea[ci], VSMALL);   // cell height
            // bottom block
            label k = n - 1;
            scalar zBotTop = -GREAT;
            bool hasWire = false;
            while (k >= 0 && alpha1[cl[k]] > 0.5)
            {
                const label c = cl[k];
                zBotTop = C[c].z();
                if (liquidFraction[c] < stubWireFlMax && lwdUnmeltedWire(c)) hasWire = true;
                --k;
            }
            // hanging metal above the first gas gap
            scalar zHang = GREAT;
            for (; k >= 0; --k)
            {
                const label c = cl[k];
                if (alpha1[c] <= 0.5) continue;
                if (zHang == GREAT) zHang = C[c].z();
                if (liquidFraction[c] > 0.5)
                {
                    Vball += alpha1[c]*V[c];
                    bx0 = min(bx0, C[c].x()); bx1 = max(bx1, C[c].x());
                    by0 = min(by0, C[c].y()); by1 = max(by1, C[c].y());
                    bz0 = min(bz0, C[c].z()); bz1 = max(bz1, C[c].z());
                    dzBall = max(dzBall, V[c]/max(colArea[ci], VSMALL));
                }
            }
            if (rh <= rFoot)
            {
                ++nFootCols;
                const bool bridged =
                    hasWire || (tipZ < GREAT && zBotTop >= tipZ - 1.5*dzc);
                if (bridged)
                {
                    ++nBridged;
                    bridgedArea += colArea[ci];
                }
                if (zHang < GREAT)
                {
                    hangMinZ = min(hangMinZ, zHang);
                    if (zBotTop > -GREAT)
                    {
                        const scalar g = max(zHang - zBotTop - dzc, 0.0);
                        if (g < gapMin) { gapMin = g; }
                        surfUnderZ = max(surfUnderZ, zBotTop);
                    }
                }
            }
        }
        reduce(nFootCols, sumOp<label>()); reduce(nBridged, sumOp<label>());
        reduce(bridgedArea, sumOp<scalar>()); reduce(gapMin, minOp<scalar>());
        reduce(hangMinZ, minOp<scalar>()); reduce(surfUnderZ, maxOp<scalar>());
        reduce(Vball, sumOp<scalar>());
        reduce(bx0, minOp<scalar>()); reduce(bx1, maxOp<scalar>());
        reduce(by0, minOp<scalar>()); reduce(by1, maxOp<scalar>());
        reduce(bz0, minOp<scalar>()); reduce(bz1, maxOp<scalar>());
        reduce(dzBall, maxOp<scalar>());
        if (nBridged > 0) gapMin = 0;
        const bool hasBall = (bx1 >= bx0);
        const scalar dEq = Foam::cbrt(6.0*Vball/constant::mathematical::pi);
        // cell width ~ sqrt(column area) of the finest columns: add one cell to extents
        scalar dxc = GREAT;
        forAll(colArea, ci) dxc = min(dxc, Foam::sqrt(colArea[ci]));
        reduce(dxc, minOp<scalar>());
        const scalar ballWx = hasBall ? bx1 - bx0 + dxc : 0;
        const scalar ballWy = hasBall ? by1 - by0 + dxc : 0;
        const scalar ballH  = hasBall ? bz1 - bz0 + dzBall : 0;

        Info<< "WireTransfer: tip z " << (tipZ < GREAT ? tipZ*1e3 : -1) << " mm, "
            << (nBridged > 0 ? "BRIDGED" : "free") << " (" << nBridged << "/" << nFootCols
            << " cols), gap " << (gapMin < GREAT ? gapMin*1e3 : -1) << " mm, ball V "
            << Vball*1e9 << " mm3 d_eq " << dEq*1e3 << " mm | stub "
            << (stubWasOn ? "ON" : "off") << " stall " << stubStallFac << " events "
            << stubNEvents << " contact " << stubContactTime << " s stalled "
            << stubStalledVol*1e9 << " mm3" << endl;

        if (Pstream::master())
        {
            const fileName dir(runTime.globalPath()/"postProcessing"/"wireTransfer");
            mkDir(dir);
            const fileName fn(dir/"wireTransfer.dat");
            const bool isNew = !isFile(fn);
            std::ofstream os(fn.c_str(), std::ios::app);
            if (isNew)
            {
                os << "# time[s] stubbed stallFactor feedFactor nContactCells contactArea[m2] "
                   << "supportZ[m] nStubEvents contactTime[s] firstStubTime[s] "
                   << "stalledLength[m] stalledVolume[m3] fedLength[m] fedVolume[m3] "
                   << "inletMetalArea[m2] tipZ[m] hangMinZ[m] surfUnderZ[m] gapMin[m] "
                   << "bridged nBridgedCols nFootCols bridgedArea[m2] ballVolume[m3] "
                   << "ballDiamEq[m] ballWidthX[m] ballWidthY[m] ballHeight[m] "
                   << "ballBottomZ[m] ballTopZ[m] deltaT[s]\n";
            }
            os.precision(8);
            os << runTime.value() << ' ' << (stubWasOn ? 1 : 0) << ' ' << stubStallFac << ' '
               << stubFeedFac << ' ' << stubNCells << ' ' << stubArea << ' '
               << (stubSupZ > -GREAT ? stubSupZ : -1) << ' ' << stubNEvents << ' '
               << stubContactTime << ' ' << stubFirstTime << ' '
               << stubStalledLen << ' ' << stubStalledVol << ' ' << stubFedLen << ' '
               << stubFedVol << ' ' << stubInletMetalArea << ' '
               << (tipZ < GREAT ? tipZ : -1) << ' ' << (hangMinZ < GREAT ? hangMinZ : -1) << ' '
               << (surfUnderZ > -GREAT ? surfUnderZ : -1) << ' '
               << (gapMin < GREAT ? gapMin : -1) << ' ' << (nBridged > 0 ? 1 : 0) << ' '
               << nBridged << ' ' << nFootCols << ' ' << bridgedArea << ' '
               << Vball << ' ' << dEq << ' ' << ballWx << ' ' << ballWy << ' ' << ballH << ' '
               << (hasBall ? bz0 : -1) << ' ' << (hasBall ? bz1 : -1) << ' '
               << runTime.deltaTValue() << '\n';
        }
    }
}
