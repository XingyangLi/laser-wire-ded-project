@echo off
title Laser Wire DED - wiggle status
wsl -d Ubuntu-24.04 -u dukyong -- python3 /mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/status_wiggle.py
echo.
echo Pictures while it runs:  Open_in_ParaView.bat wiggle05mm_10mm
echo                          Open_in_ParaView.bat wiggle10mm_10mm
pause
