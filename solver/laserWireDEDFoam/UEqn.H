    MRF.correctBoundaryVelocity(U);

    #include "marangoni.H"

    fvVectorMatrix UEqn
    (
        fvm::ddt(rho, U) + fvm::div(rhoPhi, U)
      + MRF.DDt(rho, U)
      + turbulence->divDevRhoReff(rho, U)
        // Carman-Kozeny (enthalpy-porosity) sink: -K (U - Usolid)
        // plus the optional contact-line pin: -Kcontact (U - Usolid)
      + fvm::Sp(Kmushy + Kcontact, U)
     ==
        (Kmushy + Kcontact)*Usolid
      + Fmarangoni
      + Fbuoy
      + Fcontact
      + fvOptions(rho, U)
    );

    UEqn.relax();

    fvOptions.constrain(UEqn);

    if (pimple.momentumPredictor())
    {
        solve
        (
            UEqn
         ==
            fvc::reconstruct
            (
                (
                    stForcef
                  - ghf*fvc::snGrad(rho)
                  - fvc::snGrad(p_rgh)
                ) * mesh.magSf()
            )
        );

        fvOptions.correct(U);
    }
