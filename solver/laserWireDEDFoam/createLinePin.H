// Imposed trailing contact line. Off unless linePin { enabled true; }.
//
// The line is a material point of the wire: its height is the initial
// wetted top plus the feed displacement. In a shell one to three cells
// thick on the trailing face, alpha is restored toward gas above that
// height and metal below it, and the velocity is restored toward the feed.
// Liquid moved out of a shell cell is given to the next cell outward, so
// the coating is displaced rather than deleted. Cells outside that
// exchange are left alone, so the pool surface is free.
// The shell is the imposed pin. The gap outside it is the free surface.
//
// ppm sets the hold. s = min(ppm/ppmRef, 1) is the fraction of the error
// removed after every alpha solve, and the fraction of Kpin. At ppmRef the
// shell is overwritten. Sahoo–Belton sigma still follows ppm on its own.
const dictionary linePinDict(meltProperties.subOrEmptyDict("linePin"));
const bool linePinEnabled = linePinDict.getOrDefault<bool>("enabled", false);
const scalar linePinTau = linePinDict.getOrDefault<scalar>("tau", 5e-4);
const scalar linePinPpmRef = linePinDict.getOrDefault<scalar>("ppmRef", 300);
const scalar linePinNCells = linePinDict.getOrDefault<scalar>("nCells", 2);
const scalar linePinK = linePinDict.getOrDefault<scalar>("Kpin", 1e12);
// Negative until the first step measures the wetted top.
scalar linePinZ0 = -1;
if (linePinEnabled)
{
    Info<< "Line pin: imposed trailing contact, "
        << linePinNCells << " cells, tau " << linePinTau
        << " s, ppmRef " << linePinPpmRef
        << ", Kpin " << linePinK << nl;
}
