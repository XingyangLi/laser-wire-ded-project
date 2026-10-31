// Generated melting at the solid-wire tip. Off unless wireTipMelt is enabled.
//
// The wall velocity and the trailing contact line are imposed. This block
// only turns heat that has already reached the cells on the bottom of
// wireWall into liquid wire. Superheat above Tliquidus pays the sensible
// heat of cold wire (Twire) up to the liquidus. Latent heat is left to the
// enthalpy-porosity term on the next step. New metal is added only where
// alpha has room under 1, so a full pool is not overwritten.
const dictionary wireTipMeltDict(meltProperties.subOrEmptyDict("wireTipMelt"));
const bool wireTipMeltEnabled =
    wireTipMeltDict.getOrDefault<bool>("enabled", false);
const scalar wireTipTcold =
    wireTipMeltDict.getOrDefault<scalar>("Twire", 300.0);
const scalar wireTipBand =
    wireTipMeltDict.getOrDefault<scalar>("band", 4.0e-4);
const scalar wireTipVmax =
    wireTipMeltDict.getOrDefault<scalar>("vMax", 0.05);
scalar wireTipLength = 0;
if (wireTipMeltEnabled)
{
    Info<< "WireTipMelt: generated melt-back at the wall tip, Twire "
        << wireTipTcold << " K, band " << wireTipBand
        << " m, vMax " << wireTipVmax << " m/s" << nl
        << "    imposed: wall velocity = feed, linePin moves the contact" << nl
        << "    generated: liquid volume from superheat at the tip" << nl;
}
