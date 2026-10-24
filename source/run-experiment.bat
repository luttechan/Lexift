@echo off
setlocal
cd /d "%~dp0" || exit /b 1
if exist ".venv\Scripts\pythonw.exe" (
  start "" "%~dp0.venv\Scripts\pythonw.exe" -B "%~dp0launch.pyw" --show
  exit /b 0
)
set "EXPERIMENT_PYTHON=C:\Users\Neko4K\Documents\Codex\2026-10-21\g-ankivoice-ankivoice-extended-release-v\work\build-env\Scripts\pythonw.exe"
if exist "%EXPERIMENT_PYTHON%" (
  start "" "%EXPERIMENT_PYTHON%" -B "%~dp0launch.pyw" --show
  exit /b 0
)
echo Run install.bat first, then run.bat.
pause
exit /b 1
