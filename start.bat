@echo off
setlocal EnableExtensions

title AutoDocX

set "ROOT=%~dp0"
set "PYTHON=%ROOT%runtime\python\python.exe"
set "HOST=127.0.0.1"
set "PORT=8000"
set "URL=http://%HOST%:%PORT%"

echo.
echo ============================================
echo              Starting AutoDocX
echo ============================================
echo.

if not exist "%PYTHON%" (
    echo AutoDocX private runtime is not installed.
    echo.
    echo Starting automatic installation...
    echo.

    call "%ROOT%install.bat"

    if errorlevel 1 (
        echo.
        echo [ERROR] AutoDocX installation failed.
        echo.
        pause
        exit /b 1
    )
)

if not exist "%PYTHON%" (
    echo.
    echo [ERROR] Private Python is still missing.
    echo Run install.bat manually and check the error.
    echo.
    pause
    exit /b 1
)

echo Verifying dependencies...

"%PYTHON%" -c "import fastapi, uvicorn" >nul 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] AutoDocX dependencies are missing.
    echo Run install.bat and reinstall the runtime.
    echo.
    pause
    exit /b 1
)

cd /d "%ROOT%"

echo.
echo AutoDocX URL:
echo %URL%
echo.
echo API documentation:
echo %URL%/docs
echo.
echo Press CTRL+C to stop AutoDocX.
echo.

start "" powershell.exe ^
    -NoProfile ^
    -WindowStyle Hidden ^
    -Command "Start-Sleep -Seconds 2; Start-Process '%URL%'"

"%PYTHON%" -m uvicorn app.main:app ^
    --host %HOST% ^
    --port %PORT%

echo.
echo AutoDocX stopped.
echo.

pause