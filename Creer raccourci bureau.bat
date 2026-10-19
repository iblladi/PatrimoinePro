@echo off
rem Cree un raccourci "PatrimoinePro" sur le Bureau.
setlocal
set "TARGET=%~dp0PatrimoinePro.exe"
if not exist "%TARGET%" (
  echo PatrimoinePro.exe est introuvable dans ce dossier.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $lnk=$ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'PatrimoinePro.lnk')); $lnk.TargetPath='%TARGET%'; $lnk.WorkingDirectory='%~dp0'; $lnk.IconLocation='%TARGET%,0'; $lnk.Description='Gestion de portefeuille et projets d epargne'; $lnk.Save()"
if errorlevel 1 (
  echo Echec de la creation du raccourci.
) else (
  echo Raccourci PatrimoinePro cree sur le Bureau.
)
pause
