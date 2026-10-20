// Enclosed-gas porosity: classify, lock once the shell freezes, quantify.
// See createPorosity.H. Off -> the VOF field is left untouched.
{
    if (porosityEnabled)
    {
        const vectorField& C = mesh.C().primitiveField();
        const scalarField& V = mesh.V();
        const labelListList& cCells = mesh.cellCells();
        const label nCells = mesh.nCells();

        // 0 = metal / ignored, 1 = atmosphere-connected gas, 2 = enclosed gas
        labelList gasState(nCells, 0);
        forAll(alpha1, celli)
        {
            if (alpha1[celli] < porAlphaOpen) gasState[celli] = 2;
        }

        // Gas that touches an open boundary, or that sits in a column with a
        // clear path to the top of the domain, is atmosphere.
        word openNames[5] = {"top", "inletGas", "outlet", "side", "wireInlet"};
        for (const word& nm : openNames)
        {
            const label p = mesh.boundaryMesh().findPatchID(nm);
            if (p < 0) continue;
            const labelUList& fc = mesh.boundary()[p].faceCells();
            forAll(fc, i)
            {
                if (gasState[fc[i]] == 2) gasState[fc[i]] = 1;
            }
        }
        forAll(colCells, ci)
        {
            for (const label c : colCells[ci])
            {
                if (alpha1[c] >= porAlphaOpen) break;
                gasState[c] = 1;
            }
        }

        DynamicList<label> q(nCells/8 + 1);
        forAll(gasState, celli)
        {
            if (gasState[celli] == 1) q.append(celli);
        }
        for (label qi = 0; qi < q.size(); ++qi)
        {
            for (const label n : cCells[q[qi]])
            {
                if (gasState[n] == 2)
                {
                    gasState[n] = 1;
                    q.append(n);
                }
            }
        }
        if (Pstream::parRun())
        {
            label guard = 0;
            while (guard++ < 1000)
            {
                List<label> nei(syncTools::swapBoundaryCellList(mesh, gasState));
                DynamicList<label> nq;
                const label nInt = mesh.nInternalFaces();
                for (label fi = nInt; fi < mesh.nFaces(); ++fi)
                {
                    const label c = mesh.faceOwner()[fi];
                    if (gasState[c] == 2 && nei[fi - nInt] == 1)
                    {
                        gasState[c] = 1;
                        nq.append(c);
                    }
                }
                for (label qi = 0; qi < nq.size(); ++qi)
                {
                    for (const label n : cCells[nq[qi]])
                    {
                        if (gasState[n] == 2)
                        {
                            gasState[n] = 1;
                            nq.append(n);
                        }
                    }
                }
                label changed = nq.size();
                reduce(changed, sumOp<label>());
                if (!changed) break;
            }
        }

        // Local connected components of the enclosed gas, then the minimum
        // id is propagated across processor faces.
        labelList comp(nCells, -1);
        label nLocal = 0;
        forAll(gasState, celli)
        {
            if (gasState[celli] != 2 || comp[celli] >= 0) continue;
            const label id = nLocal++;
            DynamicList<label> cq;
            cq.append(celli);
            comp[celli] = id;
            for (label qi = 0; qi < cq.size(); ++qi)
            {
                for (const label n : cCells[cq[qi]])
                {
                    if (gasState[n] == 2 && comp[n] < 0)
                    {
                        comp[n] = id;
                        cq.append(n);
                    }
                }
            }
        }
        const label idShift = Pstream::myProcNo()*10000000;
        forAll(comp, celli)
        {
            if (comp[celli] >= 0) comp[celli] += idShift;
        }
        if (Pstream::parRun())
        {
            label guard = 0;
            while (guard++ < 1000)
            {
                List<label> nei(syncTools::swapBoundaryCellList(mesh, comp));
                DynamicList<label> cq;
                const label nInt = mesh.nInternalFaces();
                for (label fi = nInt; fi < mesh.nFaces(); ++fi)
                {
                    const label c = mesh.faceOwner()[fi];
                    const label nb = nei[fi - nInt];
                    if (comp[c] >= 0 && nb >= 0 && nb < comp[c])
                    {
                        comp[c] = nb;
                        cq.append(c);
                    }
                }
                for (label qi = 0; qi < cq.size(); ++qi)
                {
                    const label c = cq[qi];
                    for (const label n : cCells[c])
                    {
                        if (comp[n] >= 0 && comp[c] < comp[n])
                        {
                            comp[n] = comp[c];
                            cq.append(n);
                        }
                    }
                }
                label changed = cq.size();
                reduce(changed, sumOp<label>());
                if (!changed) break;
            }
        }

        struct PoreAcc
        {
            scalar nCells = 0;
            scalar vol = 0;
            scalar mx = 0;
            scalar my = 0;
            scalar mz = 0;
            scalar shellFl = 0;
            scalar shellN = 0;
            scalar type = 1;     // 1 entrapment, 2 lack-of-fusion, 3 keyhole
            scalar maxT = 0;
            scalar maxPr = 0;
        };
        std::map<label, PoreAcc> acc;

        forAll(comp, celli)
        {
            if (comp[celli] < 0) continue;
            PoreAcc& p = acc[comp[celli]];
            const scalar pv = (1.0 - max(min(alpha1[celli], scalar(1)), scalar(0)))*V[celli];
            p.nCells += 1;
            p.vol += pv;
            p.mx += C[celli].x()*pv;
            p.my += C[celli].y()*pv;
            p.mz += C[celli].z()*pv;

            scalar maxT = T[celli];
            scalar maxPr = pRecoil[celli];
            bool capped = false;
            bool coverDeposit = false;
            const label ci = cellColumn[celli];
            if (ci >= 0)
            {
                for (const label k : colCells[ci])
                {
                    if (k == celli) break;
                    if (alpha1[k] > 0.50)
                    {
                        capped = true;
                        if
                        (
                            C[k].z() > porZSub + 0.25*Foam::cbrt(max(V[k], SMALL))
                         || meltHistory[k] > 0.50
                        )
                        {
                            coverDeposit = true;
                        }
                    }
                }
            }
            for (const label n : cCells[celli])
            {
                maxT = max(maxT, T[n]);
                maxPr = max(maxPr, pRecoil[n]);
                if (alpha1[n] > 0.50)
                {
                    p.shellFl += liquidFraction[n];
                    p.shellN += 1;
                }
            }
            p.maxT = max(p.maxT, maxT);
            p.maxPr = max(p.maxPr, maxPr);

            const bool nearSub =
                C[celli].z() > porZSub - Foam::cbrt(max(V[celli], SMALL))
             && C[celli].z() < porZSub + porLofBand;
            const bool lof = capped && coverDeposit && nearSub;
            const bool hot =
                maxT > porKeyholeTfrac*porTboil
             || maxPr > porKeyholeRecoil;
            const bool deep = (zSurface[celli] - C[celli].z()) > porKeyholeDepth;
            const bool keyhole = capped && hot && deep;
            scalar ty = 1;
            if (keyhole) ty = 3;
            else if (lof) ty = 2;
            p.type = max(p.type, ty);
        }

        // Pack and share so a pore cut by a processor boundary is one pore.
        // Record: id nCells vol mx my mz shellFl shellN type maxT maxPr
        DynamicList<scalar> packed;
        for (const auto& kv : acc)
        {
            const PoreAcc& p = kv.second;
            packed.append(scalar(kv.first));
            packed.append(p.nCells);
            packed.append(p.vol);
            packed.append(p.mx);
            packed.append(p.my);
            packed.append(p.mz);
            packed.append(p.shellFl);
            packed.append(p.shellN);
            packed.append(p.type);
            packed.append(p.maxT);
            packed.append(p.maxPr);
        }
        List<scalarList> gathered(Pstream::nProcs());
        gathered[Pstream::myProcNo()] = scalarList(packed);
        if (Pstream::parRun())
        {
            Pstream::gatherList(gathered);
            Pstream::scatterList(gathered);
        }

        std::map<label, PoreAcc> global;
        for (const scalarList& part : gathered)
        {
            for (label i = 0; i + 10 < part.size(); i += 11)
            {
                const label id = label(part[i] + 0.5);
                PoreAcc& p = global[id];
                p.nCells += part[i + 1];
                p.vol += part[i + 2];
                p.mx += part[i + 3];
                p.my += part[i + 4];
                p.mz += part[i + 5];
                p.shellFl += part[i + 6];
                p.shellN += part[i + 7];
                p.type = max(p.type, part[i + 8]);
                p.maxT = max(p.maxT, part[i + 9]);
                p.maxPr = max(p.maxPr, part[i + 10]);
            }
        }

        labelHashSet locked;
        std::map<label, scalar> typeOf;
        for (const auto& kv : global)
        {
            const PoreAcc& p = kv.second;
            if (p.nCells < porMinCells || p.vol <= SMALL) continue;
            const scalar shell = (p.shellN > 0) ? p.shellFl/p.shellN : 0;
            typeOf[kv.first] = p.type;
            if (shell < porFlLock) locked.insert(kv.first);
        }

        bool changedAlpha = false;
        forAll(poreMarker, celli)
        {
            poreMarker[celli] = 0;
            poreType[celli] = 0;
            const label id = comp[celli];
            if (id < 0 || !locked.found(id)) continue;
            poreMarker[celli] = 1;
            poreType[celli] = typeOf[id];
            if (alpha1[celli] > porAlphaLock)
            {
                alpha1[celli] = porAlphaLock;
                changedAlpha = true;
            }
        }
        poreMarker.correctBoundaryConditions();
        poreType.correctBoundaryConditions();
        if (changedAlpha)
        {
            alpha1.correctBoundaryConditions();
            alpha2 = 1.0 - alpha1;
            rho == alpha1*rho1 + alpha2*rho2;
            mixture.correct();
        }

        const bool report =
            pimple.finalIter()
         && (
                runTime.timeIndex() % max(porInterval, 1) == 0
             || runTime.writeTime()
            );
        if (report)
        {
            scalar nPore = 0, nLock = 0, nEnt = 0, nLof = 0, nKey = 0;
            scalar vPore = 0, vLock = 0, dSum = 0, dMax = 0;
            DynamicList<scalar> rows;
            for (const auto& kv : global)
            {
                const PoreAcc& p = kv.second;
                if (p.nCells < porMinCells || p.vol <= SMALL) continue;
                const scalar shell = (p.shellN > 0) ? p.shellFl/p.shellN : 0;
                const bool isLocked = shell < porFlLock;
                const scalar dEq =
                    Foam::cbrt(6.0*p.vol/constant::mathematical::pi);
                nPore += 1;
                vPore += p.vol;
                dSum += dEq*p.vol;
                dMax = max(dMax, dEq);
                if (p.type > 2.5) nKey += 1;
                else if (p.type > 1.5) nLof += 1;
                else nEnt += 1;
                if (isLocked)
                {
                    nLock += 1;
                    vLock += p.vol;
                }
                const scalar inv = 1.0/max(p.vol, SMALL);
                // id type locked vol dEq cx cy cz nCells shellFl
                rows.append(scalar(kv.first));
                rows.append(p.type);
                rows.append(isLocked ? 1 : 0);
                rows.append(p.vol);
                rows.append(dEq);
                rows.append(p.mx*inv);
                rows.append(p.my*inv);
                rows.append(p.mz*inv);
                rows.append(p.nCells);
                rows.append(shell);
            }

            // Every rank built the same global map, but only the master writes.
            const scalar metalVol = gSum(max(min(alpha1.primitiveField(), scalar(1)), scalar(0))*V);
            const scalar vf = vPore/max(vPore + metalVol, SMALL);
            const scalar dMean = (vPore > SMALL) ? dSum/vPore : 0;

            Info<< "Porosity: pores = " << label(nPore)
                << "  locked = " << label(nLock)
                << "  entrapment = " << label(nEnt)
                << "  lackOfFusion = " << label(nLof)
                << "  keyhole = " << label(nKey)
                << "  V = " << vPore << " m3"
                << "  vf = " << vf
                << endl;

            if (Pstream::master())
            {
                const fileName dir(runTime.globalPath()/"postProcessing"/"porosity");
                mkDir(dir);
                {
                    const fileName fn(dir/"porosity.dat");
                    const bool isNew = !isFile(fn);
                    std::ofstream os(fn.c_str(), std::ios::app);
                    if (isNew)
                    {
                        os << "# time[s] nPores nLocked nEntrapment nLackOfFusion nKeyhole "
                           << "poreVolume[m3] lockedVolume[m3] metalVolume[m3] "
                           << "volumeFraction[-] eqDiameterMean[m] eqDiameterMax[m]\n"
                           << "# volumeFraction = poreVolume / (poreVolume + metalVolume) "
                           << "on this mesh (half-domain cases are not mirrored)\n"
                           << "# type: 1 gasEntrapment, 2 lackOfFusion, 3 keyhole\n";
                    }
                    os.setf(std::ios::scientific);
                    os.precision(8);
                    os << runTime.value() << ' '
                       << label(nPore) << ' ' << label(nLock) << ' '
                       << label(nEnt) << ' ' << label(nLof) << ' ' << label(nKey) << ' '
                       << vPore << ' ' << vLock << ' ' << metalVol << ' '
                       << vf << ' ' << dMean << ' ' << dMax << '\n';
                }
                {
                    const fileName fn(dir/"pores.dat");
                    const bool isNew = !isFile(fn);
                    std::ofstream os(fn.c_str(), std::ios::app);
                    if (isNew)
                    {
                        os << "# time[s] poreId type locked volume[m3] eqDiameter[m] "
                           << "cx[m] cy[m] cz[m] nCells shellLiquidFraction[-]\n"
                           << "# type: 1 gasEntrapment, 2 lackOfFusion, 3 keyhole; "
                           << "locked = 1 once the metal shell is below flLock\n";
                    }
                    os.setf(std::ios::scientific);
                    os.precision(8);
                    if (rows.empty())
                    {
                        os << "# " << runTime.value() << " none\n";
                    }
                    for (label i = 0; i + 9 < rows.size(); i += 10)
                    {
                        os << runTime.value() << ' '
                           << label(rows[i] + 0.5) << ' '
                           << label(rows[i + 1] + 0.5) << ' '
                           << label(rows[i + 2] + 0.5) << ' '
                           << rows[i + 3] << ' ' << rows[i + 4] << ' '
                           << rows[i + 5] << ' ' << rows[i + 6] << ' ' << rows[i + 7] << ' '
                           << label(rows[i + 8] + 0.5) << ' '
                           << rows[i + 9] << '\n';
                    }
                }
            }
        }
    }
}
