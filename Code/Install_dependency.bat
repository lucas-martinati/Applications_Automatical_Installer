@echo off
setlocal enabledelayedexpansion

REM Check if Python is already installed
where python >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=2 delims=." %%i in ('python --version') do set python_version=%%i
    if !python_version! geq 8 (
        echo Python 3.8 or higher is already installed.
        goto :setup_venv
    )
)

echo Downloading Python...
curl -o python_installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe

echo Installing Python...
python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
if %errorlevel% neq 0 (
    echo Failed to install Python.
    goto :cleanup
)

echo Python has been successfully installed.

:setup_venv
echo Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment.
    goto :cleanup
)

echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment.
    goto :cleanup
)

echo Updating pip...
python -m pip install --upgrade pip

echo Installing required packages...
pip install -r Code/requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install required packages.
    goto :cleanup
)

echo All required packages have been successfully installed.

:cleanup
if exist python_installer.exe del python_installer.exe

echo Installation process complete.
pause
exit /b 0