@echo off
setlocal EnableExtensions

title Stop AutoDocX

set "FOUND=0"

echo.
echo ============================================
echo              Stopping AutoDocX
echo ============================================
echo.

for /f "tokens=5" %%P in (
    'netstat -aon ^| findstr ":7832 " ^| findstr "LISTENING"'
) do (
    set "FOUND=1"
    echo Stopping backend   (PID %%P)...
    taskkill /PID %%P /F >nul 2>&1
)

for /f "tokens=5" %%P in (
    'netstat -aon ^| findstr ":7833 " ^| findstr "LISTENING"'
) do (
    set "FOUND=1"
    echo Stopping Streamlit (PID %%P)...
    taskkill /PID %%P /F >nul 2>&1
)

if "%FOUND%"=="0" (
    echo No AutoDocX processes found on ports 7832 or 7833.
) else (
    echo Done.
)

echo.
pause
