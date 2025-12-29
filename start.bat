@echo off
echo Starting Travel Planner AI...
cd /d "%~dp0"

REM Start Backend
start "Backend - Flask" cmd /k "cd /d "%~dp0backend" && venv\Scripts\activate.bat && python app.py"

REM Wait for backend to start
timeout /t 3 /nobreak

REM Start Frontend
start "Frontend - Server" cmd /k "cd /d "%~dp0frontend" && python -m http.server 8000"

REM Wait for frontend to start
timeout /t 2 /nobreak

REM Open Browser
start http://localhost:8000

echo.
echo Backend: http://127.0.0.1:5000
echo Frontend: http://localhost:8000
echo.
echo Both servers are running. Do not close these windows!
