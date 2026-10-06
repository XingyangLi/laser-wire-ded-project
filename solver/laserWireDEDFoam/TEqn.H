// ---------------------------------------------------------------------------
// Energy equation, enthalpy-porosity (Voller-Prakash) source-based method
//
//  d(rhoCp T)/dt + div(rhoCpPhi T) - T*[d(rhoCp)/dt + div(rhoCpPhi)]
//      - div(k grad T) = Q_laser - Q_loss - rho_m L [ d(alpha fl)/dt + div(alphaPhi fl) ]
//
//  k        = alpha (k_s + fl (k_l - k_s)) + (1-alpha) k_g
//  Q_loss   = [ q_evap(T) + h (T-T0) + eps sigma_SB (T^4 - T0^4) ] * 2 alpha |grad alpha|
//  q_evap   = Lv * 0.82 * p_sat(T) sqrt(M/(2 pi R T)),
//  p_sat    = p0 exp( Lv M/R (1/Tb - 1/T) )          (Clausius-Clapeyron)
//  (losses linearised implicitly -> unconditionally positive T)
// ---------------------------------------------------------------------------
{
    const dimensionedScalar cpU(dimSpecificHeatCapacity, 1.0);
    const dimensionedScalar kU(dimPower/dimLength/dimTemperature, 1.0);
    const dimensionedScalar LU(dimEnergy/dimMass, 1.0);
    rhoCp == alpha1*rho1*matCp*cpU + alpha2*rho2*cp2;

    const surfaceScalarField rhoCpPhi
    (
        "rhoCpPhi",
        alphaPhi10*(rho1*fvc::interpolate(matCp)*cpU - rho2*cp2) + phi*(rho2*cp2)
    );

    #include "laserSource.H"

    // --- free-surface loss settings
    const dictionary& slDict = meltProperties.subOrEmptyDict("surfaceLosses");
    const bool evapOn = slDict.getOrDefault<bool>("evaporation", true);
    const bool radOn  = slDict.getOrDefault<bool>("radiation", true);
    const bool convOn = slDict.getOrDefault<bool>("convection", true);
    const scalar emis = slDict.getOrDefault<scalar>("emissivity", 0.4);
    const scalar hConv = slDict.getOrDefault<scalar>("hConv", 20.0);
    const scalar Tamb = slDict.getOrDefault<scalar>("Tambient", 300.0);
    const dictionary& vapDict = meltProperties.subOrEmptyDict("vaporisation");
    const scalar Tboil = vapDict.getOrDefault<scalar>("Tboil", 3090.0);
    const scalar Lv = vapDict.getOrDefault<scalar>("Lv", 7.45e6);
    const scalar Mmol = vapDict.getOrDefault<scalar>("molarMass", 0.0558);
    const scalar pAmb = vapDict.getOrDefault<scalar>("pAmbient", 101325.0);
    const scalar Rgas = 8.314462618;
    const scalar sigmaSB = 5.670374419e-8;

    const volScalarField areaDens
    (
        "areaDens",
        2.0*max(min(alpha1, scalar(1)), scalar(0))*mag(fvc::grad(alpha1))
    );


    volScalarField lossCoeff
    (
        IOobject("lossCoeff", runTime.timeName(), mesh),
        mesh,
        dimensionedScalar(dimPower/dimVolume/dimTemperature, Zero)
    );
    volScalarField lossSource
    (
        IOobject("lossSource", runTime.timeName(), mesh),
        mesh,
        dimensionedScalar(dimPower/dimVolume, Zero)
    );

    for (label corr = 0; corr < nTCorr; ++corr)
    {
        alphaFl == alpha1*liquidFraction;

        const volScalarField kappa
        (
            "kappa",
            alpha1*(matKs + liquidFraction*(matKl - matKs))*kU
          + alpha2*k2
        );

        // implicit loss coefficient B [W/m3/K] and explicit part B*T0
        {
            scalarField& B = lossCoeff.primitiveFieldRef();
            scalarField& S = lossSource.primitiveFieldRef();
            const scalarField& Tc = T.primitiveField();
            const scalarField& ad = areaDens.primitiveField();
            forAll(B, celli)
            {
                B[celli] = 0; S[celli] = 0;
                if (ad[celli] <= 0) continue;
                const scalar Tl = max(Tc[celli], 1.0);
                scalar b = 0;
                if (convOn) b += hConv;
                if (radOn) b += emis*sigmaSB*(sqr(Tl) + sqr(Tamb))*(Tl + Tamb);
                scalar bev = 0;
                if (evapOn && Tl > matTsol[celli])
                {
                    const scalar psat =
                        pAmb*Foam::exp(min(Lv*Mmol/Rgas*(1.0/Tboil - 1.0/Tl), 50.0));
                    const scalar mdot =
                        0.82*psat*Foam::sqrt(Mmol/(2*constant::mathematical::pi*Rgas*Tl));
                    bev = Lv*mdot/Tl;
                }
                B[celli] = (b + bev)*ad[celli];
                S[celli] = b*ad[celli]*Tamb;
            }
        }

        fvScalarMatrix TEqn
        (
            fvm::ddt(rhoCp, T)
          + fvm::div(rhoCpPhi, T, "div(rhoCpPhi,T)")
          - fvm::Sp(fvc::ddt(rhoCp) + fvc::div(rhoCpPhi), T)
          - fvm::laplacian(kappa, T)
         ==
            Qheat
          - fvm::Sp(lossCoeff, T)
          + lossSource
          - rho1*matL*LU*
            (
                fvc::ddt(alphaFl)
              + fvc::div(alphaPhi10, liquidFraction, "div(alphaPhi,fl)")
            )
          + fvOptions(rhoCp, T)
        );

        TEqn.relax();
        fvOptions.constrain(TEqn);
        TEqn.solve();
        fvOptions.correct(T);

        T.primitiveFieldRef() = max(min(T.primitiveField(), TmaxClip), TminClip);
        T.correctBoundaryConditions();

        // Liquid-fraction update (Voller-Swaminathan style)
        scalarField& fl = liquidFraction.primitiveFieldRef();
        const scalarField& Tc = T.primitiveField();
        forAll(fl, celli)
        {
            const scalar Ts = matTsol[celli];
            const scalar Tl = matTliq[celli];
            const scalar dTm = max(Tl - Ts, SMALL);
            if (alpha1[celli] > alphaMinFl)
            {
                const scalar Tfl = Ts + fl[celli]*dTm;
                fl[celli] = max(min(fl[celli] + flRelax*matCp[celli]/matL[celli]*(Tc[celli] - Tfl), 1.0), 0.0);
                if (Tc[celli] <= Ts) fl[celli] = 0.0;
                if (Tc[celli] >= Tl) fl[celli] = 1.0;
            }
            else
            {
                fl[celli] = max(min((Tc[celli] - Ts)/dTm, 1.0), 0.0);
            }
        }
        liquidFraction.correctBoundaryConditions();
    }

    surfaceLossPower =
        gSum((lossCoeff.primitiveField()*T.primitiveField() - lossSource.primitiveField())*mesh.V());

    alphaFl == alpha1*liquidFraction;

    Kmushy.primitiveFieldRef() =
        Cmushy.value()*max(min(alpha1.primitiveField(), 1.0), 0.0)
       *sqr(1.0 - liquidFraction.primitiveField())
       /(pow3(liquidFraction.primitiveField()) + epsMushy);
    Kmushy.correctBoundaryConditions();

    Info<< "T: min = " << gMin(T.primitiveField())
        << " max = " << gMax(T.primitiveField())
        << "  laser: incident = " << laserIncidentPower
        << " W absorbed = " << laserAbsorbedPower
        << " W  surface loss = " << surfaceLossPower << " W" << endl;
}
