# 125 Build Automation Extend 🚀

**Telegram 기반 4-Bot 분산 AI 자동화 시스템** - Gmail, Drive, AI 분석을 통한 완전 자동화

기존 124-build-automation(개인형 AI 자동화 봇)을 여러 사용자가 동시에 사용할 수 있는 SaaS형 분산 시스템으로 확장한 프로젝트입니다.

## ✨ 주요 기능

### 🤖 **4-Bot 분산 시스템**
- **Main Bot** - 사용자 인터페이스 및 작업 분배
- **Document Bot** - PDF, DOCX, TXT, CSV, XLSX, PPTX 분석
- **Audio Bot** - OGG, MP3, WAV 음성 인식 (Whisper AI)
- **Image Bot** - JPG, PNG, GIF, WEBP 이미지 분석 (Gemini Vision)

### 📧 **Gmail 자동화**
- AI 기반 자동 답장
- Gmail 모니터링 및 알림
- 이메일 요약 및 분류

### 📁 **Google Drive 통합**
- 20+ 파일 포맷 자동 분석
- 실시간 파일 동기화
- 크로스 플랫폼 지원

### 🔐 **보안 인증**
- Google OAuth2 - 다중 사용자 인증
- Service Account - 백엔드 서비스 인증
- AES256 암호화 - API 키 안전 저장

### 📊 **실시간 검증**
- API 키 유효성 실시간 확인
- Telegram, Gmail, Drive 연동 상태 모니터링

## 🏗️ 기술 스택

### Bot System (Python)
- **python-telegram-bot** - Telegram Bot API
- **Redis** - Inter-bot 메시지 큐 (Pub/Sub)
- **Gemini AI** - 이미지/문서/음성 분석
- **Whisper** - 음성 인식 (faster-whisper)
- **PyPDF2, python-docx** - 문서 처리
- **pandas** - 데이터 분석

### Backend
- **FastAPI** - 고성능 Python 웹 프레임워크
- **SQLAlchemy** - ORM (SQLite/PostgreSQL 지원)
- **authlib** - Google OAuth2 인증
- **cryptography** - AES256 암호화
- **uvicorn** - ASGI 서버

### Frontend
- **Next.js 14** - React 기반 풀스택 프레임워크
- **TypeScript** - 타입 안전성
- **Tailwind CSS** - 스타일링
- **SWR** - 데이터 페칭

## 📁 프로젝트 구조

```
125-build-automation-extend/
├── bots/                          # 4-Bot 분산 시스템
│   ├── main_bot/                  # 메인 봇 (작업 분배)
│   │   ├── main_bot.py
│   │   └── handlers/
│   ├── document_bot/              # 문서 처리 봇
│   │   └── document_bot.py
│   ├── audio_bot/                 # 오디오 처리 봇
│   │   └── audio_bot.py
│   ├── image_bot/                 # 이미지 처리 봇
│   │   └── image_bot.py
│   ├── shared/                    # 공유 유틸리티
│   │   ├── redis_utils.py         # Redis Pub/Sub
│   │   ├── gemini_client.py       # Gemini AI 클라이언트
│   │   └── telegram_utils.py      # Telegram 유틸리티
│   ├── run_bots.py                # 전체 시스템 실행 스크립트
│   └── .env.example               # 환경변수 예시
│
├── backend/                       # FastAPI 백엔드
│   ├── main.py                    # 메인 서버
│   ├── routers/                   # API 라우터
│   │   ├── auth.py               # Google OAuth
│   │   └── verify_keys.py        # API 키 검증
│   ├── services/                  # 외부 API 통합
│   │   ├── telegram.py           # Telegram 검증
│   │   └── gmail.py              # Gmail 서비스
│   ├── models/                    # 데이터베이스 모델
│   └── utils/                     # 유틸리티
│       └── crypto.py              # AES 암호화
│
├── frontend/                      # Next.js 프론트엔드
│   ├── pages/                    # 페이지 컴포넌트
│   ├── components/               # 재사용 컴포넌트
│   └── styles/                   # 스타일시트
│
├── tools/                         # 유틸리티 도구
│   ├── check_secrets.py          # 민감 파일 검사
│   ├── remove_emojis.py          # 이모지 제거 도구
│   └── remove_unicode.py         # 유니코드 정제
│
└── README.md
```

## 🚀 빠른 시작

### 사전 요구사항
- Python >= 3.9
- Node.js >= 18.0.0
- Redis Server (WSL/Linux/macOS)
- Telegram Bot Tokens (4개)
- Google API Credentials
- Gemini API Key

