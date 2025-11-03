# 🚀 125 Build Automation Extend - 배포 가이드

## 📋 목차
1. [운영 전 체크리스트](#운영-전-체크리스트)
2. [PM2 배포](#pm2-배포)
3. [Docker 배포](#docker-배포)
4. [Nginx 설정](#nginx-설정)
5. [SSL 인증서 설정](#ssl-인증서-설정)
6. [모니터링](#모니터링)

---

## 운영 전 체크리스트

### ✅ 필수 설정
- [ ] `backend/.env` 파일 설정
  - [ ] `GEMINI_API_KEY` 설정
  - [ ] `TELEGRAM_BOT_TOKEN` 설정
  - [ ] `ALLOWED_ORIGINS` 설정 (배포 도메인 포함)
  - [ ] `USE_RAG=false` (기본값)

- [ ] `frontend/.env.local` 설정
  - [ ] `BACKEND_ORIGIN=http://localhost:8000` (개발) 또는 실제 도메인 (프로덕션)

### ✅ 의존성 설치
- [ ] Python 3.11+ 설치
- [ ] Node.js 20+ 설치
- [ ] PM2 설치: `npm install -g pm2`
- [ ] Docker & Docker Compose 설치 (선택)

---

## PM2 배포 (권장)

### 1. 의존성 설치

```bash
# 백엔드 의존성
cd backend
pip install -r requirements.txt

# 프론트엔드 의존성
cd ../frontend
npm install

# 루트로 돌아가기
cd ..
```

### 2. PM2 시작

```bash
# 모든 서비스 시작
pm2 start ecosystem.config.js

# 상태 확인
pm2 status

# 로그 보기
pm2 logs

# 설정 저장 (부팅시 자동 시작)
pm2 save
pm2 startup
```

### 3. PM2 관리 명령어

```bash
# 서비스 재시작
pm2 restart all

# 서비스 중지
pm2 stop all

# 서비스 삭제
pm2 delete all

# 모니터링 대시보드
pm2 monit
```

---

## Docker 배포

### 1. 빌드 및 실행

```bash
# 모든 컨테이너 빌드 및 실행
docker-compose up -d

# 로그 보기
docker-compose logs -f

# 컨테이너 중지
docker-compose down

# 컨테이너 재빌드
docker-compose up --build -d
```

### 2. 개별 서비스 관리

```bash
# 백엔드만 재시작
docker-compose restart backend

# 로그 보기
docker-compose logs backend
docker-compose logs frontend
docker-compose logs telegram-bot
```

### 3. 컨테이너 내부 접속

```bash
# 백엔드 컨테이너 접속
docker-compose exec backend bash

# 프론트엔드 컨테이너 접속
docker-compose exec frontend sh
```

---

## Nginx 설정

### 1. 설정 파일 설치

```bash
# Ubuntu/Debian
sudo cp nginx.conf.example /etc/nginx/sites-available/125-automation
sudo ln -s /etc/nginx/sites-available/125-automation /etc/nginx/sites-enabled/

# CentOS/RHEL
sudo cp nginx.conf.example /etc/nginx/conf.d/125-automation.conf
```

### 2. 도메인 수정

```bash
# 설정 파일 편집
sudo nano /etc/nginx/sites-available/125-automation
# 또는
sudo nano /etc/nginx/conf.d/125-automation.conf
```

**수정할 항목:**
- `your-prod-domain.com` → 실제 도메인으로 변경
- 필요 시 포트, 업스트림 서버 경로 수정

### 3. Nginx 재시작

```bash
# 설정 문법 확인
sudo nginx -t

# 재시작
sudo systemctl reload nginx
# 또는
sudo systemctl restart nginx
```

---

## SSL 인증서 설정 (Let's Encrypt)

### 1. Certbot 설치

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install certbot python3-certbot-nginx
```

### 2. 인증서 발급

```bash
# Nginx용 인증서 발급
sudo certbot --nginx -d your-prod-domain.com

# 자동 갱신 설정
sudo crontab -e
# 다음 라인 추가:
0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. HTTPS 설정 활성화

`nginx.conf.example`에서 HTTPS 설정을 해제하고 다시 로드:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 모니터링

### 1. 로그 확인

```bash
# PM2 로그
pm2 logs

# Nginx 로그
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# 시스템 로그
sudo journalctl -u nginx -f
sudo journalctl -f
```

### 2. 서비스 상태 확인

```bash
# 서비스 상태 확인
systemctl status nginx
systemctl status pm2-root

# 포트 사용 확인
netstat -tulpn | grep :80
netstat -tulpn | grep :443
netstat -tulpn | grep :8000
```

### 3. Health Check

```bash
# 백엔드 Health Check
curl http://localhost:8000/health

# 프록시 Health Check (Nginx)
curl http://your-domain.com/health

# API Health Check
curl http://your-domain.com/api/health
```

---

## 트러블슈팅

### ❌ 서비스 시작 실패

**문제**: `pm2 start ecosystem.config.js` 실패
```bash
# 로그 확인
pm2 logs

# 수동 실행으로 원인 파악
cd backend && python -m uvicorn main:app
cd frontend && npm start
```

### ❌ CORS 에러

**문제**: `Access to fetch blocked by CORS policy`

**해결**:
1. `backend/.env`의 `ALLOWED_ORIGINS` 확인
2. 도메인이 정확히 일치하는지 확인 (http/https, 포트)

### ❌ 포트 충돌

**문제**: `Address already in use`

```bash
# 포트 사용 중인 프로세스 확인
lsof -i :8000
lsof -i :3000

# 프로세스kill
kill -9 <PID>

# PM2 프로세스 정리
pm2 delete all
pm2 flush  # 로그 삭제
```

### ❌ Gemini API 오류

**문제**: `gemini_ai: false` 또는 API 호출 실패

**해결**:
1. `.env` 파일에서 `GEMINI_API_KEY` 확인
2. API 키가 유효한지 테스트
3. 백엔드 로그 확인: `tail -f backend/logs/backend.log`

---

## 보안 강화

### 1. 방화벽 설정

```bash
# UFW (Ubuntu)
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable

# FirewallD (CentOS)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2.Fail2ban 설치 (추천)

```bash
# Ubuntu/Debian
sudo apt-get install fail2ban

# 설정
sudo nano /etc/fail2ban/jail.local
```

### 3. 정기 업데이트

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get upgrade

# CentOS/RHEL
sudo yum update
```

---

## 성능 최적화

### 1. PM2 클러스터 모드

`ecosystem.config.js` 수정:
```js
{
  name: "125-backend",
  instances: "max",  // CPU 코어 수만큼 인스턴스 생성
  exec_mode: "cluster",
  // ...
}
```

### 2. Nginx 캐싱

`nginx.conf`에 다음 추가:
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 3. 리소스 모니터링

```bash
# CPU/메모리 사용량 확인
htop
pm2 monit

# 디스크 사용량 확인
df -h
du -sh /var/log/nginx
```

---

## 백업 및 복구

### 1. 데이터 백업

```bash
# 로그 백업
tar -czf logs-backup-$(date +%Y%m%d).tar.gz backend/logs

# 데이터베이스 백업 (향후 추가)
```

### 2. 설정 파일 백업

```bash
# 전체 설정 백업
tar -czf config-backup-$(date +%Y%m%d).tar.gz \
    backend/.env \
    nginx.conf \
    ecosystem.config.js \
    .env
```

---

## 지원

문제 발생 시:
1. 로그 확인 (`pm2 logs`, `tail -f backend/logs/backend.log`)
2. 서비스 상태 확인 (`pm2 status`)
3. Health Check 실행 (`curl http://localhost:8000/health`)

---

## 📞 지원팀

- **레포지토리**: https://github.com/skerishKang/125-build-automation-extend
- **이슈**: GitHub Issues 사용

---

## 📝 업데이트 이력

| 날짜 | 버전 | 변경사항 |
|------|------|----------|
| 2025-11-04 | v0.3.0 | - 포트 프록시 방식 도입<br>- AI 서비스 모듈화<br>- 텔레그램 봇 분리 |
| 2025-11-04 | v0.3.1 | - 운영 설정 추가 (로깅, CORS)<br>- 배포 파일 추가 (PM2, Docker, Nginx)<br>- CI/CD 파이프라인 구축 |
