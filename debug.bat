@echo off
setlocal
cd /d "%~dp0" || exit /b 1
set "PYTHONFAULTHANDLER=1"
if not exist ".venv\Scripts\python.exe" goto fail
"%~dp0.venv\Scripts\python.exe" "%~dp0launch.pyw" --show
set "CODE=%ERRORLEVEL%"
echo.
echo KanaShift exit code: %CODE%
echo App log: %LOCALAPPDATA%\KanaShift\kanashift.log
echo Startup error log: %LOCALAPPDATA%\KanaShift\startup-error.log
pause
exit /b %CODE%
:fail
echo Run install.bat first.
pause
exit /b 1
