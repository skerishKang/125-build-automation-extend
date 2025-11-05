@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

echo ================================================================
echo  4-BOT DISTRIBUTED TELEGRAM SYSTEM
echo ================================================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo [.env 파일이 없습니다!]
    echo 템플릿을 복사하고 환경변수를 설정해주세요.
    echo.
    echo copy .env.example .env
    echo.
    pause
    exit /b 1
)

REM Check if Gemini API keys are set
findstr /C:"YOUR_GEMINI_API_KEY_HERE" .env >nul
if %errorlevel% equ 0 (
    echo [WARNING] .env에서 Gemini API 키를 설정해주세요!
    echo 4개의 GEMINI_API_KEY_* 값을 실제 API 키로 교체해주세요.
    echo.
    pause
    exit /b 1
)

echo [OK] Environment configured
echo Starting 4-Bot System...
echo.

REM Change to bots directory
cd /d "%~dp0"

REM Check Redis
echo Checking Redis connection...
python -c "import redis; r=redis.Redis(host='localhost', port=6379); r.ping(); print('[OK] Redis: Connected')" 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Redis 연결 실패 - Bot들이 실행되지만 메시지 전달이 제한됩니다
    echo         Redis를 설치하려면: https://redis.io/download
    echo.
)

echo.
echo Starting all 4 bots...
echo ================================================================

REM Run the bot runner
python run_bots.py

echo.
echo ================================================================
echo Bots stopped.
pause
