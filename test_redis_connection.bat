@echo off
REM WSL Redis 연결 테스트 스크립트

echo ================================================
echo WSL Redis 연결 테스트
echo ================================================
echo.

REM WSL IP 주소 가져오기
for /f "tokens=*" %%a in ('wsl ip addr show eth0 2^>nul ^| grep inet 2^>nul ^| awk "{print `$2}" 2^>nul ^| cut -d/ -f1 2^>nul') do set WSL_IP=%%a

if "%WSL_IP%"=="" (
    echo [ERROR] WSL IP 주소를 가져올 수 없습니다!
    echo WSL이 설치되어 있고 실행 중인지 확인하세요.
    pause
    exit /b 1
)

echo WSL IP 주소: %WSL_IP%
echo.

REM Redis 포트 확인
echo [1/2] Redis 포트 상태 확인...
wsl sudo ss -tlnp | findstr "6379"
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Redis가 포트 6379에서 리슨하지 않음
)
echo.

REM Python으로 Redis 연결 테스트
echo [2/2] Python Redis 연결 테스트...
python -c "
try:
    import redis
    r = redis.Redis(host='%WSL_IP%', port=6379, socket_connect_timeout=5)
    result = r.ping()
    print(f'✅ Redis 연결 성공! ping() = {result}')
    print(f'   서버: %WSL_IP%:6379')
except Exception as e:
    print(f'❌ Redis 연결 실패: {e}')
    print(f'   WSL IP: %WSL_IP%')
    print(f'   포트: 6379')
    print()
    print('해결 방법:')
    print('1. install_redis_wsl.bat 실행')
    print('2. WSL에서: sudo service redis-server status')
"

echo.
pause
