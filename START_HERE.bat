@echo off
REM Quick Start Script for Championship Analysis Tool
REM Double-click this file to run the analysis tool

echo.
echo ============================================================
echo   CHAMPIONSHIP ANALYSIS TOOL - QUICK START
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv\" (
    echo Setting up virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing required packages...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo Starting analysis tool...
echo.

REM Run the interactive tool
python analyze_team.py

echo.
pause
