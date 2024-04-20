@echo off

where python >nul 2>nul
if %errorlevel% equ 0 (
    echo Python is already installed.
    goto :continue
)

echo Downloading Python...
curl -o python_installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe

echo Installing Python...
python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
del python_installer.exe

echo Python has been successfully installed.

:continue
echo Installing requests...
pip install requests

echo The requests package has been successfully installed.
echo Installing PyQt5...
pip install PyQt5

echo The PyQt5 package has been successfully installed.
echo Installing tqdm...
pip install tqdm

echo If only the Python download was completed, please rerun the .bat file to install the packages.
pause