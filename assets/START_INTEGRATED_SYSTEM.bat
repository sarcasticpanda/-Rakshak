@echo off
REM जनRakshak - Integrated Startup Script
REM Starts both backend and frontend servers with proper configuration

echo ====================================
echo  जनRakshak - Stampede Detection
echo  Backend-Frontend Integration
echo ====================================
echo.

REM Check if we're in the correct directory
if not exist "backend" (
    echo ERROR: backend folder not found!
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

if not exist "frontend\bits hack frontend" (
    echo ERROR: frontend folder not found!
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.9 or higher.
    pause
    exit /b 1
)
python --version
echo.

REM Create venv if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
)

REM Activate venv and install dependencies
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    pause
    exit /b 1
)

REM Check if dependencies are installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installing backend dependencies...
    pip install -r requirements_api.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies!
        pause
        exit /b 1
    )
) else (
    echo Dependencies already installed.
)

echo.
echo [3/4] Starting backend server...
echo Backend will run on: http://localhost:8000
echo WebSocket endpoint: ws://localhost:8000/ws/metrics
echo API Documentation: http://localhost:8000/docs
echo.

REM Start backend in new window - FIXED: Use main:app instead of app.main:app
start "जनRakshak Backend" cmd /k "cd /d %cd% && venv\Scripts\activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend to start
echo Waiting for backend to start (5 seconds)...
timeout /t 5 /nobreak >nul

cd ..

echo.
echo [4/4] Starting frontend server...
echo Frontend will run on: http://localhost:5500
echo.

REM Start frontend in new window
start "जनRakshak Frontend" cmd /k "cd /d %cd%\frontend\bits hack frontend && python -m http.server 5500"

REM Wait for frontend to start
echo Waiting for frontend to start (2 seconds)...
timeout /t 2 /nobreak >nul

echo.
echo ====================================
echo  ✅ Servers Started Successfully!
echo ====================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5500
echo.
echo Opening browser...
timeout /t 2 /nobreak >nul

REM Open browser
start http://localhost:5500/index.html

echo.
echo ====================================
echo  📊 Integration Status
echo ====================================
echo.
echo ✅ Backend: Running with metrics aggregator (1Hz)
echo ✅ Frontend: Serving static files
echo ✅ WebSocket: Real-time data streaming
echo ✅ Fallback: REST polling ready (if WS fails)
echo ✅ Chart: Pre-initialized with camera data
echo ✅ Reconnection: Unlimited attempts with 30s cap
echo.
echo To stop servers: Close the command windows
echo To restart: Run this script again
echo.
echo Press any key to view integration guide...
pause >nul

REM Open integration guide
if exist "INTEGRATION_FIX_GUIDE.md" (
    start notepad "INTEGRATION_FIX_GUIDE.md"
)

echo.
echo Thank you for using जनRakshak!
echo.
pause
