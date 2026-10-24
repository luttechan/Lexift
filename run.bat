@echo off
setlocal
cd /d "%~dp0" || exit /b 1
if not exist "%~dp0app\Lexift.exe" exit /b 1
start "" "%~dp0app\Lexift.exe" --show
