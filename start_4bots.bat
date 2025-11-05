@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set BOT_DIR=%~dp0bots

echo ================================================================
echo  4-BOT DISTRIBUTED TELEGRAM SYSTEM
echo ================================================================
echo.

REM Check if bots directory exists
if not exist "%BOT_DIR%" (
    echo [ERROR] bots directory not found!
    echo Please run this script from the project root.
    pause
    exit /b 1
)

REM Change to bots directory
cd /d "%BOT_DIR%"

REM Run the bot starter
call start_bots.bat
