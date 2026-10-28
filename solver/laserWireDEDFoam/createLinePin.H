// Imposed trailing contact line. Off unless linePin { enabled true; }.
//
// The line is a material point of the wire: its height is the initial
// wetted top plus the feed displacement. At the line the shell is narrow
// and fully imposed. If thicknessTop is set, the gas bias widens toward
// the crest and the hold fades, and the cell outside the bias is not
// forced back to metal. That outer meniscus is free: the wedge past the
// bias is generated, not painted. Liquid moved out of a shell cell is
// given to the next cell outward, so the coating is displaced rather
// than deleted.
//
// ppm sets the hold. s = min(ppm/ppmRef, 1) is the fraction of the error
// removed after every alpha solve, and the fraction of Kpin. At ppmRef the
// shell is overwritten. Sahoo–Belton sigma still follows ppm on its own.
const dictionary linePinDict(meltProperties.subOrEmptyDict("linePin"));
const bool linePinEnabled = linePinDict.getOrDefault<bool>("enabled", false);
const scalar linePinTau = linePinDict.getOrDefault<scalar>("tau", 5e-4);
const scalar linePinPpmRef = linePinDict.getOrDefault<scalar>("ppmRef", 300);
const scalar linePinNCells = linePinDict.getOrDefault<scalar>("nCells", 2);
// Fixed radial thickness of the imposed gas shell. Negative means nCells
// times the local cell size, which on a coarse cell is a thick shell.
const scalar linePinThickness = linePinDict.getOrDefault<scalar>("thickness", -1);
// Wider gas bias at the crest. Negative keeps a constant thickness.
const scalar linePinThicknessTop = linePinDict.getOrDefault<scalar>("thicknessTop", -1);
// Full hold within this height above the line. Above it the hold fades.
const scalar linePinBand = linePinDict.getOrDefault<scalar>("lineBand", 8e-5);
const scalar linePinFade = linePinDict.getOrDefault<scalar>("holdFade", 0.75);
const scalar linePinK = linePinDict.getOrDefault<scalar>("Kpin", 1e12);
// Negative until the first step measures the wetted top.
scalar linePinZ0 = -1;
if (linePinEnabled)
{
    Info<< "Line pin: imposed trailing contact, "
        << linePinNCells << " cells, tau " << linePinTau
        << " s, ppmRef " << linePinPpmRef
        << ", Kpin " << linePinK;
    if (linePinThickness > 0)
    {
        Info<< ", thickness " << linePinThickness*1e3 << " mm (imposed)";
    }
    if (linePinThicknessTop > linePinThickness && linePinThickness > 0)
    {
        Info<< ", thicknessTop " << linePinThicknessTop*1e3
            << " mm (fading bias, meniscus free outside)";
    }
    Info<< nl;
}
