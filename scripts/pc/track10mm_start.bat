@echo off
REM (Re)start the 10 mm validation track hidden + keep-awake. Safe to double-click after a reboot:
REM it continues from the latest written time. Does nothing if the solver is already running.
title Laser Wire DED - 10 mm track start
wsl -d Ubuntu-24.04 -u dukyong -- bash -c "pgrep -f 'laserWireDEDFoam -parallel' >/dev/null"
if not errorlevel 1 (
  echo A laserWireDEDFoam run is already active - not starting another one.
  pause
  exit /b 0
)
powershell -NoProfile -Command "Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\Users\dukyo\laser_wire_ded_project\scripts\pc\launch_wsl_job.ps1','-Script','/mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/run_track10mm_fe_ni.sh'"
echo Started. Check progress with Track10mm_Status.bat
pause
