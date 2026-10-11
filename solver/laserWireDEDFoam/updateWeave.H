// Triangular zigzag of the head in y. Travel distance is the plate motion
// (scan speed * time), so the frozen bead has one zigzag per weaveWavelength.
// y = amplitude * (1 - 4*|frac-0.5|) runs -amplitude .. +amplitude .. -amplitude.
// At t = 0 the head sits on the -amplitude corner.
if (weaveOn)
{
    const scalar travel = solidVelocity.x()*runTime.value();
    const scalar frac = travel/weaveWavelength - std::floor(travel/weaveWavelength);
    weaveY = weaveAmplitude*(1 - 4*mag(frac - 0.5));
    const scalar sign = (frac < 0.5 ? 1.0 : -1.0);
    weaveYDot = sign*4*weaveAmplitude*solidVelocity.x()/weaveWavelength;
    wireOrigin = wireOrigin0 + point(0, weaveY, 0);
    if (!weaveReported)
    {
        Info<< "Weave path: y = " << weaveY << " m at t = " << runTime.value()
            << " s (sideways speed " << weaveYDot << " m/s)" << nl;
        weaveReported = true;
    }
    if (retraceLaser && mag(weaveY - weaveYTraced) > weaveRetraceDy)
    {
        retraceLaser();
    }
}
