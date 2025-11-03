@echo off
title 125 Build Automation - Full Stack (Unified)
echo ==========================================================
echo 125 Build Automation - Full Stack (Unified Version)
echo - FastAPI Backend (Port 8000)
echo - Next.js Frontend (Port 3000, proxied via /api/*)
echo - Telegram Bot (Separated Process)
echo ==========================================================
echo.

cd /d "g:\Ddrive\BatangD\task\workdiary\125-build-automation-extend"

echo Current Directory: %CD%
echo.

echo Step 1/3: Backend preparation...
echo   - Checking environment...
cd backend
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('ENV: OK' if os.getenv('GEMINI_API_KEY') else 'ENV: MISSING GEMINI_API_KEY')" 2>nul
echo   - Starting FastAPI backend on port 8000...
start cmd /k "cd /d g:\Ddrive\BatangD\task\workdiary\125-build-automation-extend\backend && python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0"
cd ..

echo.
echo Step 2/3: Frontend preparation...
cd frontend
if not exist node_modules (
    echo   Installing dependencies...
    npm install
)
cd ..

echo.
echo Step 3/3: Starting frontend...
echo ==========================================================
echo Frontend URL: http://localhost:3000
echo Backend API: Proxied through /api/* (No port needed!)
echo Telegram Bot: Check new terminal window
echo Features: API Key Verification + AI Document Analysis
echo Stop frontend: Ctrl+C in this window
echo ==========================================================
echo.

cd frontend
npm run dev

echo.
echo ==========================================================
echo All services stopped
echo ==========================================================
pause
