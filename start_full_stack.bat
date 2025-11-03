@echo off
title 125 Build Automation - Telegram Bot Only

echo Killing existing bot window...
taskkill /fi "windowtitle eq TelegramBotRunner" /im cmd.exe /f 2>nul
echo.

echo ==========================================================
echo 125 Build Automation - Telegram Bot Only
echo ==========================================================
echo.

cd /d "g:\Ddrive\BatangD\task\workdiary\125-build-automation-extend"

echo Current Directory: %CD%
echo.

echo Starting Telegram Bot...
start "TelegramBotRunner" cmd /k "cd /d g:\Ddrive\BatangD\task\workdiary\125-build-automation-extend && python backend/bot_runner.py"

echo.
echo ==========================================================
echo Telegram Bot started in a new window.
echo Please start the backend and frontend manually.
echo ==========================================================
pause
