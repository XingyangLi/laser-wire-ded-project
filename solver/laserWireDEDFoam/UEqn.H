    MRF.correctBoundaryVelocity(U);

    #include "marangoni.H"

    fvVectorMatrix UEqn
    (
        fvm::ddt(rho, U) + fvm::div(rhoPhi, U)
      + MRF.DDt(rho, U)
      + turbulence->divDevRhoReff(rho, U)
        // Carman-Kozeny sink -Kmushy (U - Usolid), plus the optional
        // contact-line pin -Kcontact (U - Ucontact). Ucontact equals Usolid
        // on the substrate line. On the wire it is the head frame (0) or
        // the feed velocity, see contactLine.H. Kcontact = 0 leaves this
        // identical to -Kmushy (U - Usolid).
      + fvm::Sp(Kmushy + Kcontact, U)
     ==
        Kmushy*Usolid
      + Kcontact*Ucontact
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
