@echo off
REM Model-setup studio: geometry view and parameter tuning. Solver is unchanged.
setlocal
set PY=C:\Users\dukyo\AppData\Local\Programs\Python\Python311\python.exe
if not exist "%PY%" set PY=py
cd /d "%~dp0"
echo Opening the model studio in your browser.
echo Leave this window open. Closing it closes the studio, not a running solver.
"%PY%" "%~dp0studio_server.py"
if errorlevel 1 pause
endlocal
