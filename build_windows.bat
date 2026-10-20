@echo off
setlocal
cd /d "%~dp0" || exit /b 1
set "PATH=%SystemRoot%\System32;%SystemRoot%;%~dp0.venv\Scripts;%PATH%"
if not exist ".venv\Scripts\python.exe" goto install_first
"%~dp0.venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto fail
"%~dp0.venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm --noupx --onedir --windowed --name KanaShift --contents-directory module --paths module --workpath module/build --specpath module --icon "%~dp0module\kanashift.ico" --add-data "%~dp0module\Style;Style" launch.pyw
if errorlevel 1 goto fail
"%~dp0.venv\Scripts\python.exe" module/build_release.py
if errorlevel 1 goto fail
echo.
echo Built: dist\KanaShift\KanaShift.exe
pause
exit /b 0
:install_first
echo Run install.bat before building KanaShift.
pause
exit /b 1
:fail
echo Build failed. Check the messages above.
pause
exit /b 1
