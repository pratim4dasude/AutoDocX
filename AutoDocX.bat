@echo off
setlocal EnableExtensions

title AutoDocX

set "ROOT=%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\run_autodocx.ps1"

if errorlevel 1 (
    echo.
    echo [ERROR] AutoDocX exited with an error.
    echo.
    pause
)
