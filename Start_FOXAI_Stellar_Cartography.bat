@echo off
setlocal enabledelayedexpansion
title FOXAI Stellar Cartography R0.4.0

echo ============================================================
echo  FOXAI Stellar Cartography R0.4.0
echo ============================================================
echo.

cd /d "%~dp0"

set PYTHON_CMD=

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYTHON_CMD=py -3
    goto :found_python
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYTHON_CMD=python
    goto :found_python
)

echo [ERROR] Python 3 was not found on this system.
echo Please install Python 3.9 or newer from https://www.python.org/downloads/
echo and make sure "Add python.exe to PATH" is checked during setup.
echo.
pause
exit /b 1

:found_python
echo Using: %PYTHON_CMD%
echo.
echo Starting FOXAI Stellar Cartography and opening your browser...
echo (This window must stay open while you use the app. Close it to stop.)
echo.

%PYTHON_CMD% run.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] The app exited with an error. See the messages above.
    pause
    exit /b 1
)

pause