### 1. Redis 설치 및 시작

#### Ubuntu/WSL
```bash
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

#### macOS
```bash
brew install redis
brew services start redis
```

#### Windows
```powershell
# WSL2 사용 권장
wsl sudo apt install redis-server
wsl sudo service redis-server start
```

### 2. Bot 토큰 설정

1. [@BotFather](https://t.me/BotFather)에서 4개 봇 생성
2. 각 봇의 토큰 저장

### 3. 봇 시스템 설정

```bash
cd bots

# 환경변수 파일 생성
cp .env.example .env

# .env 파일 편집하여 토큰 입력
nano .env
```

**`.env.example` 파일 생성 필요**

### 4. 의존성 설치

```bash
# Bot 시스템
pip install redis python-telegram-bot google-generativeai faster-whisper
pip install PyPDF2 python-docx pandas openpyxl python-pptx chardet

# 또는 프로젝트 루트에서
pip install -r requirements.txt
```

### 5. Bot 시스템 실행

```bash
cd bots
python run_bots.py
```

### 6. 백엔드 실행 (별도 터미널)

```bash
# 프로젝트 루트에서
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### 7. 프론트엔드 실행 (별도 터미널)

```bash
cd frontend
npm install
npm run dev
```

## 🔑 API 키 발급 가이드

