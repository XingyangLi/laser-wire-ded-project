// ---------------------------------------------------------------------------
// Surface tension model of wireMeltFoam (replaces mixture.surfaceTensionForce())
//
//   CSF face force   f_st = w_f * interpolate(sigma K) * snGrad(alpha)    [N/m3]
//     K       interface curvature  K = -div(nHatf)  (same as interfaceProperties)
//     w_f     liquid weight = (alpha*fl)_f / max(alpha_f, alphaMin), clipped [0,1]
//             -> surface tension acts on liquid metal only; the solid wire/gas
//                interface carries no capillary force (liquidOnly = false: w_f = 1)
//
//   Linear model (oxygenDependent false, the historical default):
//     sigma(T) = max( sigma_m + (dSigma/dT) * (max(T, Tref) - Tref), sigmaMin )
//     dSigma/dT is the constant dictionary value (negative for clean metal).
//
//   Oxygen model (oxygenDependent true), Sahoo / Belton / Szekely:
//     sigma(T, a_O) = sigma_m - A (T - Tm)
//                   - R T Gamma_s ln( 1 + k1 a_O exp(-dH0 / (R T)) )
//     with T evaluated at max(T, Tm), so the value is frozen below the liquidus.
//     a_O [wt%] = chamberOxygenPpm * 1e-4  (1 wt% = 10000 ppm by weight).
//     chamberOxygenPpm is a uniform melt oxygen, used as a stand-in for the
//     chamber set-point. Sieverts equilibrium with the gas is not solved.
//     The Marangoni coefficient is the analytic d(sigma)/dT of that expression
//     (it changes sign when oxygen adsorption dominates). Where sigma is
//     clipped at sigmaMin, or T < Tm, dSigma/dT is set to 0.
//
//     sigma_m and A default to this case's sigma and -dSigmadT, so a_O = 0
//     reproduces the linear model. Adsorption coefficients default to Fe-O
//     (Sahoo, DebRoy, McNallan, Metall. Trans. B 19B (1988) 483-491):
//       Gamma_s = 2.03e-5 mol/m^2, k1 = 0.0138 /wt%, dH0 = -1.463e5 J/mol.
//     The isotherm is Belton's (Metall. Trans. B 7B (1976) 35-42) in the
//     combined temperature form used by Szekely for weld-pool flow and fitted
//     by Sahoo et al. The 316L linear part is the case preset (sigma 1.75 N/m
//     at T_liquidus, dSigma/dT -4.3e-4 N/m/K; Mills, Recommended Values of
//     Thermophysical Properties for Selected Commercial Alloys, Woodhead 2002,
//     austenitic stainless, low-O slope of that order). Fe-O is the surrogate
//     for 316L oxygen adsorption; it is not a 316L-specific fit.
//
//   Marangoni (optional): F_M = w * (dSigma/dT) (grad T - n (n.grad T)) |grad alpha|
//   Capillary time-step limit (Brackbill):
//     dt <= capillaryDtFactor * sqrt(rho_avg dx_min^3 / (2 pi sigma_max))
//
// Read from constant/meltProperties, sub-dictionary 'surfaceTension'.
// The sigma entry in transportProperties is not used for the force.
// ---------------------------------------------------------------------------

const dictionary stDict(meltProperties.subOrEmptyDict("surfaceTension"));
const dictionary mgDict(meltProperties.subOrEmptyDict("marangoni"));

const bool mgOld = mgDict.getOrDefault<bool>("enabled", false);
const scalar sigma0 = stDict.getOrDefault<scalar>("sigma", 1.8);
// Imposed numerical enhancement. 1 leaves the alloy value. It is not a
// measured surface tension. The CSF force and the capillary time-step
// limit both see sigmaScale * sigma(T).
const scalar sigmaScale = stDict.getOrDefault<scalar>("sigmaScale", 1.0);
const scalar dSigmadTval =
    stDict.getOrDefault<scalar>("dSigmadT", mgDict.getOrDefault<scalar>("dSigmadT", 0.0));
