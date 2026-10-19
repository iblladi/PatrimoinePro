@echo off
rem Lance PatrimoinePro avec le Python installe sur la machine.
setlocal
cd /d "%~dp0"
where pythonw >nul 2>&1
if errorlevel 1 goto trypython
start "" pythonw "PatrimoinePro.pyw"
exit /b 0

:trypython
where python >nul 2>&1
if errorlevel 1 goto nopython
start "" python "PatrimoinePro.pyw"
exit /b 0

:nopython
echo.
echo Python n'est pas installe sur cet ordinateur.
echo Utilisez plutot PatrimoinePro.exe (application autonome).
echo.
pause
