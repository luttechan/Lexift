@echo off
setlocal
cd /d "%~dp0" || exit /b 1
if exist "%~dp0dist\Lexift\Lexift.exe" (
  start "" "%~dp0dist\Lexift\Lexift.exe" --show
  exit /b 0
)
if not exist ".venv\Scripts\python.exe" goto install_first
if not exist ".venv\Scripts\pythonw.exe" goto install_first
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0launch.pyw" --show
exit /b 0
:install_first
echo [Lexift] Required .venv environment is missing.
echo Run install.bat first.
pause
exit /b 1
