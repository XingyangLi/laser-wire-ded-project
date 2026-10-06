// Capillary (Brackbill) time-step limit, applied after setDeltaT.H
if (capDtFactor > 0)
{
    const scalar sigmaMaxNow = max(gMax(sigmaT.primitiveField()), SMALL);
    const scalar dtCap =
        capDtFactor
       *Foam::sqrt(capRhoAvg*pow3(capDx)/(2.0*constant::mathematical::pi*sigmaMaxNow));

    if (runTime.deltaTValue() > dtCap)
    {
        runTime.setDeltaT(dtCap);
        Info<< "deltaT limited by capillary condition = " << dtCap << endl;
    }
}
