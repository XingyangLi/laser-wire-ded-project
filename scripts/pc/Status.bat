@echo off
REM Show status of a WSL case (default: live val3mm_fe_ni_v2)
title Laser Wire DED - Status
set CASE=%~1
if "%CASE%"=="" set CASE=val3mm_fe_ni_v2
echo Status for case: %CASE%
echo.
wsl -d Ubuntu-24.04 -u dukyong -- bash /mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/status_any.sh %CASE%
echo.
pause
