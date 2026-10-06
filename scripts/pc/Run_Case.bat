@echo off
REM Generate + mesh + solve a NEW case. Does NOT touch the live val3mm_fe_ni_v2 run.
title Laser Wire DED - Run Case
setlocal EnableDelayedExpansion

set REPO=C:\Users\dukyo\laser_wire_ded_project
set PC=%REPO%\scripts\pc

set RECIPE=%~1
set CASENAME=%~2
if "%RECIPE%"=="" set RECIPE=val3mm_fe_ni_v2
if "%CASENAME%"=="" set CASENAME=%RECIPE%_copy

echo.
echo ============================================
echo  Laser Wire DED - start a NEW simulation
echo ============================================
echo  Recipe : %RECIPE%
echo  Case   : %CASENAME%
echo.
echo  Results go to WSL:
echo    ~/laser_wire_ded_stranded/%CASENAME%
echo  Pictures go to:
echo    %REPO%\viz\%CASENAME%
echo.
echo  This does NOT stop or change the live val3mm_fe_ni_v2 run.
echo.

if /I "%CASENAME%"=="val3mm_fe_ni_v2" (
  echo ERROR: Refusing to overwrite the live case val3mm_fe_ni_v2.
  echo Choose another name, e.g. Run_Case.bat val3mm_fe_ni_v2 val3mm_fe_ni_v2b
  pause
  exit /b 2
)
if /I "%CASENAME%"=="full_transitional_r" (
  echo ERROR: Protected case name.
  pause
  exit /b 2
)

echo Press Enter to start, or Ctrl+C to cancel...
pause >nul

echo Launching in the background (PC stays awake)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PC%\launch_run_case.ps1" -Recipe "%RECIPE%" -CaseName "%CASENAME%"
set RC=%ERRORLEVEL%
echo.
if %RC% EQU 0 (
  echo Started. Check progress with Status.bat %CASENAME%
) else (
  echo Launch failed, exit code %RC%
)
echo.
pause
endlocal
exit /b %RC%
