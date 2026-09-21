@echo off
REM ===================================================================
REM  RL Tutor -- Windows launcher
REM
REM  Just double-click this file.
REM
REM  First run: creates a private virtual environment in .venv and
REM  installs PySide6 / numpy / matplotlib INTO IT. Nothing is installed
REM  into your system Python, so this cannot disturb anything you
REM  already have. Takes a minute or two and needs internet.
REM
REM  Every run after that starts instantly and works offline.
REM  To uninstall completely: delete this folder.
REM ===================================================================
setlocal
cd /d "%~dp0"

set "VENV=%~dp0.venv"
set "VPY=%VENV%\Scripts\python.exe"

REM --- if the venv already exists, just go ---------------------------
if exist "%VPY%" goto :run

REM --- otherwise find a Python to build it with -----------------------
echo.
echo   First run - setting up. This happens once.
echo.

set "PY="
for %%C in ("py -3" "python" "python3") do (
    if not defined PY (
        %%~C -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1
        if not errorlevel 1 set "PY=%%~C"
    )
)
if not defined PY (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    )
)

if not defined PY (
    echo.
    echo   ================================================================
    echo    Python 3.10 or newer was not found.
    echo.
    echo    Install it, then double-click this file again:
    echo.
    echo      Option A ^(easiest^):  open a terminal and run
    echo                            winget install Python.Python.3.12
    echo.
    echo      Option B:             https://www.python.org/downloads/
    echo                            TICK "Add python.exe to PATH"
    echo   ================================================================
    echo.
    pause
    exit /b 1
)

echo   Using: %PY%
echo   Creating virtual environment in .venv ...
%PY% -m venv "%VENV%"
if errorlevel 1 (
    echo.
    echo   ERROR: could not create the virtual environment.
    echo   On some systems you need:  %PY% -m pip install virtualenv
    pause
    exit /b 1
)

echo   Installing PySide6, numpy, matplotlib ...
"%VPY%" -m pip install --upgrade pip --quiet
"%VPY%" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo   ERROR: dependency install failed. Check your internet connection.
    pause
    exit /b 1
)
echo   Done.
echo.

:run
echo   Opening Control and RL Tutor ...
"%VPY%" -m app.main %*
if errorlevel 1 pause
endlocal
