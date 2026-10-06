@echo off
REM Open any OpenFOAM case folder that has (or will get) a case.foam marker.
REM Usage: drag a case folder onto this bat, or: open_any_foam_case.bat <path>
setlocal
if "%~1"=="" (
  echo Usage: open_any_foam_case.bat ^<case-folder-or-case.foam^>
  echo Example: open_any_foam_case.bat \\wsl.localhost\Ubuntu-24.04\home\dukyong\laser_wire_ded_stranded\val3mm_fe_ni_v2
  echo Or drag a case folder onto this shortcut.
  pause
  exit /b 1
)
set "SCRIPT=%~dp0open_in_paraview.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" "%~1"
