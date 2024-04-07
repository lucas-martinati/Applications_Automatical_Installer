@echo off

where python >nul 2>nul
if %errorlevel% equ 0 (
    echo Python est deja installe.
    goto :continue
)

echo Telechargement de Python...
curl -o python_installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe

echo Installation de Python...
python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
del python_installer.exe

echo Python a ete installe avec succes.

:continue
echo Installation de requests...
pip install requests

echo Le package requests a ete installe avec succes.
echo Installation de PyQt5...
pip install PyQt5

echo Le package PyQt5 a ete installe avec succes.
echo Installation de tqdm...
pip install tqdm

echo si seul le telechargement de python a etait effectuer, veuillez relancer le .bat pour installer les packages
pause