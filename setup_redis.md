# WSL Redis Installation Guide

## Step-by-Step Commands

Run these commands in **PowerShell (as Administrator)**:

### 1. Update and Install Redis
```powershell
wsl sudo apt update
wsl sudo apt install -y redis-server
```

### 2. Fix Redis Configuration
```powershell
wsl sudo sed -i 's/^bind 0\.0\.0\.0 -::1/bind 0.0.0.0/' /etc/redis/redis.conf
wsl sudo sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf
```

### 3. Restart Redis
```powershell
wsl sudo service redis-server restart
```

### 4. Verify Configuration
```powershell
echo "=== Bind Settings ==="
wsl grep "^bind" /etc/redis/redis.conf

echo "`n=== Protected Mode ==="
wsl grep "^protected-mode" /etc/redis/redis.conf

echo "`n=== Port Listening Status ==="
wsl sudo ss -tlnp | grep 6379

echo "`n=== WSL IP Address ==="
wsl ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1
```

### 5. Test Connection
```powershell
$WSL_IP = wsl ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1
python -c "import redis; print('Redis connection:', redis.Redis(host='$WSL_IP').ping())"
```

## Quick One-Liner
```powershell
wsl sudo apt update && wsl sudo apt install -y redis-server && wsl sudo sed -i 's/^bind 0\.0\.0\.0 -::1/bind 0.0.0.0/' /etc/redis/redis.conf && wsl sudo sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf && wsl sudo service redis-server restart && wsl sudo ss -tlnp | grep 6379 && echo "WSL IP:" && wsl ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1
```