const bool sigmaTdep = stDict.getOrDefault<bool>("temperatureDependent", mgOld);
const scalar sigmaTref = stDict.getOrDefault<scalar>("Tref", Tliq.value());
const scalar sigmaMin = stDict.getOrDefault<scalar>("sigmaMin", 0.1*sigma0);
const scalar sigmaMaxInit = max(subP.sigma, wireP.sigma);
const bool marangoniOn = stDict.getOrDefault<bool>("marangoni", mgOld);
const bool stLiquidOnly = stDict.getOrDefault<bool>("liquidOnly", true);
// Same factor as marangoni.H. Off by default so existing cases keep the
// historical CSF. On: the light gas does not take the whole capillary jump.
const bool stDensityScaled = stDict.getOrDefault<bool>("densityScaled", false);
const scalar stAlphaMin = stDict.getOrDefault<scalar>("alphaMin", 1e-3);
const scalar capDtFactor = stDict.getOrDefault<scalar>("capillaryDtFactor", 0.8);

// oxygenDependent false: the linear model above, unchanged.
const bool oxygenDependent = stDict.getOrDefault<bool>("oxygenDependent", false);
const scalar chamberOxygenPpm = stDict.getOrDefault<scalar>("chamberOxygenPpm", 0.0);
// 1 wt% standard state used by Sahoo et al. 10000 ppm by weight = 1 wt%.
const scalar oxygenActivity = max(chamberOxygenPpm, scalar(0))*1.0e-4;
const scalar oxygenGamma = stDict.getOrDefault<scalar>("oxygenGammaS", 2.03e-5);
const scalar oxygenK1 = stDict.getOrDefault<scalar>("oxygenK1", 0.0138);
const scalar oxygenDH = stDict.getOrDefault<scalar>("oxygenDeltaH0", -1.463e5);
const scalar oxygenR = stDict.getOrDefault<scalar>("oxygenR", 8.314462618);
const bool oxygenSigmaMSet = stDict.found("oxygenSigmaM");
const scalar oxygenSigmaM = stDict.getOrDefault<scalar>("oxygenSigmaM", sigma0);
const bool oxygenASet = stDict.found("oxygenA");
const scalar oxygenA = stDict.getOrDefault<scalar>("oxygenA", max(-dSigmadTval, scalar(0)));
const bool oxygenTmSet = stDict.found("oxygenTm");
const scalar oxygenTm = stDict.getOrDefault<scalar>("oxygenTm", sigmaTref);

const dimensionedScalar dSigmadT("dSigmadT", dimForce/dimLength/dimTemperature, dSigmadTval);

// smallest cell-centre distance (internal faces) for the capillary limit
const scalar capDx = 1.0/max(gMax(mesh.deltaCoeffs().primitiveField()), SMALL);
const scalar capRhoAvg = 0.5*(rho1.value() + rho2.value());

// sigma and dSigma/dT are written when the oxygen model is on so two chamber
// levels can be compared without parsing the log.
const IOobject::writeOption stWrite =
    oxygenDependent ? IOobject::AUTO_WRITE : IOobject::NO_WRITE;

volScalarField sigmaT
(
    IOobject("sigmaT", runTime.timeName(), mesh, IOobject::NO_READ, stWrite),
    mesh,
    dimensionedScalar(dimForce/dimLength, sigmaMaxInit)
);

// Numeric dSigma/dT [N/m/K] stored dimensionless, matching matDSigma.
// Marangoni multiplies by dimForce/dimLength/dimTemperature.
volScalarField dSigmadTField
(
    IOobject("dSigmadTField", runTime.timeName(), mesh, IOobject::NO_READ, stWrite),
    matDSigma
);

