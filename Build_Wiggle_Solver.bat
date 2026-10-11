@echo off
title Laser Wire DED - build wiggle solver
echo Building the solver that can zigzag the laser and the wire.
echo It goes to a separate folder, so a run that is already going keeps its own program.
wsl -d Ubuntu-24.04 -u dukyong -- bash /mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/build_wiggle_solver.sh
echo.
if errorlevel 1 (
  echo Build failed. The log is in WSL: ~/lwded_wiggle/solver_build/build.log
) else (
  echo Build finished. Start a track with Wiggle05_Start.bat or Wiggle10_Start.bat
)
pause
