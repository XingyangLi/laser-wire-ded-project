@echo off
REM Status of the 10 mm validation track (read-only): sim time, ETA (CT), pool, bead vs targets, metal/wire balance
title Laser Wire DED - 10 mm track status
wsl -d Ubuntu-24.04 -u dukyong -- python3 /mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/status_track10mm.py %1
echo.
echo Look at it live: Open_in_ParaView.bat track10mm_fe_ni   (mirrors the latest 12 written times)
echo Renders after the run: C:\Users\dukyo\laser_wire_ded\viz\track10mm_fe_ni\
pause
