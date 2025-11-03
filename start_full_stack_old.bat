@echo off
title 125 Build Automation - AI Document Analyzer
echo ==========================================================
echo 125 Build Automation - AI Document Analyzer (Enhanced)
echo Full-featured version with Korean language support
echo ==========================================================
echo.

cd /d "g:\Ddrive\BatangD\task\workdiary\125-build-automation-extend"

echo Current Directory: %CD%
echo.

echo Step 1/3: Backend preparation...
echo   - Checking environment...
cd backend
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('ENV: OK' if os.getenv('TELEGRAM_BOT_TOKEN') else 'ENV: MISSING')" 2>nul
echo   - Starting enhanced AI chatbot...
start cmd /k "cd /d g:\Ddrive\BatangD\task\workdiary\125-build-automation-extend\backend && python main_enhanced.py"
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
echo Enhanced AI Chatbot: Check new terminal window
echo Features: Document analysis, Korean language support
echo Stop frontend: Ctrl+C in this window
echo ==========================================================
echo.

cd frontend
npm run dev