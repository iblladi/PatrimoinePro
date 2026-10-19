@echo off
rem Installe PatrimoinePro dans le profil utilisateur et cree un raccourci sur le Bureau.
rem Recommande si le dossier de l'application est synchronise par OneDrive.
setlocal
set "SRC=%~dp0"
set "DEST=%LOCALAPPDATA%\Programs\PatrimoinePro"

echo.
echo   Installation de PatrimoinePro
echo   -----------------------------
echo   Destination : %DEST%
echo.

if not exist "%SRC%PatrimoinePro.exe" goto missing
if not exist "%SRC%_internal" goto missing

if not exist "%DEST%" mkdir "%DEST%" >nul 2>&1
copy /Y "%SRC%PatrimoinePro.exe" "%DEST%\PatrimoinePro.exe" >nul
if errorlevel 1 goto fail
xcopy "%SRC%_internal" "%DEST%\_internal" /E /I /Y /Q >nul
if errorlevel 1 goto fail

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $lnk=$ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'PatrimoinePro.lnk')); $lnk.TargetPath='%DEST%\PatrimoinePro.exe'; $lnk.WorkingDirectory='%DEST%'; $lnk.IconLocation='%DEST%\PatrimoinePro.exe,0'; $lnk.Description='Gestion de portefeuille et projets d epargne'; $lnk.Save()"

echo   Installation terminee.
echo   Un raccourci "PatrimoinePro" a ete cree sur le Bureau.
echo   Vos donnees restent dans %%APPDATA%%\PatrimoinePro.
echo.
start "" "%DEST%\PatrimoinePro.exe"
pause
exit /b 0

:missing
echo   ERREUR : PatrimoinePro.exe ou le dossier _internal est introuvable.
echo   Lancez ce fichier depuis le dossier complet de l'application.
echo.
pause
exit /b 1

:fail
echo   ERREUR pendant la copie des fichiers.
echo.
pause
exit /b 1
