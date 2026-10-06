// ---------------------------------------------------------------------------
// Surface tension model of wireMeltFoam (replaces mixture.surfaceTensionForce())
//
//   CSF face force   f_st = w_f * interpolate(sigma(T) K) * snGrad(alpha)    [N/m3]
//     K       interface curvature  K = -div(nHatf)  (same as interfaceProperties)
//     sigma   sigma(T) = max(sigma0 + dSigma/dT (max(T,Tref) - Tref), sigmaMin)
//             (constant sigma0 if temperatureDependent = false)
//     w_f     liquid weight = (alpha*fl)_f / max(alpha_f, alphaMin), clipped [0,1]
//             -> surface tension acts on liquid metal only; the solid wire/gas
//                interface carries no capillary force (liquidOnly = false: w_f = 1)
//   Marangoni (optional): F_M = w * dSigma/dT (grad T - n (n.grad T)) |grad alpha|
//   Capillary time-step limit (Brackbill):
//     dt <= capillaryDtFactor * sqrt(rho_avg dx_min^3 / (2 pi sigma_max))
//
// Read from constant/meltProperties, sub-dictionary 'surfaceTension'
// (falls back to the old 'marangoni' dictionary for older cases).
// The sigma entry in transportProperties is not used for the force.
// ---------------------------------------------------------------------------

const dictionary stDict(meltProperties.subOrEmptyDict("surfaceTension"));
const dictionary mgDict(meltProperties.subOrEmptyDict("marangoni"));

const bool mgOld = mgDict.getOrDefault<bool>("enabled", false);
const scalar sigma0 = stDict.getOrDefault<scalar>("sigma", 1.8);
const scalar dSigmadTval =
    stDict.getOrDefault<scalar>("dSigmadT", mgDict.getOrDefault<scalar>("dSigmadT", 0.0));
const bool sigmaTdep = stDict.getOrDefault<bool>("temperatureDependent", mgOld);
const scalar sigmaTref = stDict.getOrDefault<scalar>("Tref", Tliq.value());
const scalar sigmaMin = stDict.getOrDefault<scalar>("sigmaMin", 0.1*sigma0);
const scalar sigmaMaxInit = max(subP.sigma, wireP.sigma);
const bool marangoniOn = stDict.getOrDefault<bool>("marangoni", mgOld);
const bool stLiquidOnly = stDict.getOrDefault<bool>("liquidOnly", true);
const scalar stAlphaMin = stDict.getOrDefault<scalar>("alphaMin", 1e-3);
const scalar capDtFactor = stDict.getOrDefault<scalar>("capillaryDtFactor", 0.8);

const dimensionedScalar dSigmadT("dSigmadT", dimForce/dimLength/dimTemperature, dSigmadTval);

// smallest cell-centre distance (internal faces) for the capillary limit
const scalar capDx = 1.0/max(gMax(mesh.deltaCoeffs().primitiveField()), SMALL);
const scalar capRhoAvg = 0.5*(rho1.value() + rho2.value());

volScalarField sigmaT
(
    IOobject("sigmaT", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
    mesh,
    dimensionedScalar(dimForce/dimLength, sigmaMaxInit)
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

Info<< "Surface tension (CSF)\n"
    << "    sigma0              : " << sigma0 << " N/m" << nl
    << "    sigma(T)            : " << Switch(sigmaTdep)
    << "  dSigma/dT = " << dSigmadTval << " N/m/K, Tref = " << sigmaTref
    << " K, sigmaMin = " << sigmaMin << " N/m" << nl
    << "    liquid metal only   : " << Switch(stLiquidOnly) << nl
    << "    Marangoni stress    : " << Switch(marangoniOn) << nl
    << "    capillary dt limit  : "
    << Foam::sqrt(capRhoAvg*pow3(capDx)/(2.0*constant::mathematical::pi*sigma0))
    << " s (dx_min = " << capDx << " m), factor " << capDtFactor << nl << endl;

#include "updateSurfaceTension.H"
