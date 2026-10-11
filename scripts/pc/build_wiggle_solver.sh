#!/bin/bash
# Solver that knows the y-zigzag, installed beside the track10mm binary so a running job is not replaced.
export REPO=/mnt/c/Users/dukyo/laser_wire_ded_project
export B=$HOME/lwded_wiggle/solver_build
export LWDED_APPBIN=$HOME/lwded_bin_wiggle
bash "$REPO/scripts/pc/build_solver_wsl.sh"
