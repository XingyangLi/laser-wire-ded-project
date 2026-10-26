// Wire-associated cavity (open or closed). See createPorosity.H / wireCavity.
// gasState is the atmosphere flood from porosity.H: 1 atmosphere, 2 enclosed.
// The cavity is the gas that touches the unmelted wire, stays below the wire
// contact line, and lies in the trailing sector out to cavityOuter. It is
// "closed" only when every cell of that component is enclosed gas; otherwise
// it is the open wake behind the wire. Volumes are not mirrored on a half domain.
{
    cavityMarker == dimensionedScalar(cavityMarker.dimensions(), Zero);

    if (porWireCavity && contactWireZMax > -0.5*GREAT)
    {
        // 0 outside the mask, 1 masked gas, 2 in the wire-touching component
        labelList cav(nCells, 0);
        const vector trail(1, 0, 0);   // substrate moves +x; the wake is +x

        forAll(alpha1, celli)
        {
            if (alpha1[celli] >= porAlphaOpen) continue;
            if (gasState[celli] == 0) continue;
            const scalar z = C[celli].z();
            if (z > contactWireZMax) continue;
            if (z < porZSub - Foam::cbrt(max(V[celli], SMALL))) continue;
            const vector d = C[celli] - wireOrigin;
            const scalar s = d & wireUp;
            const vector rad = d - s*wireUp;
            const scalar r = mag(rad);
            if (r > porCavityOuter) continue;
            if (r > SMALL)
            {
                const scalar along = (rad & trail)/(r + VSMALL);
                if (along < porCavityCos) continue;
            }
            cav[celli] = 1;
        }

        DynamicList<label> q(32);
        forAll(cav, celli)
        {
            if (cav[celli] != 1) continue;
            bool touch = false;
            if (inWireZone[celli] && lwdUnmeltedWire(celli) && alpha1[celli] > 0.5)
            {
                touch = true;
            }
            if (!touch)
            {
                for (const label n : cCells[celli])
                {
                    if (inWireZone[n] && lwdUnmeltedWire(n) && alpha1[n] > 0.5)
                    {
                        touch = true;
                        break;
                    }
                }
            }
            if (!touch) continue;
            cav[celli] = 2;
            q.append(celli);
        }
        for (label qi = 0; qi < q.size(); ++qi)
        {
            for (const label n : cCells[q[qi]])
            {
                if (cav[n] == 1)
                {
                    cav[n] = 2;
                    q.append(n);
                }
            }
        }
        if (Pstream::parRun())
        {
            label guard = 0;
            while (guard++ < 1000)
            {
                List<label> nei;
                lwdSwapCells(cav, nei);
                DynamicList<label> nq;
                const label nInt = mesh.nInternalFaces();
                for (label fi = nInt; fi < mesh.nFaces(); ++fi)
                {
                    const label c = mesh.faceOwner()[fi];
                    if (cav[c] == 1 && nei[fi - nInt] == 2)
                    {
                        cav[c] = 2;
                        nq.append(c);
                    }
                }
                for (label qi = 0; qi < nq.size(); ++qi)
                {
                    for (const label n : cCells[nq[qi]])
                    {
                        if (cav[n] == 1)
                        {
                            cav[n] = 2;
                            nq.append(n);
                        }
                    }
                }
                label changed = nq.size();
                reduce(changed, sumOp<label>());
                if (!changed) break;
            }
        }

        scalar vOpen = 0, vClosed = 0;
        scalar mx = 0, my = 0, mz = 0;
        scalar zMin = GREAT, trailMax = -GREAT;
        scalar nOpen = 0, nClosed = 0;
        forAll(cav, celli)
        {
            if (cav[celli] != 2) continue;
            const scalar pv =
                (1.0 - max(min(alpha1[celli], scalar(1)), scalar(0)))*V[celli];
            const bool closed = (gasState[celli] == 2);
            if (closed)
            {
                vClosed += pv;
                nClosed += 1;
                cavityMarker[celli] = 2;
            }
            else
            {
                vOpen += pv;
                nOpen += 1;
                cavityMarker[celli] = 1;
            }
            mx += C[celli].x()*pv;
            my += C[celli].y()*pv;
            mz += C[celli].z()*pv;
            zMin = min(zMin, C[celli].z());
            const vector d = C[celli] - wireOrigin;
            const scalar s = d & wireUp;
            const vector rad = d - s*wireUp;
            trailMax = max(trailMax, rad & trail);
        }
        cavityMarker.correctBoundaryConditions();

        reduce(vOpen, sumOp<scalar>());
        reduce(vClosed, sumOp<scalar>());
        reduce(mx, sumOp<scalar>());
        reduce(my, sumOp<scalar>());
        reduce(mz, sumOp<scalar>());
        reduce(zMin, minOp<scalar>());
        reduce(trailMax, maxOp<scalar>());
        reduce(nOpen, sumOp<scalar>());
        reduce(nClosed, sumOp<scalar>());

        const bool report =
            pimple.finalIter()
         && (
                runTime.timeIndex() % max(porInterval, 1) == 0
             || runTime.writeTime()
            );
        if (report && Pstream::master())
        {
            const scalar vAll = vOpen + vClosed;
            const scalar inv = 1.0/max(vAll, SMALL);
            // 0 none, 1 open, 2 closed, 3 mixed
            label status = 0;
            if (vOpen > SMALL && vClosed > SMALL) status = 3;
            else if (vClosed > SMALL) status = 2;
            else if (vOpen > SMALL) status = 1;
            const scalar depth =
                (status && zMin < 0.5*GREAT) ? (contactWireZMax - zMin) : 0;
            const scalar length = (trailMax > -0.5*GREAT) ? max(trailMax, scalar(0)) : 0;
            word statusName("none");
            if (status == 1) statusName = "open";
            else if (status == 2) statusName = "closed";
            else if (status == 3) statusName = "mixed";

            Info<< "WireCavity: " << statusName
                << "  V = " << vAll << " m3"
                << "  depth = " << depth << " m"
                << "  zContact = " << contactWireZMax << " m"
                << endl;

            // Pinch-off: the existing enclosed-pore counter (entrapment) rises
            // while a wake is present. Closure: the wire-touching cavity itself
            // goes from open/mixed to fully enclosed. Both are appended to
            // postProcessing/wireCavity/events.dat. Bubble count is nEntrapment.
            {
                static label prevEnt = -1;
                static label prevStatus = -1;
                static label pinchTotal = 0;
                static label closureTotal = 0;
                const label bubbles = max(porEntNow, 0);
                label newBubbles = 0;
                label closedNow = 0;
                if (prevEnt >= 0 && bubbles > prevEnt)
                {
                    newBubbles = bubbles - prevEnt;
                    pinchTotal += newBubbles;
                    Info<< "PinchOff: t = " << runTime.value()
                        << "  newBubbles = " << newBubbles
                        << "  bubbleCount = " << bubbles
                        << "  pinchTotal = " << pinchTotal
                        << "  cavityV = " << vAll << " m3"
                        << endl;
                }
                if ((prevStatus == 1 || prevStatus == 3) && status == 2)
                {
                    closedNow = 1;
                    closureTotal += 1;
                    Info<< "CavityClosure: t = " << runTime.value()
                        << "  cavityV = " << vAll << " m3"
                        << "  bubbleCount = " << bubbles
                        << "  closureTotal = " << closureTotal
                        << endl;
                }
                if (prevEnt >= 0 && (newBubbles || closedNow))
                {
                    const fileName edir(runTime.globalPath()/"postProcessing"/"wireCavity");
                    mkDir(edir);
                    const fileName efn(edir/"events.dat");
                    const bool eNew = !isFile(efn);
                    std::ofstream eos(efn.c_str(), std::ios::app);
                    if (eNew)
                    {
                        eos << "# time[s] event newBubbles bubbleCount "
                            << "pinchTotal closureTotal cavityVolume[m3] status\n"
                            << "# event: pinchoff (entrapment count rose) or "
                            << "closure (open/mixed wire cavity became closed)\n"
                            << "# bubbleCount is nEntrapment from porosity.dat\n";
                    }
                    eos.setf(std::ios::scientific);
                    eos.precision(8);
                    if (newBubbles)
                    {
                        eos << runTime.value() << " pinchoff " << newBubbles << ' '
                            << bubbles << ' ' << pinchTotal << ' ' << closureTotal
                            << ' ' << vAll << ' ' << status << '\n';
                    }
                    if (closedNow)
                    {
                        eos << runTime.value() << " closure " << newBubbles << ' '
                            << bubbles << ' ' << pinchTotal << ' ' << closureTotal
                            << ' ' << vAll << ' ' << status << '\n';
                    }
                }
                prevEnt = bubbles;
                prevStatus = status;
            }

            const fileName dir(runTime.globalPath()/"postProcessing"/"wireCavity");
            mkDir(dir);
            const fileName fn(dir/"wireCavity.dat");
            const bool isNew = !isFile(fn);
            std::ofstream os(fn.c_str(), std::ios::app);
            if (isNew)
            {
                os << "# time[s] status zContactMax[m] zContactMin[m] "
                   << "cavityVolume[m3] volumeOpen[m3] volumeClosed[m3] "
                   << "depthBelowContact[m] lengthDownstream[m] "
                   << "cx[m] cy[m] cz[m] nOpenCells nClosedCells\n"
                   << "# status: 0 none, 1 open, 2 closed, 3 mixed "
                   << "(open = still connected to the atmosphere, "
                   << "closed = enclosed gas touching the wire)\n"
                   << "# depthBelowContact = zContactMax - min cavity-cell z\n"
                   << "# lengthDownstream = furthest cavity cell downstream of the "
                   << "wire axis (+x, the wake). Half-domain volumes are not mirrored.\n"
                   << "# zContact* is the wire triple line (contactLine pinWire). "
                   << "-1 if that line is absent.\n";
            }
            os.setf(std::ios::scientific);
            os.precision(8);
            os << runTime.value() << ' '
               << status << ' '
               << contactWireZMax << ' '
               << (contactWireZMin < 0.5*GREAT ? contactWireZMin : -1) << ' '
               << vAll << ' ' << vOpen << ' ' << vClosed << ' '
               << depth << ' ' << length << ' '
               << (vAll > SMALL ? mx*inv : 0) << ' '
               << (vAll > SMALL ? my*inv : 0) << ' '
               << (vAll > SMALL ? mz*inv : 0) << ' '
               << label(nOpen) << ' ' << label(nClosed) << '\n';
        }
    }
    else if
    (
        porWireCavity
     && pimple.finalIter()
     && (
            runTime.timeIndex() % max(porInterval, 1) == 0
         || runTime.writeTime()
        )
     && Pstream::master()
    )
    {
        // Pinning has not yet found a wire line. Still write a row so the
        // time series starts at the first sample.
        const fileName dir(runTime.globalPath()/"postProcessing"/"wireCavity");
        mkDir(dir);
        const fileName fn(dir/"wireCavity.dat");
        const bool isNew = !isFile(fn);
        std::ofstream os(fn.c_str(), std::ios::app);
        if (isNew)
        {
            os << "# time[s] status zContactMax[m] zContactMin[m] "
               << "cavityVolume[m3] volumeOpen[m3] volumeClosed[m3] "
               << "depthBelowContact[m] lengthDownstream[m] "
               << "cx[m] cy[m] cz[m] nOpenCells nClosedCells\n"
               << "# status: 0 none, 1 open, 2 closed, 3 mixed\n"
               << "# no wire contact line yet (zContact = -1)\n";
        }
        os.setf(std::ios::scientific);
        os.precision(8);
        os << runTime.value()
           << " 0 -1 -1 0 0 0 0 0 0 0 0 0 0\n";
    }

    // Thin gas film on the trailing face of the wire, near y = 0.
    // The radiograph slit is about 0.05 mm wide and about 0.4 mm deep
    // (z about 1.2 mm down to 0.75 mm). It is not the open wake, which
    // extends a millimetre off the centre plane. Depth is centre-to-centre
    // of the film cells. open = 1 if any of those cells still sees the
    // atmosphere.
    if
    (
        porWireCavity
     && pimple.finalIter()
     && (
            runTime.timeIndex() % max(porInterval, 1) == 0
         || runTime.writeTime()
        )
    )
    {
        const scalar yBand = 1.5e-4;
        const scalar rGap = 1.0e-4;
        const scalar rIn = 3.0e-5;
        const scalar zLo = 3.0e-4;
        const scalar zHi = 2.0e-3;
        const scalar cosTrail = 0.75;
        const vector trail(1, 0, 0);

        labelList slit(nCells, 0);
        forAll(alpha1, celli)
        {
            if (alpha1[celli] >= porAlphaOpen) continue;
            if (gasState[celli] == 0) continue;
            if (mag(C[celli].y()) > yBand) continue;
            const scalar z = C[celli].z();
            if (z < zLo || z > zHi) continue;
            const vector d = C[celli] - wireOrigin;
            const scalar s = d & wireUp;
            const vector rad = d - s*wireUp;
            const scalar r = mag(rad);
            if (r < wireRadius - rIn || r > wireRadius + rGap) continue;
            if (r > SMALL && (rad & trail)/(r + VSMALL) < cosTrail) continue;
            slit[celli] = 1;
        }

        DynamicList<label> sq(16);
        forAll(slit, celli)
        {
            if (slit[celli] != 1) continue;
            bool touch = false;
            for (const label n : cCells[celli])
            {
                if (inWireZone[n] && lwdUnmeltedWire(n) && alpha1[n] > 0.5)
                {
                    touch = true;
                    break;
                }
            }
            if (!touch) continue;
            slit[celli] = 2;
            sq.append(celli);
        }
        for (label qi = 0; qi < sq.size(); ++qi)
        {
            for (const label n : cCells[sq[qi]])
            {
                if (slit[n] == 1)
                {
                    slit[n] = 2;
                    sq.append(n);
                }
            }
        }
        if (Pstream::parRun())
        {
            label guard = 0;
            while (guard++ < 1000)
            {
                List<label> nei;
                lwdSwapCells(slit, nei);
                DynamicList<label> nq;
                const label nInt = mesh.nInternalFaces();
                for (label fi = nInt; fi < mesh.nFaces(); ++fi)
                {
                    const label c = mesh.faceOwner()[fi];
                    if (slit[c] == 1 && nei[fi - nInt] == 2)
                    {
                        slit[c] = 2;
                        nq.append(c);
                    }
                }
                for (label qi = 0; qi < nq.size(); ++qi)
                {
                    for (const label n : cCells[nq[qi]])
                    {
                        if (slit[n] == 1)
                        {
                            slit[n] = 2;
                            nq.append(n);
                        }
                    }
                }
                label changed = nq.size();
                reduce(changed, sumOp<label>());
                if (!changed) break;
            }
        }

        scalar zMin = GREAT, zMax = -GREAT, width = 0;
        label nSlit = 0, nAtm = 0;
        forAll(slit, celli)
        {
            if (slit[celli] != 2) continue;
            zMin = min(zMin, C[celli].z());
            zMax = max(zMax, C[celli].z());
            const vector d = C[celli] - wireOrigin;
            const scalar s = d & wireUp;
            const scalar r = mag(d - s*wireUp);
            width = max(width, max(r - wireRadius, scalar(0)));
            nSlit += 1;
            if (gasState[celli] == 1) nAtm += 1;
        }
        reduce(zMin, minOp<scalar>());
        reduce(zMax, maxOp<scalar>());
        reduce(width, maxOp<scalar>());
        reduce(nSlit, sumOp<label>());
        reduce(nAtm, sumOp<label>());
        const scalar depth = (nSlit > 0) ? max(zMax - zMin, scalar(0)) : 0;
        const label open = nAtm > 0 ? 1 : 0;

        if (Pstream::master())
        {
            Info<< "WireSlit: n = " << nSlit
                << "  depth = " << depth << " m"
                << "  width = " << width << " m"
                << "  z = " << (nSlit ? zMin : 0) << ".."
                << (nSlit ? zMax : 0) << " m"
                << "  open = " << open
                << endl;

            const fileName sdir(runTime.globalPath()/"postProcessing"/"wireSlit");
            mkDir(sdir);
            const fileName sfn(sdir/"wireSlit.dat");
            const bool sNew = !isFile(sfn);
            std::ofstream sos(sfn.c_str(), std::ios::app);
            if (sNew)
            {
                sos << "# time[s] nCells zMin[m] zMax[m] depth[m] width[m] open\n"
                    << "# Film of gas on the trailing wire face, |y| < 0.15 mm,\n"
                    << "# within 0.10 mm outside the wire radius, z in 0.3-2.0 mm.\n"
                    << "# depth is centre-to-centre. open = 1 if the film still\n"
                    << "# touches the atmosphere. Target: depth ~ 0.4 mm,\n"
                    << "# width ~ 0.05 mm, open, persisting.\n";
            }
            sos.setf(std::ios::scientific);
            sos.precision(8);
            sos << runTime.value() << ' ' << nSlit << ' '
                << (nSlit ? zMin : 0) << ' ' << (nSlit ? zMax : 0) << ' '
                << depth << ' ' << width << ' ' << open << '\n';
        }
    }
}
