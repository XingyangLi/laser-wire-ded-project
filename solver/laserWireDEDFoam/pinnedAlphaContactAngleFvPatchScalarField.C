#include "pinnedAlphaContactAngleFvPatchScalarField.H"
#include "addToRunTimeSelectionTable.H"
#include "fvPatchFieldMapper.H"
#include "volMesh.H"
#include "mathematicalConstants.H"

// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

Foam::pinnedAlphaContactAngleFvPatchScalarField::
pinnedAlphaContactAngleFvPatchScalarField
(
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF
)
:
    alphaContactAngleTwoPhaseFvPatchScalarField(p, iF),
    thetaA_(180.0),
    thetaR_(0.0)
{}


Foam::pinnedAlphaContactAngleFvPatchScalarField::
pinnedAlphaContactAngleFvPatchScalarField
(
    const pinnedAlphaContactAngleFvPatchScalarField& ptf,
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF,
    const fvPatchFieldMapper& mapper
)
:
    alphaContactAngleTwoPhaseFvPatchScalarField(ptf, p, iF, mapper),
    thetaA_(ptf.thetaA_),
    thetaR_(ptf.thetaR_)
{}


Foam::pinnedAlphaContactAngleFvPatchScalarField::
pinnedAlphaContactAngleFvPatchScalarField
(
    const fvPatch& p,
    const DimensionedField<scalar, volMesh>& iF,
    const dictionary& dict
)
:
    alphaContactAngleTwoPhaseFvPatchScalarField(p, iF, dict),
    thetaA_(dict.get<scalar>("thetaA")),
    thetaR_(dict.get<scalar>("thetaR"))
{
    if (thetaA_ < thetaR_)
    {
        FatalIOErrorInFunction(dict)
            << "thetaA (" << thetaA_ << " deg) is below thetaR ("
            << thetaR_ << " deg)" << nl
            << exit(FatalIOError);
    }
    evaluate();
}


Foam::pinnedAlphaContactAngleFvPatchScalarField::
pinnedAlphaContactAngleFvPatchScalarField
(
    const pinnedAlphaContactAngleFvPatchScalarField& ptf
)
:
    alphaContactAngleTwoPhaseFvPatchScalarField(ptf),
    thetaA_(ptf.thetaA_),
    thetaR_(ptf.thetaR_)
{}


Foam::pinnedAlphaContactAngleFvPatchScalarField::
pinnedAlphaContactAngleFvPatchScalarField
(
    const pinnedAlphaContactAngleFvPatchScalarField& ptf,
    const DimensionedField<scalar, volMesh>& iF
)
:
    alphaContactAngleTwoPhaseFvPatchScalarField(ptf, iF),
    thetaA_(ptf.thetaA_),
    thetaR_(ptf.thetaR_)
{}


// * * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * //

Foam::tmp<Foam::scalarField>
Foam::pinnedAlphaContactAngleFvPatchScalarField::theta
(
    const fvPatchVectorField&,
    const fvsPatchVectorField& nHat
) const
{
    // nHat points toward the metal. nf points out of the domain, into the
    // wall. theta = acos(nHat·nf) is the angle through the metal. Returning
    // that angle leaves correctContactAngle as a no-op (the line is pinned).
    // Clamping to the window edge restores a Young force so the line can slip.
    const scalar radToDeg = 180.0/constant::mathematical::pi;
    const vectorField nf(patch().nf());

    auto ttheta = tmp<scalarField>::New(nHat.size());
    scalarField& theta = ttheta.ref();

    forAll(theta, facei)
    {
        const scalar c = max(min(nHat[facei] & nf[facei], scalar(1)), scalar(-1));
        const scalar apparent = ::acos(c)*radToDeg;
        if (apparent > thetaA_)
        {
            theta[facei] = thetaA_;
        }
        else if (apparent < thetaR_)
        {
            theta[facei] = thetaR_;
        }
        else
        {
            theta[facei] = apparent;
        }
    }

    return ttheta;
}


void Foam::pinnedAlphaContactAngleFvPatchScalarField::write(Ostream& os) const
{
    alphaContactAngleTwoPhaseFvPatchScalarField::write(os);
    os.writeEntry("thetaA", thetaA_);
    os.writeEntry("thetaR", thetaR_);
    fvPatchField<scalar>::writeValueEntry(os);
}


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{
    makePatchTypeField
    (
        fvPatchScalarField,
        pinnedAlphaContactAngleFvPatchScalarField
    );
}


// ************************************************************************* //
