// Melt-pool, bead and dilution statistics -> postProcessing/meltPool/meltPool.dat
// Bead probe: a y-z slab of cells at x = min(pool tail + beadProbeOffset, beadProbeX)
// (i.e. just behind the solidification front, where the track is solid).
{
    const dictionary& stDictMP = meltProperties.subOrEmptyDict("statistics");
    const label every = stDictMP.getOrDefault<label>("interval", 10);
    const bool symY = stDictMP.getOrDefault<bool>("symmetryY", true);
    const scalar zSub = stDictMP.getOrDefault<scalar>("substrateTop", 0.0);
    const scalar xProbeMax = stDictMP.getOrDefault<scalar>("beadProbeX", 0.0);
    const bool probeAuto = stDictMP.getOrDefault<bool>("beadProbeAuto", true);
    const scalar probeOff = stDictMP.getOrDefault<scalar>("beadProbeOffset", 3e-4);
    const scalar hThr = stDictMP.getOrDefault<scalar>("beadHeightThreshold", 2e-5);
    const scalar powFac = stDictMP.getOrDefault<scalar>("powerFactor", symY ? 2.0 : 1.0);

    if (runTime.timeIndex() % max(every, 1) == 0 || runTime.writeTime())
    {
        const vectorField& C = mesh.C().primitiveField();
        const scalarField& V = mesh.V();
        scalar xmin = GREAT, xmax = -GREAT, ymin = GREAT, ymax = -GREAT;
        scalar zmin = GREAT, zmax = -GREAT, Tmx = 0, vol = 0, metalVol = 0;
        scalar tipZ = GREAT;
        forAll(C, i)
        {
            const scalar a = alpha1[i];
            metalVol += a*V[i];
            if (a > 0.5) Tmx = max(Tmx, T[i]);
            if (a > 0.5 && liquidFraction[i] > 0.5)
            {
                xmin = min(xmin, C[i].x()); xmax = max(xmax, C[i].x());
                ymin = min(ymin, C[i].y()); ymax = max(ymax, C[i].y());
                zmin = min(zmin, C[i].z()); zmax = max(zmax, C[i].z());
            }
            if (a > 0.5 && liquidFraction[i] < 0.5 && inWireZone[i])
            {
                tipZ = min(tipZ, C[i].z());
            }
            vol += a*liquidFraction[i]*V[i];
        }
        reduce(xmin, minOp<scalar>()); reduce(xmax, maxOp<scalar>());
        reduce(ymin, minOp<scalar>()); reduce(ymax, maxOp<scalar>());
        reduce(zmin, minOp<scalar>()); reduce(zmax, maxOp<scalar>());
        reduce(Tmx, maxOp<scalar>()); reduce(tipZ, minOp<scalar>());
        reduce(vol, sumOp<scalar>()); reduce(metalVol, sumOp<scalar>());
        const bool hasPool = (xmax >= xmin);

        scalar xProbe = xProbeMax;
        if (probeAuto && hasPool) xProbe = min(xmax + probeOff, xProbeMax);

        // nearest column x to the probe
        scalar dmin = GREAT;
        forAll(colX, ci) dmin = min(dmin, mag(colX[ci] - xProbe));
        reduce(dmin, minOp<scalar>());
        scalar xq = GREAT;
        forAll(colX, ci) if (mag(colX[ci] - xProbe) <= dmin + 1e-12) xq = min(xq, colX[ci]);
        reduce(xq, minOp<scalar>());

        scalar hBead = -GREAT, yBead = 0, yMinBead = GREAT;
        scalar Vfused = 0, VfusedSub = 0, VfusedWire = 0, zFusedMin = GREAT, Vabove = 0;
        forAll(colX, ci)
        {
            if (mag(colX[ci] - xq) > 1e-9) continue;
            const scalar h = zSurface[colCells[ci][0]] - zSub;
            hBead = max(hBead, h);
            if (h > hThr) { yBead = max(yBead, colY[ci]); yMinBead = min(yMinBead, colY[ci]); }
            for (const label c : colCells[ci])
            {
                const scalar am = max(min(alpha1[c], 1.0), 0.0);
                if (C[c].z() > zSub) Vabove += am*V[c];
                if (meltHistory[c] > 0.5 && am > 0.5)
                {
                    Vfused += am*V[c];
                    VfusedWire += am*cWire[c]*V[c];
                    if (C[c].z() < zSub) VfusedSub += am*V[c];
                    zFusedMin = min(zFusedMin, C[c].z());
                }
            }
        }
        reduce(hBead, maxOp<scalar>()); reduce(yBead, maxOp<scalar>());
        reduce(yMinBead, minOp<scalar>());
        reduce(Vfused, sumOp<scalar>()); reduce(VfusedSub, sumOp<scalar>());
        reduce(VfusedWire, sumOp<scalar>()); reduce(zFusedMin, minOp<scalar>());
        reduce(Vabove, sumOp<scalar>());
        // slab thickness of that column row: area = volume / dx_col
        scalar dxSlab = GREAT;
        forAll(colX, ci)
        {
            if (mag(colX[ci] - xq) <= 1e-9 && colCells[ci].size())
            {
                const label c0 = colCells[ci][0];
                dxSlab = min(dxSlab, V[c0]/colArea[ci]*0 + Foam::sqrt(colArea[ci]));
            }
        }
        // exact slab width from cell bounds
        {
            scalar xlo = GREAT, xhi = -GREAT;
            const labelListList& cPts = mesh.cellPoints();
            forAll(colX, ci)
            {
                if (mag(colX[ci] - xq) > 1e-9) continue;
                for (const label pI : cPts[colCells[ci][0]])
                {
                    xlo = min(xlo, mesh.points()[pI].x());
                    xhi = max(xhi, mesh.points()[pI].x());
                }
                break;
            }
            reduce(xlo, minOp<scalar>()); reduce(xhi, maxOp<scalar>());
            if (xhi > xlo) dxSlab = xhi - xlo;
        }
        const scalar areaFac = (symY ? 2.0 : 1.0)/max(dxSlab, SMALL);

        const scalar L = hasPool ? xmax - xmin : 0;
        const scalar W = hasPool ? (symY ? 2*ymax : ymax - ymin) : 0;
        const scalar D = hasPool ? max(zSub - zmin, 0.0) : 0;
        const scalar Ht = hasPool ? zmax - zSub : 0;
        const scalar Wb = (yMinBead < GREAT) ? (symY ? 2*yBead : yBead - yMinBead) : 0;
        const scalar Abead = Vabove*areaFac;                 // reinforcement area
        const scalar Afused = Vfused*areaFac;
        const scalar Asub = VfusedSub*areaFac;               // melted substrate area
        const scalar dilGeom = (Afused > SMALL) ? Asub/Afused : 0;
        const scalar dilComp = (Vfused > SMALL) ? 1 - VfusedWire/Vfused : 0;
        const scalar pen = (zFusedMin < GREAT) ? max(zSub - zFusedMin, 0.0) : 0;

        Info<< "MeltPool: L = " << L*1e3 << " mm  W = " << W*1e3
            << " mm  D = " << D*1e3 << " mm  Tmax = " << Tmx
            << " K | bead @x=" << xq*1e3 << "mm: h = " << hBead*1e3 << " w = " << Wb*1e3
            << " mm A = " << Abead*1e6 << " mm2, penetration = " << pen*1e3
            << " mm, dilution(geom/comp) = " << dilGeom << "/" << dilComp << endl;

        if (Pstream::master())
        {
            const fileName dir(runTime.globalPath()/"postProcessing"/"meltPool");
            mkDir(dir);
            const fileName fn(dir/"meltPool.dat");
            const bool isNew = !isFile(fn);
            std::ofstream os(fn.c_str(), std::ios::app);
            if (isNew)
            {
                os << "# time[s] poolLength[m] poolWidth[m] poolDepth[m] poolTopZ[m] "
                   << "Tmax[K] moltenVolume[m3] metalVolume[m3] laserIncident[W] "
                   << "laserAbsorbed[W] surfaceLoss[W] wireTipZ[m] beadHeight[m] "
                   << "beadWidth[m] deltaT[s] probeX[m] beadArea[m2] fusedArea[m2] "
                   << "penetration[m] dilutionGeom[-] dilutionComp[-] poolTailX[m] poolFrontX[m]\n";
            }
            os.precision(8);
            os << runTime.value() << ' ' << L << ' ' << W << ' ' << D << ' ' << Ht << ' '
               << Tmx << ' ' << vol*powFac << ' ' << metalVol*powFac << ' '
               << laserIncidentPower*powFac << ' ' << laserAbsorbedPower*powFac << ' '
               << surfaceLossPower*powFac << ' ' << (tipZ < GREAT ? tipZ : -1) << ' '
               << hBead << ' ' << Wb << ' ' << runTime.deltaTValue() << ' '
               << xq << ' ' << Abead << ' ' << Afused << ' ' << pen << ' '
               << dilGeom << ' ' << dilComp << ' ' << (hasPool ? xmax : 0) << ' '
               << (hasPool ? xmin : 0) << '\n';
        }
    }
}
