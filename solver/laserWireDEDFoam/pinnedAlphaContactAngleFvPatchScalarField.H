/*---------------------------------------------------------------------------*\
Class
    Foam::pinnedAlphaContactAngleFvPatchScalarField

Description
    Contact-angle hysteresis on a wall. Inside [thetaR, thetaA] the imposed
    angle is the current apparent angle, so correctContactAngle does not
    rotate the interface normal and there is no unbalanced Young force.
    Outside that window the angle is clamped to the nearer limit and the
    line can slip. Angles are degrees, through the metal, as in
    constantAlphaContactAngle.

    The companion momentum sink is wireWallDrag.H: no-slip and Kcontact on
    the trailing contact line while the angle stays inside this window, so
    the wall velocity carries the line instead of the line sliding along
    the wall.

SourceFiles
    pinnedAlphaContactAngleFvPatchScalarField.C

\*---------------------------------------------------------------------------*/

#ifndef pinnedAlphaContactAngleFvPatchScalarField_H
#define pinnedAlphaContactAngleFvPatchScalarField_H

#include "alphaContactAngleTwoPhaseFvPatchScalarField.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{

class pinnedAlphaContactAngleFvPatchScalarField
:
    public alphaContactAngleTwoPhaseFvPatchScalarField
{
    // Private data

        //- Advancing limit [deg], through the metal
        scalar thetaA_;

        //- Receding limit [deg], through the metal
        scalar thetaR_;


public:

    //- Runtime type information
    TypeName("pinnedAlphaContactAngle");


    // Constructors

        pinnedAlphaContactAngleFvPatchScalarField
        (
            const fvPatch&,
            const DimensionedField<scalar, volMesh>&
        );

        pinnedAlphaContactAngleFvPatchScalarField
        (
            const fvPatch&,
            const DimensionedField<scalar, volMesh>&,
            const dictionary&
        );

        pinnedAlphaContactAngleFvPatchScalarField
        (
            const pinnedAlphaContactAngleFvPatchScalarField&,
            const fvPatch&,
            const DimensionedField<scalar, volMesh>&,
            const fvPatchFieldMapper&
        );

        pinnedAlphaContactAngleFvPatchScalarField
        (
            const pinnedAlphaContactAngleFvPatchScalarField&
        );

        pinnedAlphaContactAngleFvPatchScalarField
        (
            const pinnedAlphaContactAngleFvPatchScalarField&,
            const DimensionedField<scalar, volMesh>&
        );

        virtual tmp<fvPatchField<scalar>> clone() const
        {
            return fvPatchField<scalar>::Clone(*this);
        }

        virtual tmp<fvPatchField<scalar>> clone
        (
            const DimensionedField<scalar, volMesh>& iF
        ) const
        {
            return fvPatchField<scalar>::Clone(*this, iF);
        }


    // Member functions

        //- Advancing limit [deg]
        scalar thetaA() const
        {
            return thetaA_;
        }

        //- Receding limit [deg]
        scalar thetaR() const
        {
            return thetaR_;
        }

        //- Apparent angle inside the window, the nearer limit outside it
        virtual tmp<scalarField> theta
        (
            const fvPatchVectorField& Up,
            const fvsPatchVectorField& nHat
        ) const;

        virtual void write(Ostream&) const;
};


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

} // End namespace Foam

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#endif

// ************************************************************************* //
