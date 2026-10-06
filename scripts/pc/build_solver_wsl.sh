#!/bin/bash
# Build the repo solver in WSL into ~/lwded_bin (keeps the older $FOAM_USER_APPBIN binary untouched).
# Compiles from a Linux-filesystem copy: on /mnt/c (case-insensitive) the solver's correctPhi.H
# shadows OpenFOAM's CorrectPhi.H and the build fails.
# Then: export PATH=$HOME/lwded_bin:$PATH
source /usr/lib/openfoam/openfoam2406/etc/bashrc
REPO=${REPO:-/mnt/c/Users/dukyo/laser_wire_ded_project}
B=${B:-$HOME/lwded_v2/solver_build}
mkdir -p $B
rsync -a --delete --exclude 'Make/linux64*' $REPO/solver/ $B/
cd $B || exit 1
export LWDED_APPBIN=${LWDED_APPBIN:-$HOME/lwded_bin}
./Allwmake > $B/build.log 2>&1; rc=$?
echo "BUILD_EXIT:$rc -> $LWDED_APPBIN/laserWireDEDFoam (log $B/build.log)"
exit $rc