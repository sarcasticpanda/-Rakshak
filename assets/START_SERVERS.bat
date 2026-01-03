@echo off
echo ====================================
echo जनRakshak Stampede Detection System
echo ====================================
echo.
echo Starting Backend Server (Port 8000)...
start "Backend Server" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo Starting Frontend Server (Port 5500)...
start "Frontend Server" cmd /k "cd /d "%~dp0frontend\bits hack frontend" && python -m http.server 5500"

timeout /t 2 /nobreak >nul

echo.
echo ====================================
echo ✅ Both servers started!
echo ====================================
echo.
echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:5500/index.html
echo.
echo Press any key to open the dashboard...
pause >nul

start http://localhost:5500/index.html
