#include "pinnedAlphaContactAngleFvPatchScalarField.H"
#include "addToRunTimeSelectionTable.H"
#include "fvPatchFieldMapper.H"
#include "volFields.H"
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
    thetaR_(0.0),
    thetaAox_(180.0),
    thetaRox_(0.0),
    oxideBlend_(false)
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
    thetaR_(ptf.thetaR_),
    thetaAox_(ptf.thetaAox_),
    thetaRox_(ptf.thetaRox_),
    oxideBlend_(ptf.oxideBlend_)
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
    thetaR_(dict.get<scalar>("thetaR")),
    thetaAox_(dict.getOrDefault<scalar>("thetaAox", thetaA_)),
    thetaRox_(dict.getOrDefault<scalar>("thetaRox", thetaR_)),
    oxideBlend_(dict.found("thetaAox") || dict.found("thetaRox"))
{
    if (thetaA_ < thetaR_ || thetaAox_ < thetaRox_)
    {
        FatalIOErrorInFunction(dict)
            << "advancing limit is below the receding limit: thetaA "
            << thetaA_ << " thetaR " << thetaR_
            << " thetaAox " << thetaAox_ << " thetaRox " << thetaRox_ << nl
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
    thetaR_(ptf.thetaR_),
    thetaAox_(ptf.thetaAox_),
    thetaRox_(ptf.thetaRox_),
    oxideBlend_(ptf.oxideBlend_)
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
    thetaR_(ptf.thetaR_),
    thetaAox_(ptf.thetaAox_),
    thetaRox_(ptf.thetaRox_),
    oxideBlend_(ptf.oxideBlend_)
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
    const volScalarField* covPtr = nullptr;
    if
    (
        oxideBlend_
     && this->db().foundObject<volScalarField>("oxideCoverage")
    )
    {
        covPtr = &this->db().lookupObject<volScalarField>("oxideCoverage");
    }
    const labelUList& faceCells = patch().faceCells();

    auto ttheta = tmp<scalarField>::New(nHat.size());
    scalarField& theta = ttheta.ref();

    forAll(theta, facei)
    {
        scalar thetaA = thetaA_;
        scalar thetaR = thetaR_;
        if (covPtr)
        {
            const scalar c = min
            (
                max(covPtr->primitiveField()[faceCells[facei]], scalar(0)),
                scalar(1)
            );
            thetaA = (1 - c)*thetaA_ + c*thetaAox_;
            thetaR = (1 - c)*thetaR_ + c*thetaRox_;
        }
        const scalar cang = max(min(nHat[facei] & nf[facei], scalar(1)), scalar(-1));
        const scalar apparent = ::acos(cang)*radToDeg;
        if (apparent > thetaA)
        {
            theta[facei] = thetaA;
        }
        else if (apparent < thetaR)
        {
            theta[facei] = thetaR;
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
    if (oxideBlend_)
    {
        os.writeEntry("thetaAox", thetaAox_);
        os.writeEntry("thetaRox", thetaRox_);
    }
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
