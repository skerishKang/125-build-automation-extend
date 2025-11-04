@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo ========================================
echo  125 Build Automation - Telegram Bot
echo ========================================
echo.
echo Starting Telegram Bot (MiniMax API)...
echo.
cd /d "%~dp0"
python backend/bot_runner.py
pause
