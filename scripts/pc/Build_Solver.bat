@echo off
REM Build the OpenFOAM solver from this repo into WSL ~/lwded_bin
title Laser Wire DED - Build Solver
set REPO=C:\Users\dukyo\laser_wire_ded_project
echo.
echo Building solver from %REPO%\solver
echo Output binary: WSL ~/lwded_bin/laserWireDEDFoam
echo This takes a few minutes. Leave this window open.
echo.
wsl -d Ubuntu-24.04 -u dukyong -- bash /mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/build_solver_wsl.sh
set RC=%ERRORLEVEL%
echo.
if %RC% EQU 0 (
  echo BUILD OK. Binary is at ~/lwded_bin/laserWireDEDFoam
) else (
  echo BUILD FAILED. See ~/lwded_v2/solver_build/build.log in WSL.
)
echo.
pause
exit /b %RC%
