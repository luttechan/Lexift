@echo off
setlocal
cd /d "%~dp0" || exit /b 1
set "PATH=%SystemRoot%\System32;%SystemRoot%;%~dp0.venv\Scripts;%PATH%"
if not exist ".venv\Scripts\python.exe" goto install_first
"%~dp0.venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto fail
if defined KANASHIFT_ZIG powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0lab\build.ps1" -Zig "%KANASHIFT_ZIG%"
if errorlevel 1 goto fail
if not exist "%~dp0lab\ime_candidate_host.exe" goto fail
"%~dp0.venv\Scripts\python.exe" module/build_native_hooks.py
if errorlevel 1 goto fail
"%~dp0.venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm --distpath dist --workpath module/build module/Lexift.spec
if errorlevel 1 goto fail
"%~dp0.venv\Scripts\python.exe" module/build_release.py
if errorlevel 1 goto fail
echo.
echo Built: dist\Lexift\Lexift.exe
pause
exit /b 0
:install_first
echo Run install.bat before building Lexift.
pause
exit /b 1
:fail
echo Build failed. Check the messages above.
pause
exit /b 1
