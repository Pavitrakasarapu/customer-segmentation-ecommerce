@echo off
setlocal enabledelayedexpansion
title Customer Segmentation E-Commerce Test Suite

echo =====================================================================
echo    CUSTOMER SEGMENTATION E-COMMERCE - AUTOMATED TEST RUNNER
echo =====================================================================
echo.

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11+ is not found in PATH!
    echo Please ensure Python is installed and added to PATH.
    pause
    exit /b 1
)

:: 2. Activate virtual environment if present
if exist ".venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment: .venv
    call .venv\Scripts\activate.bat
) else (
    echo [!] Virtual environment .venv not found. Using system python...
)

:: 3. Run automated pytest suite
echo [*] Running automated test suite with pytest...
echo.
python -m pytest -v
set TEST_RESULT=%errorlevel%

echo.
echo =====================================================================
if %TEST_RESULT% equ 0 (
    echo  [SUCCESS] All automated tests passed successfully!
) else (
    echo  [FAILURE] Tests finished with failures. Exit code: %TEST_RESULT%
)
echo =====================================================================
echo.
pause
exit /b %TEST_RESULT%
