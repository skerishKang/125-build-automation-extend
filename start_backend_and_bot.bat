@echo off
title 125 Build Automation - Dino Zoo API Explorer

echo ========================================================
echo 125 Build Automation - Dino Zoo API Explorer
echo ========================================================
echo.

cd /d "G:\Ddrive\BatangD\task\workdiary\125-build-automation-extend"

echo Starting Backend (FastAPI) on port 8000...
start "Backend" cmd /k "cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo Waiting 5 seconds for backend to initialize...
timeout /t 5 /nobreak > nul

echo.
echo Starting Telegram Bot...
start "TelegramBot" cmd /k "cd backend && python bot_runner.py"

echo.
echo Waiting 3 seconds for bot to initialize...
timeout /t 3 /nobreak > nul

echo.
echo Starting Frontend (Next.js) on port 3000...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo All services started successfully!
echo ========================================================
echo.
echo Backend API:        http://localhost:8000
echo API Documentation:  http://localhost:8000/docs
echo Frontend:           http://localhost:3000
echo.
echo Press any key to exit...
pause > nul