surfaceScalarField stWeightf
(
    IOobject("stWeightf", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
    mesh,
    dimensionedScalar(dimless, 1.0)
);

volScalarField stWeight
(
    IOobject("stWeight", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
    mesh,
    dimensionedScalar(dimless, 1.0)
);

surfaceScalarField stForcef
(
    IOobject("stForcef", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
    fvc::interpolate(sigmaT*(-fvc::div(mixture.nHatf())))*fvc::snGrad(alpha1)
);

// One cell of the Sahoo-Belton expression. sigM / Aval / TmCell are the local
// alloy values unless the dictionary overrides them.
auto lwdSahooSigma = [&](const scalar Tcell, const scalar sigM, const scalar Aval, const scalar TmCell, scalar& sig, scalar& dsdT)
{
    const scalar Te = max(Tcell, max(TmCell, scalar(300)));
    const scalar Kseg = oxygenK1*Foam::exp(-oxygenDH/(oxygenR*Te));
    const scalar Ka = Kseg*oxygenActivity;
    const scalar lnTerm = Foam::log(scalar(1) + max(Ka, scalar(0)));
    const scalar sigRaw = sigM - Aval*(Te - TmCell) - oxygenR*Te*oxygenGamma*lnTerm;
    sig = max(sigRaw, sigmaMin);
    const scalar coverage = Ka/max(scalar(1) + Ka, SMALL);
    dsdT = -Aval - oxygenR*oxygenGamma*lnTerm - oxygenGamma*coverage*(oxygenDH/Te);
    if (Tcell < TmCell || sigRaw <= sigmaMin)
    {
        dsdT = 0;
    }
};

Info<< "Surface tension (CSF)\n"
    << "    model               : "
    << (oxygenDependent ? "Sahoo-Belton sigma(T, a_O)" : "linear sigma(T)")
    << nl
    << "    sigma0              : " << sigma0 << " N/m" << nl
    << "    sigmaScale          : " << sigmaScale
    << "  (imposed numerical enhancement, not a physical alloy value)" << nl
    << "    sigma(T)            : " << Switch(sigmaTdep)
    << "  dSigma/dT = " << dSigmadTval << " N/m/K, Tref = " << sigmaTref
    << " K, sigmaMin = " << sigmaMin << " N/m" << nl
    << "    liquid metal only   : " << Switch(stLiquidOnly) << nl
    << "    density-scaled CSF  : " << Switch(stDensityScaled) << nl
    << "    Marangoni stress    : " << Switch(marangoniOn) << nl;
if (oxygenDependent)
{
    scalar sigRef = 0, dsRef = 0, sigHot = 0, dsHot = 0;
    const scalar sigM0 = oxygenSigmaMSet ? oxygenSigmaM : sigma0;
    const scalar A0 = oxygenASet ? oxygenA : max(-dSigmadTval, scalar(0));
    const scalar Tm0 = oxygenTmSet ? oxygenTm : sigmaTref;
    lwdSahooSigma(Tm0, sigM0, A0, Tm0, sigRef, dsRef);
    lwdSahooSigma(Tm0 + 200.0, sigM0, A0, Tm0, sigHot, dsHot);
    Info<< "    chamberOxygenPpm    : " << chamberOxygenPpm
        << "  a_O = " << oxygenActivity << " wt%" << nl
        << "    Gamma_s, k1, dH0    : " << oxygenGamma << " mol/m^2, "
        << oxygenK1 << " /wt%, " << oxygenDH << " J/mol" << nl
        << "    sigma(Tm)           : " << sigRef << " N/m"
        << "  dSigma/dT(Tm) = " << dsRef << " N/m/K" << nl
        << "    sigma(Tm+200K)      : " << sigHot << " N/m"
        << "  dSigma/dT = " << dsHot << " N/m/K" << nl
        << "OxygenSigma: ppm = " << chamberOxygenPpm
        << "  aO_wt% = " << oxygenActivity
        << "  sigmaTm = " << sigRef
        << "  dsigdTTm = " << dsRef
        << "  sigmaTm200 = " << sigHot
        << "  dsigdTTm200 = " << dsHot
        << endl;
}
else
{
    Info<< "    oxygen              : off (oxygenDependent false)" << endl;
}
Info<< "    capillary dt limit  : "
    << Foam::sqrt(capRhoAvg*pow3(capDx)/(2.0*constant::mathematical::pi*max(sigma0, SMALL)))
    << " s (dx_min = " << capDx << " m), factor " << capDtFactor << nl << endl;

#include "updateSurfaceTension.H"
