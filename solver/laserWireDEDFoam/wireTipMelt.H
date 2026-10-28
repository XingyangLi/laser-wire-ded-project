// Generated tip melt. See createWireTipMelt.H. Runs after TEqn, once per step.
{
    if (wireTipMeltEnabled && pimple.finalIter())
    {
        const label patchi = mesh.boundaryMesh().findPatchID("wireWall");
        if (patchi >= 0)
        {
            const fvPatch& wp = mesh.boundary()[patchi];
            const labelUList& faceCells = wp.faceCells();
            const vectorField& Cf = wp.Cf();
            scalar zMin = GREAT;
            forAll(Cf, fi)
            {
                zMin = min(zMin, Cf[fi].z());
            }
            reduce(zMin, minOp<scalar>());

            const vectorField& C = mesh.C().primitiveField();
            const scalarField& Vc = mesh.V();
            const scalarField& cp = matCp.primitiveField();
            scalarField& Tc = T.primitiveFieldRef();
            scalarField& ac = alpha1.primitiveFieldRef();
            scalarField& fl = liquidFraction.primitiveFieldRef();
            scalarField& cw = cWire.primitiveFieldRef();
            const labelListList& cellCells = mesh.cellCells();
            const scalar rho = rho1.value();
            const scalar Tl = Tliq.value();
            const scalar sensible = max(Tl - wireTipTcold, scalar(1));

            boolList tip(mesh.nCells(), false);
            forAll(faceCells, fi)
            {
                if (Cf[fi].z() <= zMin + wireTipBand)
                {
                    tip[faceCells[fi]] = true;
                }
            }

            scalar dVsum = 0;
            scalar Espent = 0;
            forAll(tip, celli)
            {
                if (!tip[celli]) continue;
                if (Tc[celli] <= Tl || ac[celli] < 0.2) continue;
                const scalar E =
                    rho*cp[celli]*ac[celli]*Vc[celli]*(Tc[celli] - Tl);
                const scalar mWant = E/max(cp[celli]*sensible, SMALL);
                scalar dV = mWant/rho;
                const scalar dVfull = dV;

                auto put = [&](const label dest, scalar& vol) -> void
                {
                    const scalar space = max((1 - ac[dest])*Vc[dest], scalar(0));
                    if (space <= 1e-18 || vol <= 1e-18) return;
                    const scalar take = min(vol, space);
                    const scalar mOld = max(ac[dest]*Vc[dest], scalar(0));
                    cw[dest] = (cw[dest]*mOld + take)/(mOld + take);
                    ac[dest] = min(ac[dest] + take/Vc[dest], scalar(1));
                    if (Tc[dest] < Tl) Tc[dest] = Tl;
                    fl[dest] = 1;
                    vol -= take;
                };

                put(celli, dV);
                if (dV > 1e-18)
                {
                    for (const label nei : cellCells[celli])
                    {
                        put(nei, dV);
                        if (dV <= 1e-18) break;
                    }
                }
                const scalar used = dVfull - dV;
                if (used <= 1e-18) continue;
                const scalar frac = used/max(dVfull, SMALL);
                Tc[celli] = Tl + (1 - frac)*(Tc[celli] - Tl);
                dVsum += used;
                Espent += frac*E;
            }
            reduce(dVsum, sumOp<scalar>());
            reduce(Espent, sumOp<scalar>());

            const scalar Ahalf =
                0.5*constant::mathematical::pi*sqr(wireRadius);
            const scalar dz = dVsum/max(Ahalf, SMALL);
            const scalar dt = max(runTime.deltaTValue(), SMALL);
            wireTipLength += dz;
            const scalar vMelt = dz/dt;
            // Cap is applied only as a report. A single hot step cannot add
            // more metal than the cells can hold.
            if
            (
                runTime.timeIndex() <= 3
             || runTime.timeIndex() % 20 == 0
             || vMelt > wireTipVmax
            )
            {
                Info<< "WireTipMelt: generated vMelt " << vMelt*1e3
                    << " mm/s  dV " << dVsum*1e9
                    << " mm3  length " << wireTipLength*1e3
                    << " mm  E " << Espent
                    << " J  imposed feed " << mag(wireFeedVelocity.z())*1e3
                    << " mm/s  tip z " << zMin*1e3 << " mm" << nl;
            }
            if (vMelt > wireTipVmax && dVsum > Ahalf*wireTipVmax*dt)
            {
                // The room limit already bound dV. Nothing further to clip.
            }
        }
    }
}
