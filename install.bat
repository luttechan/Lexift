@echo off
setlocal
cd /d "%~dp0" || exit /b 1
if exist ".venv\Scripts\python.exe" goto deps
where py.exe >nul 2>&1
if errorlevel 1 goto no_python
py -3 -m venv .venv
if errorlevel 1 goto fail
:deps
"%~dp0.venv\Scripts\python.exe" -m pip install -r module/requirements.txt
if errorlevel 1 goto fail
echo.
echo Lexift dependencies installed.
pause
exit /b 0
:no_python
echo Python 3.10+ is required. Install Python for Windows first.
pause
exit /b 1
:fail
echo Installation failed. See the error above.
pause
exit /b 1
