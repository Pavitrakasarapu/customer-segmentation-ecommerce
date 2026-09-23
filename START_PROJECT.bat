@echo off
setlocal enabledelayedexpansion
title Customer Segmentation E-Commerce Launcher

echo =====================================================================
echo    CUSTOMER SEGMENTATION E-COMMERCE - ONE-CLICK LOCAL LAUNCHER
echo =====================================================================
echo.

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11+ is not found in PATH!
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [1/10] Found %PYTHON_VERSION%

:: 2. Create virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
    echo [2/10] Creating Python virtual environment in .venv...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [2/10] Virtual environment already exists: .venv
)

:: 3. Activate venv
echo [3/10] Activating virtual environment...
call .venv\Scripts\activate.bat

:: 4. Install / Verify requirements
echo [4/10] Checking and installing requirements...
python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [WARNING] Package installation encountered issues. Continuing with existing packages...
)

:: 5. Create database directory
if not exist "instance" (
    mkdir instance
)

:: 6. Seed catalog data if database does not exist
if not exist "instance\customer_segmentation.db" (
    echo [6/10] Database not found. Seeding product catalog and admin account...
    python seed.py
) else (
    echo [6/10] Database detected: instance\customer_segmentation.db. Safe to proceed.
)

:: 7. Initialize ML Segmenter
if not exist "ml\artifacts\kmeans_model.joblib" (
    echo [7/10] Initializing behavioral ML segmentation engine...
    python train_model.py
) else (
    echo [7/10] Behavioral ML segmentation engine ready.
)

:: 8. Create / Verify Administrator
echo [8/10] Verifying Administrator account...
python create_admin.py --email pavitrakasarapu@gmail.com --password Admin@123 --name "Administrator"

:: 9. Run automated test suite
echo [9/10] Running automated verification tests...
python -m pytest -q
if %errorlevel% neq 0 (
    echo [WARNING] Some tests reported warnings or failures. Review above.
) else (
    echo        All automated tests passed successfully!
)

:: 10. Start Flask Server and Open Browser
echo [10/10] Starting Flask application on http://127.0.0.1:5000 ...
echo.
echo =====================================================================
echo  SERVER URL : http://127.0.0.1:5000
echo.
echo  ADMIN CREDENTIALS:
echo    - Administrator : pavitrakasarapu@gmail.com / Admin@123
echo.
echo  REAL CUSTOMERS:
echo    - Register a real customer profile at http://127.0.0.1:5000/register
echo    - Real browsing, searches, cart, and orders update analytics live!
echo.
echo  Press Ctrl+C in this terminal window to stop the server.
echo =====================================================================
echo.

:: Open default browser in 2 seconds in background
start /min cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:5000"

:: Start the Flask app
python app.py
pause
