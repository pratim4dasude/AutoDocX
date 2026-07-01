@echo off
setlocal EnableExtensions

title Stop AutoDocX

set "PORT=8000"
set "PROCESS_FOUND=0"

echo.
echo ============================================
echo              Stopping AutoDocX
echo ============================================
echo.

for /f "tokens=5" %%P in (
    'netstat -aon ^| findstr ":%PORT%" ^| findstr "LISTENING"'
) do (
    set "PROCESS_FOUND=1"

    echo Stopping process %%P...

    taskkill /PID %%P /F >nul 2>&1
)

if "%PROCESS_FOUND%"=="0" (
    echo No AutoDocX server was found on port %PORT%.
) else (
    echo AutoDocX was stopped.
)

echo.
pause