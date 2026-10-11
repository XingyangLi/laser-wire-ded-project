@echo off
REM Start one wiggle track (0.5 or 1.0). Hidden + keep-awake. Refuses to start if a solver is already running.
setlocal
set MM=%~1
if "%MM%"=="" set MM=0.5
if "%MM%"=="0.5" (
  set TAG=05
  set SCRIPT=/mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/run_wiggle05mm_10mm.sh
) else if "%MM%"=="1.0" (
  set TAG=10
  set SCRIPT=/mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/run_wiggle10mm_10mm.sh
) else if "%MM%"=="1" (
  set TAG=10
  set SCRIPT=/mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/run_wiggle10mm_10mm.sh
) else (
  echo Use: wiggle_start.bat 0.5    or    wiggle_start.bat 1.0
  exit /b 1
)
title Laser Wire DED - %MM% mm wiggle
wsl -d Ubuntu-24.04 -u dukyong -- bash -c "pgrep -f '[l]aserWireDEDFoam -parallel' >/dev/null"
if not errorlevel 1 (
  echo A laserWireDEDFoam run is already active - not starting another one.
  echo The 0.5 mm and 1.0 mm wiggles share the same 8 cores. Run the second after the first finishes.
  pause
  exit /b 0
)
if not exist "C:\Users\dukyo\laser_wire_ded\viz\wiggle%TAG%mm_10mm" mkdir "C:\Users\dukyo\laser_wire_ded\viz\wiggle%TAG%mm_10mm"
powershell -NoProfile -Command "Start-Process powershell -WindowStyle Hidden -RedirectStandardOutput 'C:\Users\dukyo\laser_wire_ded\viz\wiggle%TAG%mm_10mm\launcher_out.txt' -RedirectStandardError 'C:\Users\dukyo\laser_wire_ded\viz\wiggle%TAG%mm_10mm\launcher_err.txt' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\Users\dukyo\laser_wire_ded_project\scripts\pc\launch_wsl_job.ps1','-Script','%SCRIPT%'"
echo Started the %MM% mm wiggle (10 mm of travel, long plate). Case folder: wiggle%TAG%mm_10mm
echo Check progress with Wiggle_Status.bat
pause
endlocal
