@echo off
REM Install dependencies for all 4 bots

echo ==========================================
echo 🤖 4-Bot Telegram System - Dependency Installer
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.11 or higher.
    pause
    exit /b 1
)

echo ✅ Python found
python --version
echo.

REM Function to install dependencies for a bot
echo Installing dependencies for Main Bot...
echo ----------------------------------------
pip install -r main_bot\requirements.txt
if %errorlevel% equ 0 (
    echo ✅ Main Bot dependencies installed successfully
) else (
    echo ❌ Failed to install Main Bot dependencies
    pause
    exit /b 1
)
echo.

echo Installing dependencies for Document Bot...
echo ----------------------------------------
pip install -r document_bot\requirements.txt
if %errorlevel% equ 0 (
    echo ✅ Document Bot dependencies installed successfully
) else (
    echo ❌ Failed to install Document Bot dependencies
    pause
    exit /b 1
)
echo.

echo Installing dependencies for Audio Bot...
echo ----------------------------------------
pip install -r audio_bot\requirements.txt
if %errorlevel% equ 0 (
    echo ✅ Audio Bot dependencies installed successfully
) else (
    echo ❌ Failed to install Audio Bot dependencies
    pause
    exit /b 1
)
echo.

echo Installing dependencies for Image Bot...
echo ----------------------------------------
pip install -r image_bot\requirements.txt
if %errorlevel% equ 0 (
    echo ✅ Image Bot dependencies installed successfully
) else (
    echo ❌ Failed to install Image Bot dependencies
    pause
    exit /b 1
)
echo.

echo ==========================================
echo 🎉 All dependencies installed successfully!
echo ==========================================
echo.
echo Next steps:
echo 1. Copy .env.example to .env
echo 2. Edit .env and add your API keys
echo 3. Start Redis server: redis-server
echo 4. Run all bots: python run_bots.py
echo.
pause
