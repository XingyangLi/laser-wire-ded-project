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
//   bk*          = wire buckling (stubbing/buckling; zeros when off):
//                  buckled (post-critical this step), bkStall (compression S),
//                  bkCritical (S_cr), bkLength (free column L), bkAmp / bkAmpTarget
//                  (commanded bow), bkLatSpeed (dA/dt), bkTipS (pinned end),
//                  bkEvents, bkMaxAmp, and MEASURED from the solid never-molten
//                  wire (volume-weighted centreline in nBins axial bins):
//                  bkTipOffB / bkTipOffT = lowest bin offset from the original axis
//                  along e_b / along e_t = axis x e_b (vertical wire: y / -x),
//                  bkBow = largest |offset along e_b| from the tip->inlet chord,
//                  bkBowXi = where (0 tip, 1 inlet), bkSeverity = bkBow / wire
//                  diameter, bkDirX/Y/Z = e_b (preferred plane = axis + e_b)
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

        // --- measured wire centreline (buckling)
        scalar bkTipOffB = 0, bkTipOffT = 0, bkBow = 0, bkBowXi = 0;
        if (bkL > SMALL && bkSTip > -0.5*GREAT)
        {
            const label nb = bkNBins;
            const scalar xi0 = -0.1;                  // bins from just below the contact
            scalarList bw(nb, Zero), bb(nb, Zero), bt(nb, Zero);
            const scalar Rm =
                wireZoneRadiusFactor*wireRadius + bkMaxAmpD*2*wireRadius + wireRadius;
            forAll(C, c)
            {
                if (alpha1[c] < 0.5 || liquidFraction[c] >= stubWireFlMax) continue;
                const vector d = C[c] - wireOrigin;
                const scalar s = (d & wireUp);
                const vector dl = d - s*wireUp;
                if (mag(dl) > Rm) continue;
                const scalar xi = (s - bkSTip)/bkL;
                if (xi < xi0 || xi > 1.0) continue;
                if (!lwdUnmeltedWire(c)) continue;
                const label b = min(max(label((xi - xi0)/(1.0 - xi0)*nb), label(0)), nb - 1);
                const scalar wc = alpha1[c]*V[c];
                bw[b] += wc;
                bb[b] += wc*(dl & bkDir);
                bt[b] += wc*(dl & bkDir2);
            }
            Pstream::listCombineReduce(bw, plusEqOp<scalar>());
            Pstream::listCombineReduce(bb, plusEqOp<scalar>());
            Pstream::listCombineReduce(bt, plusEqOp<scalar>());
            label bTip = -1;
            forAll(bw, b) { if (bw[b] > VSMALL) { bTip = b; break; } }
            if (bTip >= 0)
            {
                bkTipOffB = bb[bTip]/bw[bTip];
                bkTipOffT = bt[bTip]/bw[bTip];
                const scalar xiTip = xi0 + (bTip + 0.5)*(1.0 - xi0)/nb;
                forAll(bw, b)
                {
                    if (bw[b] <= VSMALL) continue;
                    const scalar xi = xi0 + (b + 0.5)*(1.0 - xi0)/nb;
                    const scalar w = (xi >= 1.0 || xiTip >= 1.0)
                        ? 0.0 : max(min((1.0 - xi)/(1.0 - xiTip), 1.0), 0.0);
                    const scalar dev = bb[b]/bw[b] - w*bkTipOffB;   // from the chord
                    if (mag(dev) > mag(bkBow)) { bkBow = dev; bkBowXi = xi; }
                }
            }
        }
        const scalar bkSeverity = mag(bkBow)/max(2*wireRadius, VSMALL);
        if (bkEnabled)
        {
            Info<< "WireBuckling: " << (bkOn ? "BUCKLED" : "-") << " S " << bkS*1e3
                << " mm (crit " << bkCrit*1e3 << ", L " << bkL*1e3 << ") A "
                << bkA*1e3 << " mm (target " << bkATarget*1e3 << ", dA/dt "
                << bkAdot*1e3 << " mm/s) measured bow " << bkBow*1e3 << " mm at xi "
                << bkBowXi << ", tip offset b/t " << bkTipOffB*1e3 << "/"
                << bkTipOffT*1e3 << " mm" << endl;
        }

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
            // an older file (other column set): start a new header block
            static bool hdrChecked = false;
            bool writeHdr = isNew;
            if (!isNew && !hdrChecked)
            {
                std::ifstream is(fn.c_str());
                std::string line, lastHdr;
                while (std::getline(is, line))
                {
                    if (!line.empty() && line[0] == '#') lastHdr = line;
                }
                writeHdr = (lastHdr.find(" bkSeverity") == std::string::npos);
            }
            hdrChecked = true;
            std::ofstream os(fn.c_str(), std::ios::app);
            if (writeHdr)
            {
                os << "# time[s] stubbed stallFactor feedFactor nContactCells contactArea[m2] "
                   << "supportZ[m] nStubEvents contactTime[s] firstStubTime[s] "
                   << "stalledLength[m] stalledVolume[m3] fedLength[m] fedVolume[m3] "
                   << "inletMetalArea[m2] tipZ[m] hangMinZ[m] surfUnderZ[m] gapMin[m] "
                   << "bridged nBridgedCols nFootCols bridgedArea[m2] ballVolume[m3] "
                   << "ballDiamEq[m] ballWidthX[m] ballWidthY[m] ballHeight[m] "
                   << "ballBottomZ[m] ballTopZ[m] deltaT[s] "
                   << "buckled bkStall[m] bkCritical[m] bkLength[m] bkAmp[m] bkAmpTarget[m] "
                   << "bkLatSpeed[m/s] bkTipS[m] bkEvents bkMaxAmp[m] bkTipOffB[m] "
                   << "bkTipOffT[m] bkBow[m] bkBowXi bkSeverity bkDirX bkDirY bkDirZ\n";
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
               << runTime.deltaTValue() << ' '
               << (bkOn ? 1 : 0) << ' ' << bkS << ' ' << bkCrit << ' ' << bkL << ' '
               << bkA << ' ' << bkATarget << ' ' << bkAdot << ' '
               << (bkSTip > -0.5*GREAT ? bkSTip : 0.0) << ' ' << bkNEvents << ' '
               << bkMaxA << ' ' << bkTipOffB << ' ' << bkTipOffT << ' ' << bkBow << ' '
               << bkBowXi << ' ' << bkSeverity << ' '
               << bkDir.x() << ' ' << bkDir.y() << ' ' << bkDir.z() << '\n';
        }
    }
}
