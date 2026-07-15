@echo off
setlocal EnableExtensions

title AutoDocX Installer

set "SCRIPTS_DIR=%~dp0"
set "ROOT=%SCRIPTS_DIR%..\"
set "SETUP_SCRIPT=%SCRIPTS_DIR%setup_runtime.ps1"
set "PRIVATE_PYTHON=%ROOT%runtime\python\python.exe"

echo.
echo ============================================
echo             AutoDocX Installer
echo ============================================
echo.
echo AutoDocX will create its own private Python.
echo.
echo It will not modify:
echo - Your global Python
echo - Your system PATH
echo - Your existing virtual environments
echo - Your globally installed Python packages
echo.

if not exist "%SETUP_SCRIPT%" (
    echo [ERROR] Setup script was not found.
    echo.
    echo Expected file:
    echo %SETUP_SCRIPT%
    echo.
    pause
    exit /b 1
)

if exist "%PRIVATE_PYTHON%" (
    echo An AutoDocX private runtime already exists.
    echo.

    choice /C YN /M "Do you want to reinstall it"

    if errorlevel 2 (
        echo.
        echo Existing runtime was kept.
        echo Run AutoDocX.bat to launch AutoDocX.
        echo.
        pause
        exit /b 0
    )
)

echo Starting private runtime setup...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SETUP_SCRIPT%"

if errorlevel 1 (
    echo.
    echo ============================================
    echo          AutoDocX Installation Failed
    echo ============================================
    echo.
    echo Review the error shown above.
    echo Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

if not exist "%PRIVATE_PYTHON%" (
    echo.
    echo [ERROR] Private Python was not created.
    echo.
    echo Expected file:
    echo %PRIVATE_PYTHON%
    echo.
    pause
    exit /b 1
)

if not exist "%ROOT%workspace" mkdir "%ROOT%workspace"
if not exist "%ROOT%workspace\scans" mkdir "%ROOT%workspace\scans"
if not exist "%ROOT%workspace\understandings" mkdir "%ROOT%workspace\understandings"
if not exist "%ROOT%workspace\documents" mkdir "%ROOT%workspace\documents"

echo.
echo ============================================
echo       AutoDocX Installed Successfully
echo ============================================
echo.
echo Private Python:
echo %PRIVATE_PYTHON%
echo.
echo Run AutoDocX.bat to launch AutoDocX.
echo.

pause
exit /b 0
