@echo off
REM WSL Redis Installation and Setup Script

echo ================================================
echo WSL Redis Installation and IPv6 Fix
echo ================================================
echo.

echo [1/4] Installing Redis server...
wsl sudo apt update && wsl sudo apt install -y redis-server
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Redis installation failed!
    pause
    exit /b 1
)

echo.
echo [2/4] Fixing Redis configuration (remove IPv6)...
wsl sudo sed -i 's/^bind 0\.0\.0\.0 -::1/bind 0.0.0.0/' /etc/redis/redis.conf
wsl sudo sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Configuration update failed!
    pause
    exit /b 1
)

echo.
echo [3/4] Restarting Redis service...
wsl sudo service redis-server restart
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Redis restart failed!
    pause
    exit /b 1
)

echo.
echo [4/4] Verifying configuration...
echo.
echo === Bind Settings ===
wsl grep "^bind" /etc/redis/redis.conf
echo.
echo === Protected Mode ===
wsl grep "^protected-mode" /etc/redis/redis.conf
echo.
echo === Port Listening Status ===
wsl sudo ss -tlnp | grep 6379
echo.
echo === WSL IP Address ===
for /f "tokens=*" %%a in ('wsl ip addr show eth0 ^| grep inet ^| awk "{print `$2}" ^| cut -d/ -f1') do set WSL_IP=%%a
echo WSL IP: %WSL_IP%
echo.

echo ✅ Redis installation and setup completed!
echo.
echo Test connection from PowerShell:
echo python -c "import redis; print('Redis connection:', redis.Redis(host='%WSL_IP%').ping())"
echo.

pause
