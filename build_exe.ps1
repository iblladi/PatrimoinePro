# Rebuild PatrimoinePro (Windows, mode dossier).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File build_exe.ps1
# Requires: Python 3.11+ available as "python" on PATH, network access for PyInstaller.
#
# Note: the application is built as a FOLDER (exe + _internal) and not as a
# single self-extracting file. A one-file build unpacks itself into %TEMP% at
# every launch, which fails on some machines (antivirus, restricted temp,
# OneDrive-synced folders) with "Could not create temporary directory!".

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

Write-Host "[1/3] Installation de PyInstaller dans .build\libs ..."
$env:PYTHONPATH = Join-Path $root ".build\libs"
if (-not (Test-Path (Join-Path $env:PYTHONPATH "PyInstaller"))) {
    python -m pip install --no-cache-dir --disable-pip-version-check --target $env:PYTHONPATH pyinstaller
}

Write-Host "[2/3] Compilation ..."
python -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name PatrimoinePro `
    --contents-directory "_internal" `
    --icon (Join-Path $root "assets\icon.ico") `
    --add-data ((Join-Path $root "assets") + ";assets") `
    --distpath (Join-Path $root ".build\dist") `
    --workpath (Join-Path $root ".build\work") `
    --specpath (Join-Path $root ".build") `
    (Join-Path $root "PatrimoinePro.pyw")

Write-Host "[3/3] Copie de l'application ..."
$dist = Join-Path $root ".build\dist\PatrimoinePro"
Copy-Item (Join-Path $dist "PatrimoinePro.exe") (Join-Path $root "PatrimoinePro.exe") -Force
if (Test-Path (Join-Path $root "_internal")) {
    Remove-Item (Join-Path $root "_internal") -Recurse -Force
}
Copy-Item (Join-Path $dist "_internal") (Join-Path $root "_internal") -Recurse -Force
Write-Host ("OK - " + (Get-Item (Join-Path $root "PatrimoinePro.exe")).Length + " octets + _internal")
