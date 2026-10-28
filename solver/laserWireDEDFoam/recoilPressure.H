// ---------------------------------------------------------------------------
// Recoil pressure (Clausius-Clapeyron, Anisimov):
//   p_r(T) = 0.54 p0 exp( Lv M/R (1/Tb - 1/T) )      (T > Tliquidus, capped)
// added to the balanced CSF face force:  f = interpolate(p_r) snGrad(alpha)
// -> pushes the free surface into the liquid (towards increasing alpha).
// ---------------------------------------------------------------------------
{
    const dictionary& vapDict = meltProperties.subOrEmptyDict("vaporisation");
    const bool recoilOn = vapDict.getOrDefault<bool>("recoil", true);
    pRecoil.primitiveFieldRef() = 0.0;
    if (recoilOn)
    {
        const scalar Tboil = vapDict.getOrDefault<scalar>("Tboil", 3090.0);
        const scalar Lv = vapDict.getOrDefault<scalar>("Lv", 7.45e6);
        const scalar Mmol = vapDict.getOrDefault<scalar>("molarMass", 0.0558);
        const scalar pAmb = vapDict.getOrDefault<scalar>("pAmbient", 101325.0);
        const scalar pMax = vapDict.getOrDefault<scalar>("recoilMax", 2e5);
        // recoilInShell false zeros recoil on the trailing oxide shell
        // (same band as oxideSkin: +x, zMin–zMax, within gapThreshold).
        const bool recoilInShell = vapDict.getOrDefault<bool>("recoilInShell", true);
        const scalar Rgas = 8.314462618;
        scalarField& pr = pRecoil.primitiveFieldRef();
        const scalarField& Tc = T.primitiveField();
        forAll(pr, celli)
        {
            if (Tc[celli] > matTliq[celli] && alpha1[celli] > 1e-3)
            {
                pr[celli] = min
                (
                    0.54*pAmb*Foam::exp(min(Lv*Mmol/Rgas*(1.0/Tboil - 1.0/Tc[celli]), 50.0)),
                    pMax
                );
            }
        }
        if (!recoilInShell)
        {
            const vectorField& Cc = mesh.C().primitiveField();
            const scalarField& Vp = mesh.V();
            const vector trail(1, 0, 0);
            forAll(pr, celli)
            {
                const vector d = Cc[celli] - wireOrigin;
                const scalar s = d & wireUp;
                const vector rad = d - s*wireUp;
                const scalar r = mag(rad);
                const scalar h = Foam::cbrt(max(Vp[celli], SMALL));
                const bool onTrail =
                    (rad & trail) > 0 && s >= oxideSkinZ0 && s <= oxideSkinZ1;
                if (!onTrail) continue;
                if (r < wireRadius - 0.5*h || r > wireRadius + oxideSkinGap) continue;
                pr[celli] = 0;
            }
            static bool loggedRecoilShell = false;
            if (!loggedRecoilShell)
            {
                Info<< "Recoil: off inside the oxide shell (gap "
                    << oxideSkinGap << " m)" << nl;
                loggedRecoilShell = true;
            }
        }
        pRecoil.correctBoundaryConditions();
        stForcef += fvc::interpolate(pRecoil)*fvc::snGrad(alpha1);
    }
}