### Telegram Bot Token
1. Telegram에서 [@BotFather](https://t.me/BotFather) 검색
2. `/newbot` 명령어 전송
3. 봇 이름과 사용자명 입력
4. 받은 Bot Token을 복사 (형식: `123456789:ABC-DEF...`)
5. **총 4개 생성 필요** (Main, Document, Audio, Image)

### Gemini API Key
1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. "Create API Key" 클릭
3. 복사한 키 사용
4. **4개 각각 다른 키 권장** (부하 분산)

### Google Service Account
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. "IAM & Admin" > "Service Accounts" > "Create Service Account"
4. **권한 추가**:
   - Gmail API User
   - Drive API Full Access
5. "Keys" > "Add Key" > "Create new key" > "JSON" 선택
6. `service_account.json` 다운로드 (보안 주의)

## 🔄 Bot 시스템 동작 방식

### 1. Main Bot (작업 수신 및 분배)
```
사용자 메시지 수신 → Redis Pub/Sub → Specialized Bot으로 전달
```

### 2. Document Bot (문서 분석)
```
PDF/DOCX/TXT 업로드 → 텍스트 추출 → Gemini AI 분석 → 결과 반환
```

### 3. Audio Bot (음성 인식)
```
OGG/MP3/WAV 업로드 → Whisper → 텍스트 변환 → Gemini AI 분석
```

### 4. Image Bot (이미지 분석)
```
JPG/PNG 업로드 → Gemini Vision → 이미지 분석 결과 반환
```

### 5. Redis 메시지 흐름
```
Main Bot → {document|audio|image}_tasks 채널 → 각 Specialized Bot
                    ↓
Specialized Bot → main_bot_results 채널 → Main Bot → 사용자 응답
```

## 📧 Gmail 자동화

### 설정
```python
# service_account.json을 다운로드하여 백엔드에 배치
# Gmail API 활성화 필요
```

### 기능
- **자동 답장**: AI가 이메일 내용 분석 후 적절한 답장 작성
- **메일 모니터링**: 중요 이메일 실시간 알림
- **요약**: 긴 이메일 내용을 핵심만 요약

### 사용법
1. Gmail에서 이메일 전송
2. Main Bot이 자동 감지
3. AI가 분석 후 자동 답장
4. 사용자 승인 후 실제 전송

## 📁 Google Drive 통합

### 지원 포맷
- **문서**: PDF, DOCX, TXT, RTF
- **스프레드시트**: XLSX, XLS, CSV
- **프레젠테이션**: PPTX, PPT
- **이미지**: JPG, PNG, GIF, WEBP
- **데이터**: JSON, XML

### 기능
- **자동 다운로드**: Drive에 업로드된 파일 자동 감지
- **AI 분석**: 업로드된 파일 자동 분석
- **결과 요약**: 분석 결과를 Telegram으로 전송

## 🔒 보안 정보

### 민감 파일 보호
이 프로젝트는 다음 파일들을 `.gitignore`로 보호합니다:
- `.env` 파일들
- `service_account.json`
- `gmail_credentials.json`
- `*_credentials.json`
- `*token*.pickle`
- `*.sqlite-wal`
- `*.sqlite-shm`

### 보안 가이드
1. **API 키는 환경변수로 관리**
2. **서비스 계정 키는 절대 커밋하지 않음**
3. **실행 전 민감 파일 검사**
   ```bash
   python tools/check_secrets.py
   ```
4. **파일 권한 보호**
   ```bash
   chmod 400 service_account.json bots/.env
   ```

## 📊 모니터링 및 로그

### 로그 위치
- `bots/bot_runner.log` - 전체 시스템 로그
- `bots/main_bot.log` - 메인 봇 로그
- `bots/document_bot.log` - 문서 봇 로그
- `bots/audio_bot.log` - 오디오 봇 로그
- `bots/image_bot.log` - 이미지 봇 로그

### 로그 레벨
- `INFO` - 정상 동작
- `WARN` - 주의 사항
- `ERROR` - 오류 발생

## 🛠️ 개발 가이드

### 새 서비스 추가하기

1. **Service 파일 생성**
   ```python
   # backend/services/{service}.py
   def verify_{service}_token(token: str) -> dict:
       # API 검증 로직
       return {'valid': bool, 'error' or 'api_info': dict}
   ```

2. **라우터 추가**
   ```python
   # backend/routers/verify_keys.py
   elif service_name == '{service}':
       return {service}.verify_{service}_token(api_key)
   ```

3. **봇 메시지 핸들러 추가**
   ```python
   # bots/main_bot/handlers/{service}_handler.py
   ```

### 커밋 메시지 컨벤션
```
feat: 새 기능 추가
fix: 버그 수정
refactor: 코드 리팩토링
docs: 문서 업데이트
chore: 설정/빌드 변경
security: 보안 관련 수정
```

## 🚢 배포

### Docker (권장)
```bash
# Docker Compose로 전체 시스템 배포
docker-compose up -d
```

### 수동 배포

#### Render/Fly.io (백엔드)
```yaml
Build Command: pip install -r backend/requirements.txt
Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
Environment Variables:
  - SECRET_KEY
  - GOOGLE_CLIENT_ID
  - DATABASE_URL
```

#### Vercel (프론트엔드)
```env
NEXT_PUBLIC_API_BASE=https://your-backend-url.com
```

#### AWS EC2 (Bot 시스템)
```bash
# Systemd 서비스로 백그라운드 실행
sudo systemctl enable bots
sudo systemctl start bots
```

## ❓ 문제 해결

### Redis 연결 실패
```bash
# Redis 상태 확인
redis-cli ping
# 응답: PONG (정상)

# Redis 시작 (Ubuntu)
sudo service redis-server start

# Redis 시작 (WSL)
wsl sudo service redis-server start
```

### Unicode/이모지 인코딩 오류 (Windows)
- ✅ **이미 해결됨**: 모든 이모지를 ASCII 문자로 교체
- Python 실행 시 UTF-8 환경변수 설정
  ```bash
  set PYTHONIOENCODING=utf-8
  python run_bots.py
  ```

### Telegram Bot 연결 실패
1. Bot Token이 정확한지 확인
2. `.env` 파일에 토큰이 잘 설정되었는지 확인
3. 네트워크 연결 상태 확인

### Gemini API 오류
1. API 키 유효성 확인
2. 쿼터 제한 확인 (요금제)
3. API 키가 서로 다른지 확인 (부하 분산)

### Document Bot 오류
```python
# 필요한 라이브러리 설치 확인
pip install PyPDF2 python-docx pandas openpyxl python-pptx chardet
```

### Audio Bot 오류
```python
# Whisper 모델 다운로드 확인
# 첫 실행 시 모델 자동 다운로드 (시간 소요)
```

## 📊 성능 최적화

### Redis 메모리 최적화
```bash
# redis.conf 설정
maxmemory 512mb
maxmemory-policy allkeys-lru
```

### Gemini API 부하 분산
- **4개 서로 다른 API 키 사용**
- 로드 밸런싱으로 쿼터 제한 회피
- 각 봇별로 다른 키 할당

### Whisper 모델 선택
```python
# bots/audio_bot/audio_bot.py:78
model_size = "small"  # tiny < base < small < medium < large
```

## 📝 라이선스

MIT License

## 🤝 기여하기

프로젝트 개선을 위한 Pull Request와 Issue를 환영합니다!

### 기여 가이드
1. Fork 후 Feature Branch 생성
2.Conventional Commits 사용
3. Pull Request 생성
4. 코드 리뷰 후 Merge

---

**Made with ❤️ for 125 Build Automation Project**

### 🏷️ 태그
`#TelegramBots` `#AI` `#Automation` `#Gmail` `#GoogleDrive` `#Redis` `#FastAPI` `#NextJS` `#SaaS`
