@echo off
REM Sync reconstructed times from a WSL case to a Windows folder, then open ParaView
REM Usage: Open_in_ParaView.bat [caseName]   e.g.  Open_in_ParaView.bat gap_study_2mm
REM No name given: asks (Enter = val3mm_fe_ni_v2). Cases live in ~/laser_wire_ded_stranded (WSL).
title Laser Wire DED - ParaView
set CASE=%~1
if not "%CASE%"=="" goto have_case
echo Which case?  e.g. track10mm_fe_ni, val3mm_fe_ni_v2, gap_study_1mm
set /p CASE=Case name (Enter = val3mm_fe_ni_v2): 
if "%CASE%"=="" set CASE=val3mm_fe_ni_v2
:have_case
echo Syncing %CASE% for ParaView (about 10-30 s)...
if "%PV_ALL%"=="" set PV_ALL=0
wsl -d Ubuntu-24.04 -u dukyong -- env PV_ALL=%PV_ALL% bash /mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/sync_paraview_live.sh %CASE%
if errorlevel 1 (
  echo Sync failed.
  pause
  exit /b 1
)
set PV=C:\Program Files\ParaView 6.2.0\bin\paraview.exe
set FOAM=C:\Users\dukyo\laser_wire_ded_project\viz\paraview_live\case.foam
if not exist "%PV%" (
  echo ParaView not found at "%PV%"
  pause
  exit /b 1
)
echo Opening %FOAM%
echo In ParaView: Case Type = Reconstructed Case, check internalMesh, Apply.
echo Color by T or alpha.metal. Filters - Contour on alpha.metal=0.5 for a smooth surface.
start "" "%PV%" --data="%FOAM%"
